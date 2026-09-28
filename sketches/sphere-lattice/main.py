"""
Sphere lattice.

A sphere woven from solid tubes: several families of parallel circles
(latitude-style rings around different axes), rendered as real 3D tubes with
hidden-line removal and lit shading. The point of the sketch is to compare two
ways of getting tone out of a pen plotter:

  * hatch depth  -- one black pen; darker tones add more hatch passes
                    (each pass a new direction, or denser parallel lines)
  * multi pen    -- light grey, dark grey and black markers; darker tones
                    overprint with darker pens

How it works: every tube is rasterized into a z-buffer (depth, tube id,
angle along the tube, shading, depth-in-sphere). Strokes -- tube silhouettes
and hatch lines -- are generated analytically on the tube surfaces, then
sampled against that buffer so only visible bits survive.

Layers (plot in this order, light to dark):
  1  light grey
  2  dark grey
  3  black

Run with:  uv run vsk run main.py
"""

import math

import numpy as np
import vpype as vp
import vsketch

PAGE_SIZES = ["9inx12in", "5.5inx8.5in", "a4", "a3", "letter", "11inx14in"]
PENS = ["light grey", "dark grey", "black"]
LIGHT, DARK, BLACK = 1, 2, 3


def _rot(yaw: float, pitch: float, roll: float) -> np.ndarray:
    ry, rp, rr = map(math.radians, (yaw, pitch, roll))
    rot_y = np.array(
        [[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]]
    )
    rot_x = np.array(
        [[1, 0, 0], [0, math.cos(rp), -math.sin(rp)], [0, math.sin(rp), math.cos(rp)]]
    )
    rot_z = np.array(
        [[math.cos(rr), -math.sin(rr), 0], [math.sin(rr), math.cos(rr), 0], [0, 0, 1]]
    )
    return rot_z @ rot_x @ rot_y


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, stop) index pairs of the True runs in a 1D mask, len >= 2."""
    m = np.concatenate([[False], mask, [False]]).astype(np.int8)
    d = np.diff(m)
    starts = np.flatnonzero(d == 1)
    stops = np.flatnonzero(d == -1)
    return [(a, b) for a, b in zip(starts, stops) if b - a >= 2]


class Tube:
    """A circle of radius `rho` around `centre`, in the plane spanned by u, v,
    swept with a circular cross-section of radius `r`. All in view space
    (x right, y up, z toward the viewer), mm, sphere centred on the origin."""

    def __init__(self, tid, centre, u, v, axis, rho, r):
        self.tid = tid
        self.c, self.u, self.v, self.a = centre, u, v, axis
        self.rho, self.r = rho, r

    def frame(self, phi):
        cos, sin = np.cos(phi)[:, None], np.sin(phi)[:, None]
        n = cos * self.u + sin * self.v  # radial, in the circle plane
        return self.c + self.rho * n, n

    def surface(self, phi, theta):
        """Points and normals at matching (phi, theta) arrays."""
        centre, n = self.frame(phi)
        ct, st = np.cos(theta)[:, None], np.sin(theta)[:, None]
        normal = ct * n + st * self.a
        return centre + self.r * normal, normal, centre

    def silhouette_theta(self, phi):
        """theta of the two silhouette lines (normal perpendicular to view),
        and a mask of where that is well defined."""
        _, n = self.frame(phi)
        nz, az = n[:, 2], self.a[2]
        ok = np.hypot(nz, az) > 1e-3
        t0 = np.arctan2(-nz, az)
        return t0, t0 + np.pi, ok


class SphereLatticeSketch(vsketch.SketchClass):
    # --- Page -------------------------------------------------------------
    page_size = vsketch.Param("9inx12in", choices=PAGE_SIZES)
    landscape = vsketch.Param(False)
    sphere_radius = vsketch.Param(80.0, min_value=10.0, max_value=200.0, step=1.0)

    # --- Lattice ----------------------------------------------------------
    families = vsketch.Param(4, min_value=1, max_value=6)
    circles = vsketch.Param(7, min_value=1, max_value=25)
    # "angle": evenly spaced latitudes; "height": evenly spaced slices.
    spacing_mode = vsketch.Param("angle", choices=["angle", "height"])
    lat_extent = vsketch.Param(0.9, min_value=0.1, max_value=1.0, step=0.01)
    tube_radius = vsketch.Param(2.0, min_value=0.3, max_value=8.0, step=0.1)
    yaw = vsketch.Param(20.0, min_value=-180.0, max_value=180.0, step=1.0)
    pitch = vsketch.Param(15.0, min_value=-90.0, max_value=90.0, step=1.0)
    roll = vsketch.Param(0.0, min_value=-180.0, max_value=180.0, step=1.0)

    # --- Light ------------------------------------------------------------
    light_azimuth = vsketch.Param(-45.0, min_value=-180.0, max_value=180.0, step=5.0)
    light_elevation = vsketch.Param(40.0, min_value=-90.0, max_value=90.0, step=5.0)
    ambient = vsketch.Param(0.1, min_value=0.0, max_value=1.0, step=0.01)
    highlight = vsketch.Param(0.4, min_value=0.0, max_value=1.0, step=0.05)
    shininess = vsketch.Param(20.0, min_value=1.0, max_value=200.0, step=1.0)
    # Tone multiplier for struts on the far side of the sphere (1 = no fade).
    back_fade = vsketch.Param(0.5, min_value=0.0, max_value=1.0, step=0.05)
    gamma = vsketch.Param(1.0, min_value=0.2, max_value=4.0, step=0.05)

    # --- Shading ----------------------------------------------------------
    # "hatch depth": one black pen, tone = more passes.
    # "multi pen":   tone levels go to light grey / dark grey / black.
    pen_mode = vsketch.Param("multi pen", choices=["hatch depth", "multi pen"])
    # "contour": hatch wraps the tubes (along + helical).
    # "screen":  straight cross-hatching across the page.
    hatch_style = vsketch.Param("contour", choices=["contour", "screen"])
    # "cross":    each tone level adds a new hatch direction.
    # "parallel": each level adds lines between the previous ones.
    layering = vsketch.Param("cross", choices=["cross", "parallel"])
    hatch_spacing = vsketch.Param(1.0, min_value=0.2, max_value=5.0, step=0.05)
    # Screen: angle of the first pass. Contour: helix angle of the cross passes.
    hatch_angle = vsketch.Param(45.0, min_value=-90.0, max_value=90.0, step=5.0)
    # Contour only: drop hatching where the surface turns away more than this
    # (0..1 of the normal facing you), so lines don't pile up at tube edges.
    rim_cutoff = vsketch.Param(0.2, min_value=0.0, max_value=0.9, step=0.05)
    level_1 = vsketch.Param(0.25, min_value=0.0, max_value=1.0, step=0.01)
    level_2 = vsketch.Param(0.5, min_value=0.0, max_value=1.0, step=0.01)
    level_3 = vsketch.Param(0.75, min_value=0.0, max_value=1.0, step=0.01)
    draw_level_1 = vsketch.Param(True)
    draw_level_2 = vsketch.Param(True)
    draw_level_3 = vsketch.Param(True)

    # --- Outlines ---------------------------------------------------------
    outlines = vsketch.Param(True)
    outline_pen = vsketch.Param("black", choices=PENS)
    # Multi pen only: on the far side of the sphere, draw outlines and the
    # first tone level with the light grey pen and skip the darker levels.
    back_to_light = vsketch.Param(True)

    # --- Quality / pens ---------------------------------------------------
    raster_res = vsketch.Param(0.12, min_value=0.03, max_value=0.5, step=0.01)
    color_light = vsketch.Param("#b4b4b4")
    color_dark = vsketch.Param("#6a6a6a")
    color_black = vsketch.Param("#111111")
    pen_width = vsketch.Param(0.4, min_value=0.1, max_value=2.0, step=0.05)

    # ------------------------------------------------------------------

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size(self.page_size, landscape=self.landscape)
        vsk.scale("mm")
        page_w, page_h = self._page_mm(vsk)
        self.cx, self.cy = page_w / 2, page_h / 2

        self.light = _unit(
            np.array(
                [
                    math.cos(math.radians(self.light_elevation))
                    * math.sin(math.radians(self.light_azimuth)),
                    math.sin(math.radians(self.light_elevation)),
                    math.cos(math.radians(self.light_elevation))
                    * math.cos(math.radians(self.light_azimuth)),
                ]
            )
        )
        self.half_vec = _unit(self.light + np.array([0.0, 0.0, 1.0]))

        tubes = self._build_tubes()
        self._rasterize(tubes)

        self.strokes: dict[int, list[np.ndarray]] = {LIGHT: [], DARK: [], BLACK: []}
        levels = self._levels()
        if self.hatch_style == "contour":
            for t in tubes:
                self._contour_hatch(t, levels)
        else:
            self._screen_hatch(levels)
        if self.outlines:
            for t in tubes:
                self._outline(t)

        for layer, lines in self.strokes.items():
            vsk.penWidth(f"{self.pen_width}mm", layer)
            vsk.stroke(layer)
            for pts in lines:
                vsk.polygon(pts[:, 0], pts[:, 1])

        # Set colors here rather than in finalize(): the `vsk run` viewer
        # only runs finalize() on save, but it does honor layer metadata.
        colors = {LIGHT: self.color_light, DARK: self.color_dark, BLACK: self.color_black}
        for lid, layer in vsk.document.layers.items():
            if lid in colors:
                layer.set_property(vp.METADATA_FIELD_COLOR, vp.Color(colors[lid]))

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def _build_tubes(self) -> list[Tube]:
        rot = _rot(self.yaw, self.pitch, self.roll)
        R, r = self.sphere_radius, self.tube_radius
        n = self.circles
        if self.spacing_mode == "angle":
            lats = [
                math.radians(((i + 0.5) / n * 2 - 1) * 90 * self.lat_extent)
                for i in range(n)
            ]
        else:
            lats = [math.asin(((i + 0.5) / n * 2 - 1) * self.lat_extent) for i in range(n)]

        tubes = []
        for f in range(self.families):
            # Family axes fan around the picture plane; family 0 is vertical,
            # giving horizontal "latitude" rings.
            ang = math.pi / 2 + f * math.pi / self.families
            axis = np.array([math.cos(ang), math.sin(ang), 0.0])
            u = _unit(np.cross(axis, [0.0, 0.0, 1.0]))
            v = np.cross(axis, u)
            axis, u, v = rot @ axis, rot @ u, rot @ v
            for lat in lats:
                rho = R * math.cos(lat)
                if rho < 3 * r:
                    continue
                tubes.append(Tube(len(tubes), R * math.sin(lat) * axis, u, v, axis, rho, r))
        return tubes

    # ------------------------------------------------------------------
    # Shading
    # ------------------------------------------------------------------

    def _darkness(self, normal: np.ndarray, centre: np.ndarray) -> np.ndarray:
        """0 = paper white, 1 = full black."""
        lam = np.clip(normal @ self.light, 0, None)
        tone = self.ambient + (1 - self.ambient) * lam
        spec = np.clip(normal @ self.half_vec, 0, None) ** self.shininess
        dark = np.clip(1 - tone - self.highlight * spec, 0, 1) ** self.gamma
        # Fade struts on the far half of the sphere.
        cz = np.clip(centre[:, 2] / self.sphere_radius, -1, 0)
        return dark * (1 + cz * (1 - self.back_fade))

    def _levels(self) -> list[tuple[int, float, int]]:
        """(level index, threshold, pen layer) for each enabled level."""
        out = []
        for i, (thr, on) in enumerate(
            [
                (self.level_1, self.draw_level_1),
                (self.level_2, self.draw_level_2),
                (self.level_3, self.draw_level_3),
            ]
        ):
            if on:
                layer = (LIGHT, DARK, BLACK)[i] if self.pen_mode == "multi pen" else BLACK
                out.append((i, thr, layer))
        return out

    def _layer_for(self, layer: int, centre: np.ndarray, level: int = 0) -> np.ndarray:
        """Per-point pen layer (0 = skip), rerouting the far side."""
        out = np.full(len(centre), layer)
        if self.pen_mode == "multi pen" and self.back_to_light:
            out[centre[:, 2] < 0] = LIGHT if level == 0 else 0
        return out

    # ------------------------------------------------------------------
    # Z-buffer
    # ------------------------------------------------------------------

    def _rasterize(self, tubes: list[Tube]) -> None:
        res = self.res = self.raster_res
        ext = self.sphere_radius + self.tube_radius + 2
        self.ox, self.oy = self.cx - ext, self.cy - ext
        self.size = size = int(math.ceil(2 * ext / res)) + 1
        self.zbuf = np.full(size * size, -np.inf, dtype=np.float32)
        self.tbuf = np.full(size * size, -1, dtype=np.int32)
        self.pbuf = np.zeros(size * size, dtype=np.float32)
        self.dbuf = np.zeros(size * size, dtype=np.float32)
        self.cbuf = np.zeros(size * size, dtype=np.float32)  # centreline z

        step = res * 0.5
        for t in tubes:
            n_phi = int(math.ceil(2 * math.pi * (t.rho + t.r) / step))
            n_th = int(math.ceil(math.pi * t.r / step)) + 1
            phi = np.linspace(0, 2 * math.pi, n_phi, endpoint=False)
            # Only the front-facing half of each cross-section can be seen.
            t0, _, _ = t.silhouette_theta(phi)
            th = t0[:, None] + np.linspace(0, math.pi, n_th)[None, :]
            phi_g = np.repeat(phi, n_th)
            th_g = th.ravel()
            p, normal, centre = t.surface(phi_g, th_g)
            keep = normal[:, 2] >= 0
            p, normal, centre = p[keep], normal[keep], centre[keep]
            phi_g = phi_g[keep]

            idx = self._pix(p)
            z = p[:, 2].astype(np.float32)
            # Nearest sample per pixel within this tube.
            order = np.lexsort((-z, idx))
            idx_s = idx[order]
            first = np.concatenate([[True], idx_s[1:] != idx_s[:-1]])
            sel = order[first]
            pix = idx[sel]
            nearer = z[sel] > self.zbuf[pix]
            sel, pix = sel[nearer], pix[nearer]
            self.zbuf[pix] = z[sel]
            self.tbuf[pix] = t.tid
            self.pbuf[pix] = phi_g[sel]
            self.dbuf[pix] = self._darkness(normal[sel], centre[sel])
            self.cbuf[pix] = centre[sel, 2]

    def _pix(self, p: np.ndarray) -> np.ndarray:
        """Flat buffer index of view-space points (x right, y up)."""
        col = np.clip(((self.cx + p[:, 0] - self.ox) / self.res).astype(np.int64), 0, self.size - 1)
        row = np.clip(((self.cy - p[:, 1] - self.oy) / self.res).astype(np.int64), 0, self.size - 1)
        return row * self.size + col

    def _visible(self, t: Tube, p: np.ndarray, phi: np.ndarray) -> np.ndarray:
        idx = self._pix(p)
        zb = self.zbuf[idx]
        z = p[:, 2]
        strict = zb <= z + 2 * self.res
        # Near the silhouette the tube's own surface rises steeply between
        # pixels, so be lenient against nearby parts of the same tube.
        dphi = np.abs((self.pbuf[idx] - phi + np.pi) % (2 * np.pi) - np.pi)
        own = (self.tbuf[idx] == t.tid) & (dphi * t.rho < 3 * t.r)
        return strict | (own & (zb <= z + 1.5 * t.r))

    # ------------------------------------------------------------------
    # Strokes
    # ------------------------------------------------------------------

    def _emit(self, xy: np.ndarray, keep: np.ndarray, layers: np.ndarray, closed: bool) -> None:
        """Split a sampled line into visible runs per pen layer."""
        for layer in (LIGHT, DARK, BLACK):
            m = keep & (layers == layer)
            if not m.any():
                continue
            if closed and m.all():
                self.strokes[layer].append(np.vstack([xy, xy[:1]]))
                continue
            for a, b in _runs(m):
                self.strokes[layer].append(xy[a:b])

    def _to_page(self, p: np.ndarray) -> np.ndarray:
        return np.column_stack([self.cx + p[:, 0], self.cy - p[:, 1]])

    def _outline(self, t: Tube) -> None:
        step = 0.25
        n = int(math.ceil(2 * math.pi * (t.rho + t.r) / step))
        phi = np.linspace(0, 2 * math.pi, n, endpoint=False)
        t0, t1, ok = t.silhouette_theta(phi)
        layer = {"light grey": LIGHT, "dark grey": DARK, "black": BLACK}[self.outline_pen]
        for th in (t0, t1):
            p, _, centre = t.surface(phi, th)
            keep = ok & self._visible(t, p, phi)
            self._emit(self._to_page(p), keep, self._layer_for(layer, centre), closed=True)

    def _contour_hatch(self, t: Tube, levels) -> None:
        sp = self.hatch_spacing
        n_around = max(3, int(round(2 * math.pi * t.r / sp)))
        d_th = 2 * math.pi / n_around
        # Whole number of helix turns per circuit so every helix closes.
        turns = round(t.rho / t.r * math.tan(math.radians(self.hatch_angle)))
        pitch = math.hypot(t.rho + t.r, t.r * turns)
        phi = np.linspace(0, 2 * math.pi, int(math.ceil(2 * math.pi * pitch / 0.25)), endpoint=False)

        for i, thr, layer in levels:
            if self.layering == "cross":
                # Along the tube, then a helix, then the opposite helix.
                twist, frac = (0, turns, -turns)[i], 0.0
            else:
                # Along the tube at 0, 1/3 and 2/3 of the spacing.
                twist, frac = 0, i / 3
            for k in range(n_around):
                th = (k + frac) * d_th + twist * phi
                self._hatch_line(t, phi, th, thr, layer, i)

    def _hatch_line(self, t: Tube, phi, theta, thr, layer, level) -> None:
        p, normal, centre = t.surface(phi, theta)
        keep = normal[:, 2] > self.rim_cutoff
        if not keep.any():
            return
        keep &= self._darkness(normal, centre) > thr
        if not keep.any():
            return
        keep &= self._visible(t, p, phi)
        self._emit(self._to_page(p), keep, self._layer_for(layer, centre, level), closed=True)

    def _screen_hatch(self, levels) -> None:
        ext = self.size * self.res / 2
        mid = np.array([self.ox + ext, self.oy + ext])
        span = ext * math.sqrt(2)
        sp = self.hatch_spacing
        s = np.arange(-span, span, self.res * 0.7)
        covered = self.tbuf >= 0
        for i, thr, layer in levels:
            if self.layering == "cross":
                ang = self.hatch_angle + (0, 90, 45)[i]
                off = 0.0
            else:
                ang = self.hatch_angle
                off = i / 3
            a = math.radians(ang)
            d = np.array([math.cos(a), math.sin(a)])
            nrm = np.array([-d[1], d[0]])
            mask = covered & (self.dbuf > thr)
            pen = np.full(self.size * self.size, layer)
            if self.pen_mode == "multi pen" and self.back_to_light:
                pen[self.cbuf < 0] = LIGHT if i == 0 else 0
            for o in np.arange(-span, span, sp) + off * sp:
                xy = mid + o * nrm + s[:, None] * d
                col = ((xy[:, 0] - self.ox) / self.res).astype(np.int64)
                row = ((xy[:, 1] - self.oy) / self.res).astype(np.int64)
                inside = (col >= 0) & (col < self.size) & (row >= 0) & (row < self.size)
                idx = np.where(inside, row * self.size + col, 0)
                keep = inside & mask[idx]
                if keep.any():
                    self._emit(xy, keep, np.where(inside, pen[idx], 0), closed=False)

    @staticmethod
    def _page_mm(vsk: vsketch.Vsketch) -> tuple[float, float]:
        w, h = vsk.document.page_size
        px_per_mm = 96 / 25.4
        return w / px_per_mm, h / px_per_mm


if __name__ == "__main__":
    SphereLatticeSketch.display()
