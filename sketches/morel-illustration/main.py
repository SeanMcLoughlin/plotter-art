"""
Morel illustration.

Turns a botanical illustration (a single subject on plain paper) into a
pen-and-ink drawing for a plotter, in four Stabilo pens. Lines follow the
brush strokes of the illustration, and each pen's line density follows how
much of that pen's ink reproduces the illustration's colour.

How it works:
  1. Colour separation: for every colour in the image, solve how much area
     each pen must cover so that pens + paper mix (by area, as hatching does)
     to that colour. Tones are first compressed so the lightest parts of the
     subject map to paper -- pens can't reach the illustration's darks
     without near-solid ink -- then boosted again where a lot of ink is
     needed, so pits stay dense.
  2. Stroke direction: the structure tensor of the image gives the direction
     of the brush strokes. Where it's incoherent (flat areas, centres of
     pits) it blends toward a coarser one that follows the big forms.
  3. Evenly spaced streamlines (Jobard-Lefer style) along that direction, one
     set per pen, spaced so the pen covers its share of the area. Where a
     pen needs more ink than one set of lines gives, a second set of
     straight lines crosses it.

Everything is cached in stages, so changing hatching settings doesn't redo
the separation, and changing colours' preview or pen toggles doesn't redo
anything.

Layers (plot in this order, light to dark):
  1  yellow      (Stabilo 88/54)
  2  light brown (88/89)
  3  dark brown  (88/45)
  4  black       (88/46)

Run with:  uv run vsk run main.py
"""

import math
from collections import deque
from pathlib import Path

import numpy as np
import vpype as vp
import vsketch
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import nnls
from skimage.measure import find_contours

HERE = Path(__file__).parent
PAGE_SIZES = ["9inx12in", "5.5inx8.5in", "a4", "a3", "letter", "11inx14in"]
PENS = ["yellow", "light brown", "dark brown", "black"]
LAYERS = (1, 2, 3, 4)
LUMA = np.array([0.299, 0.587, 0.114])
# Nudge the separation toward lighter pens when several could make a colour.
PEN_COST = np.array([0.0, 0.02, 0.05, 0.15])


def _lin(c):
    """sRGB 0..255 -> linear 0..1."""
    c = np.asarray(c, float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _hex(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], float)


def _largest(mask: np.ndarray) -> np.ndarray:
    lab, n = ndi.label(mask)
    if n == 0:
        return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    return lab == (np.argmax(sizes) + 1)


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------
# Stage cache: each stage keeps only its latest result
# ----------------------------------------------------------------------

_CACHE: dict = {}


def _cached(stage: str, key, make):
    if _CACHE.get(stage, (None,))[0] != key:
        _CACHE[stage] = (key, make())
    return _CACHE[stage][1]


# ----------------------------------------------------------------------
# Source analysis and colour separation (at source resolution)
# ----------------------------------------------------------------------


def analyse(path: Path, mask_threshold: float, stroke_scale: float, form_scale: float) -> dict:
    """Paper colour, subject mask and stroke direction."""
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(float)
    b = max(4, min(rgb.shape[:2]) // 40)
    border = np.concatenate(
        [rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3), rgb[:, :b].reshape(-1, 3), rgb[:, -b:].reshape(-1, 3)]
    )
    paper = np.median(border, axis=0)
    lum = rgb @ LUMA
    # Subject: clearly darker or more colourful than the paper.
    dark = paper @ LUMA - lum
    chroma = np.ptp(rgb, axis=-1) - np.ptp(paper)
    score = ndi.gaussian_filter(np.maximum(dark / 12, chroma / 20), 1.5)
    mask = ndi.binary_fill_holes(ndi.binary_closing(_largest(score > mask_threshold), iterations=3))

    # Stroke direction from the structure tensor, as a doubled-angle vector
    # (so it can be blended and resampled without the 180-degree ambiguity
    # breaking it). Where the fine one is incoherent, blend toward a coarse
    # one that follows the big forms.
    gx = ndi.gaussian_filter(lum, 1.0, order=(0, 1))
    gy = ndi.gaussian_filter(lum, 1.0, order=(1, 0))

    def tensor(rho):
        jxx, jyy, jxy = (ndi.gaussian_filter(a, rho) for a in (gx * gx, gy * gy, gx * gy))
        tr = jxx + jyy + 1e-9
        return (jxx - jyy) / tr, 2 * jxy / tr

    fc, fs = tensor(stroke_scale)
    cc, cs = tensor(form_scale)
    w = np.clip(np.hypot(fc, fs) / 0.4, 0, 1)
    rows = np.flatnonzero(mask.any(axis=1))
    return {"rgb": rgb, "paper": paper, "mask": mask,
            "c2": w * fc + (1 - w) * cc, "s2": w * fs + (1 - w) * cs,
            "subject_px": int(rows[-1] - rows[0] + 1)}


