"""
Graph paper swallowed by vortices.

A regular grid is drawn as polylines, then every point is pushed through a
chain of vortex warps. Each vortex rotates points around its center by an
angle that decays with distance (the "swirl") and optionally pulls them
inward (the "sink"), which bunches lines up into a dense dark core.

Run with:  uv run vsk run main.py
"""

import math

import numpy as np
import vsketch
from shapely.geometry import LineString, MultiLineString, box

MAX_VORTICES = 4

PAGE_SIZES = ["9inx12in", "a4", "a3", "letter", "11inx14in"]


class VortexGridSketch(vsketch.SketchClass):
    # --- Page -------------------------------------------------------------
    page_size = vsketch.Param("9inx12in", choices=PAGE_SIZES)
    landscape = vsketch.Param(True)
    margin = vsketch.Param(15.0, min_value=0.0, max_value=100.0, step=1.0)

    # --- Grid (all lengths in mm) -----------------------------------------
    cell_size = vsketch.Param(12.0, min_value=2.0, max_value=50.0, step=0.5)
    overshoot = vsketch.Param(3.0, min_value=0.0, max_value=20.0, step=0.5)
    draw_horizontal = vsketch.Param(True)
    draw_vertical = vsketch.Param(True)
    clip_to_frame = vsketch.Param(True)

    # --- Line quality ------------------------------------------------------
    max_segment = vsketch.Param(0.4, min_value=0.05, max_value=5.0, step=0.05)
    wobble = vsketch.Param(0.0, min_value=0.0, max_value=3.0, step=0.05)
    wobble_scale = vsketch.Param(0.05, min_value=0.005, max_value=1.0, step=0.005)

    # --- Vortex cores -----------------------------------------------------
    fill_holes = vsketch.Param(True)
    pen_width = vsketch.Param(0.4, min_value=0.1, max_value=2.0, step=0.05)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size(self.page_size, landscape=self.landscape)
        vsk.scale("mm")

        page_w, page_h = self._page_mm(vsk)
        m = self.margin
        avail_w = page_w - 2 * (m + self.overshoot)
        avail_h = page_h - 2 * (m + self.overshoot)
        cols = max(1, int(avail_w // self.cell_size))
        rows = max(1, int(avail_h // self.cell_size))
        grid_w, grid_h = cols * self.cell_size, rows * self.cell_size
        x0, y0 = (page_w - grid_w) / 2, (page_h - grid_h) / 2

        vortices = self._vortices(x0, y0, grid_w, grid_h)

        lines = []
        step = min(self.cell_size / 4, 1.0)
        os_ = self.overshoot
        if self.draw_horizontal:
            xs = np.arange(x0 - os_, x0 + grid_w + os_ + step / 2, step)
            for r in range(rows + 1):
                y = y0 + r * self.cell_size
                lines.append(np.column_stack([xs, np.full_like(xs, y)]))
        if self.draw_vertical:
            ys = np.arange(y0 - os_, y0 + grid_h + os_ + step / 2, step)
            for c in range(cols + 1):
                x = x0 + c * self.cell_size
                lines.append(np.column_stack([np.full_like(ys, x), ys]))

        warped = []
        for src in lines:
            pts = self._refine_and_warp(src, vortices)
            pts = self._apply_wobble(vsk, pts)
            warped.extend(self._cut_holes(pts, vortices))

        geom = MultiLineString([p for p in warped if len(p) >= 2])
        if self.clip_to_frame:
            frame = box(x0 - os_, y0 - os_, x0 + grid_w + os_, y0 + grid_h + os_)
            geom = geom.intersection(frame)
        vsk.geometry(geom)

        if self.fill_holes:
            for v in vortices:
                if v["hole"] > 0:
                    vsk.geometry(self._spiral(v["cx"], v["cy"], v["hole"]))

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")

    # ------------------------------------------------------------------
    # Vortex math
    # ------------------------------------------------------------------

    def _vortices(self, x0, y0, grid_w, grid_h) -> list[dict]:
        res = []
        for i in range(MAX_VORTICES):
            if not getattr(self, f"v{i}_on"):
                continue
            res.append(
                {
                    "cx": x0 + getattr(self, f"v{i}_x") * grid_w,
                    "cy": y0 + getattr(self, f"v{i}_y") * grid_h,
                    "turns": getattr(self, f"v{i}_turns"),
                    "radius": getattr(self, f"v{i}_radius"),
                    "tightness": getattr(self, f"v{i}_tightness"),
                    "pull": getattr(self, f"v{i}_pull"),
                    "hole": getattr(self, f"v{i}_hole"),
                }
            )
        return res

    @staticmethod
    def _warp(pts: np.ndarray, vortices: list[dict]) -> np.ndarray:
        """Apply each vortex in sequence: rotate around the center by an angle
        that decays with distance, and squeeze radially toward the center."""
        out = pts.copy()
        for v in vortices:
            rel = out - (v["cx"], v["cy"])
            d = np.hypot(rel[:, 0], rel[:, 1])
            # Influence: 1 at the center, ~0 past `radius`. The gaussian keeps
            # the far grid untouched; tightness concentrates the twist into
            # the core (0 = soft swirl, high = whirlpool drain).
            u = d / v["radius"]
            w = np.exp(-(u**2)) / (1 + v["tightness"] * u)
            theta = 2 * math.pi * v["turns"] * w
            scale = 1 - v["pull"] * w
            c, s = np.cos(theta), np.sin(theta)
            rx = (rel[:, 0] * c - rel[:, 1] * s) * scale
            ry = (rel[:, 0] * s + rel[:, 1] * c) * scale
            out = np.column_stack([rx + v["cx"], ry + v["cy"]])
        return out

    def _refine_and_warp(self, src: np.ndarray, vortices: list[dict]) -> np.ndarray:
        """Subdivide source segments until every warped segment is shorter
        than `max_segment`, so tight spirals near the core stay smooth."""
        dst = self._warp(src, vortices)
        for _ in range(20):
            seg = np.hypot(*np.diff(dst, axis=0).T)
            long_ = seg > self.max_segment
            if not long_.any() or len(src) > 200_000:
                break
            idx = np.nonzero(long_)[0]
            mid_src = (src[idx] + src[idx + 1]) / 2
            mid_dst = self._warp(mid_src, vortices)
            src = np.insert(src, idx + 1, mid_src, axis=0)
            dst = np.insert(dst, idx + 1, mid_dst, axis=0)
        return dst

    def _apply_wobble(self, vsk: vsketch.Vsketch, pts: np.ndarray) -> np.ndarray:
        if self.wobble <= 0:
            return pts
        x, y = pts[:, 0] * self.wobble_scale, pts[:, 1] * self.wobble_scale
        nx = vsk.noise(x, y, np.zeros_like(x), grid_mode=False)
        ny = vsk.noise(x, y, np.full_like(x, 7.3), grid_mode=False)
        return pts + self.wobble * 2 * (np.column_stack([nx, ny]) - 0.5)

    @staticmethod
    def _cut_holes(pts: np.ndarray, vortices: list[dict]) -> list[np.ndarray]:
        """Drop points inside any vortex hole, splitting the polyline."""
        keep = np.ones(len(pts), dtype=bool)
        for v in vortices:
            if v["hole"] > 0:
                d = np.hypot(pts[:, 0] - v["cx"], pts[:, 1] - v["cy"])
                keep &= d > v["hole"]
        if keep.all():
            return [pts]
        pieces, start = [], None
        for i, k in enumerate(np.append(keep, False)):
            if k and start is None:
                start = i
            elif not k and start is not None:
                pieces.append(pts[start:i])
                start = None
        return pieces

    def _spiral(self, cx: float, cy: float, r: float) -> LineString:
        """Archimedean spiral filling a disc: one continuous stroke."""
        spacing = self.pen_width
        max_t = 2 * math.pi * r / spacing
        n = max(8, int(max_t * r / spacing))
        t = np.linspace(0, max_t, n)
        rad = spacing * t / (2 * math.pi)
        return LineString(np.column_stack([cx + rad * np.cos(t), cy + rad * np.sin(t)]))

    @staticmethod
    def _page_mm(vsk: vsketch.Vsketch) -> tuple[float, float]:
        w, h = vsk.document.page_size
        px_per_mm = 96 / 25.4
        return w / px_per_mm, h / px_per_mm


# Generate the per-vortex params. vsketch discovers Params by walking the
# class __dict__, so adding them after class creation works fine.
_DEFAULT_VORTICES = [
    # on, x, y, turns, radius, tightness, pull, hole
    (True, 0.58, 0.55, 1.8, 50.0, 3.0, 0.9, 2.0),
    (False, 0.25, 0.35, -1.0, 40.0, 0.0, 0.2, 0.0),
    (False, 0.80, 0.25, 1.0, 30.0, 2.0, 0.0, 0.0),
    (False, 0.30, 0.80, 0.5, 50.0, 0.0, 0.0, 0.0),
]
for _i, (_on, _x, _y, _turns, _rad, _tight, _pull, _hole) in enumerate(_DEFAULT_VORTICES):
    _params = {
        "on": vsketch.Param(_on),
        "x": vsketch.Param(_x, min_value=0.0, max_value=1.0, step=0.01),
        "y": vsketch.Param(_y, min_value=0.0, max_value=1.0, step=0.01),
        "turns": vsketch.Param(_turns, min_value=-10.0, max_value=10.0, step=0.1),
        "radius": vsketch.Param(_rad, min_value=1.0, max_value=300.0, step=1.0),
        "tightness": vsketch.Param(_tight, min_value=0.0, max_value=30.0, step=0.5),
        "pull": vsketch.Param(_pull, min_value=0.0, max_value=1.0, step=0.01),
        "hole": vsketch.Param(_hole, min_value=0.0, max_value=30.0, step=0.5),
    }
    for _name, _param in _params.items():
        setattr(VortexGridSketch, f"v{_i}_{_name}", _param)


if __name__ == "__main__":
    VortexGridSketch.display()