def separate(an: dict, pen_rgb: np.ndarray, white_pct: float, tone_gamma: float, density: float) -> np.ndarray:
    """Per-pen area coverage, shape (h, w, pens)."""
    paper = an["paper"]
    subject = an["mask"]
    refl = _lin(an["rgb"]) / _lin(paper)
    # Tone compression: the lightest subject tones become paper, keeping hue.
    white = np.percentile(refl[subject], white_pct, axis=0)
    refl = np.clip(refl / white, 0, 1) ** tone_gamma
    target = np.where(subject[..., None], 1 - refl, 0)
    # Hatching mixes by area: 1 - refl = sum_i c_i (1 - pen_i / paper).
    A = np.stack([1 - np.clip(_lin(p) / _lin(paper), 0, 1) for p in pen_rgb], 1)
    A_reg = np.vstack([A, np.diag(np.sqrt(0.01 + 0.2 * PEN_COST[: len(pen_rgb)]))])
    zeros = np.zeros(len(pen_rgb))
    q = np.round(target.reshape(-1, 3) * 40).astype(np.int16)
    uniq, inv = np.unique(q, axis=0, return_inverse=True)
    sol = np.array([nnls(A_reg, np.concatenate([u / 40, zeros]))[0] for u in uniq])
    cov = sol[inv.ravel()].reshape(*target.shape[:2], len(pen_rgb))
    cov = ndi.gaussian_filter(cov, (1, 1, 0))
    # Extra ink only where a lot is needed (pits), leaving light areas alone.
    cov *= 1 + (density - 1) * _smoothstep(0.3, 0.8, cov.sum(-1, keepdims=True))
    return np.where(subject[..., None], cov, 0)


# ----------------------------------------------------------------------
# Evenly spaced streamlines (at working resolution)
# ----------------------------------------------------------------------


def _disk(r: int):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    m = xx * xx + yy * yy <= r * r
    return yy[m], xx[m]


def streamlines(cov, ux, uy, rng, res, pen_w, s_min, s_max, stop, step_mm, min_len):
    """Lines along the direction field (ux, uy), spaced so the pen's ink covers
    `cov` of the area.

    New lines start one spacing to the side of accepted ones (Jobard & Lefer),
    falling back to random seeds. A line ends when it comes within `stop`
    spacings of another line, leaves the active area, or turns too sharply.
    Returns polylines in working-pixel (col, row) coordinates.
    """
    h, w = cov.shape
    sep = (np.clip(pen_w / np.maximum(cov, 1e-6), s_min, s_max) / res).astype(np.float32)
    active = cov >= pen_w / s_max
    ys, xs = np.nonzero(active)
    if len(ys) == 0:
        return []
    seed_block = np.zeros((h, w), bool)
    stop_block = np.zeros((h, w), bool)
    order = list(rng.permutation(len(ys))[: max(1, int(len(ys) * (res / s_min) ** 2 * 3))])
    queue: deque = deque()
    step = step_mm / res
    lines = []

    def seeds():
        while order or queue:
            while queue:
                yield queue.popleft()
            if order:
                k = order.pop()
                yield ys[k] + rng.uniform(-0.5, 0.5), xs[k] + rng.uniform(-0.5, 0.5)

    for r0, c0 in seeds():
        if not (0 <= r0 < h and 0 <= c0 < w):
            continue
        if not active[int(r0), int(c0)] or seed_block[int(r0), int(c0)]:
            continue
        pts = [(r0, c0)]
        for sgn in (1, -1):
            r, c = r0, c0
            pr = pc = None
            out = []
            turned = 0.0
            for _ in range(20000):
                ri, ci = int(r), int(c)
                dx, dy = ux[ri, ci], uy[ri, ci]
                if pr is None:
                    dx, dy = sgn * dx, sgn * dy
                else:
                    if dx * pc + dy * pr < 0:  # orientation, not direction
                        dx, dy = -dx, -dy
                    if dx * pc + dy * pr < 0.5:  # too sharp a turn
                        break
                    # Stop before circling a vortex: lines don't block
                    # themselves, so a loop would ink one spot solid.
                    turned += math.asin(max(-1.0, min(1.0, pc * dy - pr * dx)))
                    if abs(turned) > 1.5 * math.pi:
                        break
                r2, c2 = r + dy * step, c + dx * step
                ri, ci = int(r2), int(c2)
                if not (0 <= ri < h and 0 <= ci < w) or not active[ri, ci] or stop_block[ri, ci]:
                    break
                out.append((r2, c2))
                r, c, pr, pc = r2, c2, dy, dx
            pts = out[::-1] + pts if sgn == -1 else pts + out
        pts = np.array(pts)
        if len(pts) * step_mm < min_len:
            continue
        ri = pts[:, 0].astype(int)
        ci = pts[:, 1].astype(int)
        local = sep[ri, ci]
        for blk, frac in ((seed_block, 1.0), (stop_block, stop)):
            radii = np.round(local * frac).astype(int)
            for rad in np.unique(radii):
                # Points are much closer than a disc is wide; stamping about
                # every half-radius covers the same area for far less work.
                every = max(1, int(rad / (2 * step)))
                sel = (radii == rad) & (np.arange(len(radii)) % every == 0)
                sel[-1] |= radii[-1] == rad
                dy_, dx_ = _disk(int(rad))
                rr = (ri[sel][:, None] + dy_[None]).ravel()
                cc = (ci[sel][:, None] + dx_[None]).ravel()
                ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
                blk[rr[ok], cc[ok]] = True
        lines.append(pts[:, ::-1].copy())
        # Seeds just over one spacing out on both sides, every few points.
        for j in range(0, len(pts), 4):
            d = local[j] * 1.05
            nr, nc = ux[ri[j], ci[j]], -uy[ri[j], ci[j]]
            queue.append((pts[j, 0] + nr * d, pts[j, 1] + nc * d))
            queue.append((pts[j, 0] - nr * d, pts[j, 1] - nc * d))
    return lines


# ----------------------------------------------------------------------
# Sketch
# ----------------------------------------------------------------------


class MorelIllustrationSketch(vsketch.SketchClass):
    # --- Source / page ----------------------------------------------------
    # The illustration, relative to this folder.
    image = vsketch.Param("images/morel-dalle.png")
    page_size = vsketch.Param("9inx12in", choices=PAGE_SIZES)
    landscape = vsketch.Param(False)
    # Height of the subject on the page, mm.
    height = vsketch.Param(260.0, min_value=20.0, max_value=500.0, step=1.0)
    # Resolution lines are drawn at, mm per pixel. Raise for faster previews.
    render_res = vsketch.Param(0.08, min_value=0.03, max_value=0.3, step=0.01)

    # --- Source analysis ---------------------------------------------------
    # How different from the paper a pixel must be to count as subject.
    mask_threshold = vsketch.Param(1.0, min_value=0.2, max_value=5.0, step=0.05)
    # Scale (source pixels) of the brush strokes lines follow, and of the
    # big forms they follow where strokes are unclear.
    stroke_scale = vsketch.Param(5.0, min_value=1.0, max_value=30.0, step=0.5)
    form_scale = vsketch.Param(25.0, min_value=5.0, max_value=100.0, step=1.0)

    # --- Tone -------------------------------------------------------------
    # The subject's lightest tones (this percentile) become paper; the rest
    # scales relative to them. Lower = lighter drawing overall.
    white_pct = vsketch.Param(97.0, min_value=50.0, max_value=100.0, step=0.5)
    # > 1 lightens midtones, < 1 darkens them.
    tone_gamma = vsketch.Param(0.8, min_value=0.2, max_value=3.0, step=0.05)
    # Extra ink where a lot is needed (pits): 1 = none, 2 = double.
    density = vsketch.Param(2.0, min_value=1.0, max_value=4.0, step=0.1)

    # --- Hatching ---------------------------------------------------------
    # Closest and widest line spacing, mm.
    min_spacing = vsketch.Param(0.45, min_value=0.2, max_value=3.0, step=0.05)
    max_spacing = vsketch.Param(3.0, min_value=0.5, max_value=10.0, step=0.1)
    # Coverage one set of flowing lines takes; beyond it, straight lines cross.
    cross_at = vsketch.Param(0.3, min_value=0.05, max_value=1.0, step=0.05)
    # Angle of the first pen's crossing lines; each next pen turns 30 degrees.
    cross_angle = vsketch.Param(45.0, min_value=-90.0, max_value=90.0, step=5.0)
    # Lines stop this many spacings from another line.
    stop_distance = vsketch.Param(0.4, min_value=0.1, max_value=1.0, step=0.05)
    # Shortest line kept, mm.
    min_length = vsketch.Param(1.5, min_value=0.0, max_value=10.0, step=0.1)
    # Integration step, mm (larger = faster, coarser curves).
    step = vsketch.Param(0.15, min_value=0.05, max_value=1.0, step=0.05)
    # Silhouette of the whole subject.
    outline = vsketch.Param(True)
    outline_pen = vsketch.Param("dark brown", choices=PENS)

    # --- Pens -------------------------------------------------------------
    # Used for the colour separation as well as the preview, so match them
    # to swatches of the real pens on your paper.
    color_yellow = vsketch.Param("#e0a526")
    color_light = vsketch.Param("#a8784a")
    color_dark = vsketch.Param("#5a3620")
    color_black = vsketch.Param("#1a1a1a")
    draw_yellow = vsketch.Param(True)
    draw_light = vsketch.Param(True)
    draw_dark = vsketch.Param(True)
    draw_black = vsketch.Param(True)
    pen_width = vsketch.Param(0.4, min_value=0.1, max_value=2.0, step=0.05)

    # ------------------------------------------------------------------

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size(self.page_size, landscape=self.landscape)
        vsk.scale("mm")
        page_w, page_h = self._page_mm(vsk)

        path = Path(self.image)
        if not path.is_absolute():
            path = HERE / path
        if not path.exists():
            raise FileNotFoundError(path)
        colors = [self.color_yellow, self.color_light, self.color_dark, self.color_black]

        an_key = (str(path), path.stat().st_mtime, self.mask_threshold, self.stroke_scale, self.form_scale)
        an = _cached("analyse", an_key,
                     lambda: analyse(path, self.mask_threshold, self.stroke_scale, self.form_scale))
        sep_key = (an_key, tuple(colors), self.white_pct, self.tone_gamma, self.density)
        cov = _cached("separate", sep_key, lambda: separate(
            an, np.array([_hex(c) for c in colors]), self.white_pct, self.tone_gamma, self.density))
        hatch_key = (sep_key, self.height, self.render_res, self.min_spacing, self.max_spacing,
                     self.cross_at, self.cross_angle, self.stop_distance, self.min_length, self.step,
                     self.pen_width, vsk.random_seed)
        hatch = _cached("hatch", hatch_key, lambda: self._hatch(an, cov, vsk.random_seed))

        # Centre the drawing on the page.
        res = self.render_res
        h, w = hatch["shape"]
        ox, oy = page_w / 2 - w * res / 2, page_h / 2 - h * res / 2
        enabled = [self.draw_yellow, self.draw_light, self.draw_dark, self.draw_black]
        for layer, lines, on in zip(LAYERS, hatch["lines"], enabled):
            vsk.penWidth(f"{self.pen_width}mm", layer)
            if not on:
                continue
            vsk.stroke(layer)
            for pts in lines:
                vsk.polygon(ox + pts[:, 0] * res, oy + pts[:, 1] * res)
        if self.outline:
            vsk.stroke(LAYERS[PENS.index(self.outline_pen)])
            for pts in hatch["outline"]:
                vsk.polygon(ox + pts[:, 0] * res, oy + pts[:, 1] * res)

        # Set colors here rather than in finalize(): the `vsk run` viewer
        # only runs finalize() on save, but it does honor layer metadata.
        for lid, layer in vsk.document.layers.items():
            if lid in LAYERS:
                layer.set_property(vp.METADATA_FIELD_COLOR, vp.Color(colors[lid - 1]))

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")

    def _hatch(self, an: dict, cov_src: np.ndarray, seed: int) -> dict:
        """Upsample to working resolution and lay out every pen's lines."""
        res = self.render_res
        f = self.height / an["subject_px"] / res  # source px -> working px
        rows = np.flatnonzero(an["mask"].any(axis=1))
        cols = np.flatnonzero(an["mask"].any(axis=0))
        pad = 4
        r0, r1 = max(rows[0] - pad, 0), min(rows[-1] + pad + 1, an["mask"].shape[0])
        c0, c1 = max(cols[0] - pad, 0), min(cols[-1] + pad + 1, an["mask"].shape[1])

        def up(a):
            return ndi.zoom(np.asarray(a[r0:r1, c0:c1], np.float32), f, order=1)

        mask = up(an["mask"]) > 0.5
        theta = 0.5 * np.arctan2(up(an["s2"]), up(an["c2"])) + np.float32(np.pi / 2)  # along the strokes
        ux, uy = np.cos(theta), np.sin(theta)  # (col, row)
        del theta
        rng = np.random.default_rng(seed)
        args = dict(res=res, pen_w=self.pen_width, s_min=self.min_spacing, s_max=self.max_spacing,
                    stop=self.stop_distance, step_mm=self.step, min_len=self.min_length)

        lines = []
        for i in range(cov_src.shape[-1]):
            c = up(cov_src[..., i]).clip(0, None)
            a = math.radians(self.cross_angle + 30 * i)
            flowing = streamlines(np.minimum(c, self.cross_at), ux, uy, rng, **args)
            crossing = streamlines(np.maximum(c - self.cross_at, 0), np.full_like(ux, math.cos(a)),
                                   np.full_like(uy, math.sin(a)), rng, **args)
            lines.append(flowing + crossing)

        smooth = ndi.gaussian_filter(mask.astype(float), 1.5)
        # The silhouette only (the longest contour), not holes or stray specks.
        contours = find_contours(smooth, 0.5)
        outline = [max(contours, key=len)[:, ::-1]] if contours else []
        return {"lines": lines, "outline": outline, "shape": mask.shape}

    @staticmethod
    def _page_mm(vsk: vsketch.Vsketch) -> tuple[float, float]:
        w, h = vsk.document.page_size
        px_per_mm = 96 / 25.4
        return w / px_per_mm, h / px_per_mm


if __name__ == "__main__":
    MorelIllustrationSketch.display()
