"""
Chromatic aberration cubes.

A grid of wireframe cubes, each drawn three times on separate layers (yellow,
magenta, cyan). The three copies are split apart by an offset that grows
across the grid: left-to-right it splits horizontally, top-to-bottom it splits
vertically, so the top-left cube is a single clean overprint and the
bottom-right one is fully smeared. Plot each layer with its own pen.

Inspired by https://adamfuhrer.com/t/pen-plot

Run with:  uv run vsk run main.py
"""

import math

import numpy as np
import vpype as vp
import vsketch

PAGE_SIZES = ["9inx12in", "a4", "a3", "letter", "11inx14in"]

# Unit cube centered on the origin, y up, z toward the viewer.
VERTS = np.array(
    [[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float
)
# Each face as a loop of vertex indices (index = 4*xi + 2*yi + zi).
FACES = [
    (0, 1, 3, 2),  # x = -1
    (4, 6, 7, 5),  # x = +1
    (0, 4, 5, 1),  # y = -1
    (2, 3, 7, 6),  # y = +1
    (0, 2, 6, 4),  # z = -1
    (1, 5, 7, 3),  # z = +1
]


class ChromaticCubesSketch(vsketch.SketchClass):
    # --- Page -------------------------------------------------------------
    page_size = vsketch.Param("9inx12in", choices=PAGE_SIZES)
    landscape = vsketch.Param(False)
    margin = vsketch.Param(25.0, min_value=0.0, max_value=100.0, step=1.0)

    # --- Grid -------------------------------------------------------------
    cols = vsketch.Param(7, min_value=1, max_value=30)
    rows = vsketch.Param(7, min_value=1, max_value=30)
    cube_size = vsketch.Param(0.42, min_value=0.1, max_value=1.2, step=0.01)

    # --- Orientation (degrees) --------------------------------------------
    yaw_min = vsketch.Param(25.0, min_value=-90.0, max_value=90.0, step=1.0)
    yaw_max = vsketch.Param(55.0, min_value=-90.0, max_value=90.0, step=1.0)
    pitch_min = vsketch.Param(18.0, min_value=-90.0, max_value=90.0, step=1.0)
    pitch_max = vsketch.Param(32.0, min_value=-90.0, max_value=90.0, step=1.0)
    roll_jitter = vsketch.Param(3.0, min_value=0.0, max_value=45.0, step=0.5)
    perspective = vsketch.Param(0.1, min_value=0.0, max_value=0.6, step=0.01)

    # --- Aberration -------------------------------------------------------
    # Max split (mm) between neighbouring layers at the far column / row.
    shift_x = vsketch.Param(2.5, min_value=0.0, max_value=20.0, step=0.1)
    shift_y = vsketch.Param(2.5, min_value=0.0, max_value=20.0, step=0.1)
    # >1 keeps the first columns/rows clean longer, <1 splits them sooner.
    shift_curve = vsketch.Param(1.0, min_value=0.2, max_value=4.0, step=0.1)
    # Extra per-layer yaw (deg) and scale split, also growing across the grid.
    rotate_split = vsketch.Param(0.0, min_value=0.0, max_value=20.0, step=0.5)
    scale_split = vsketch.Param(0.0, min_value=0.0, max_value=0.3, step=0.01)
    show_hidden = vsketch.Param(False)

    # --- Pens -------------------------------------------------------------
    color_1 = vsketch.Param("#f5c400")
    color_2 = vsketch.Param("#e5006e")
    color_3 = vsketch.Param("#00a0e3")
    pen_width = vsketch.Param(0.4, min_value=0.1, max_value=2.0, step=0.05)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size(self.page_size, landscape=self.landscape)
        vsk.scale("mm")

        page_w, page_h = self._page_mm(vsk)
        cell = min(
            (page_w - 2 * self.margin) / self.cols,
            (page_h - 2 * self.margin) / self.rows,
        )
        x0 = (page_w - cell * self.cols) / 2
        y0 = (page_h - cell * self.rows) / 2
        # Half edge length: a cube's projection spans up to ~sqrt(3) edges.
        half = self.cube_size * cell / math.sqrt(3)

        for layer in (1, 2, 3):
            vsk.penWidth(f"{self.pen_width}mm", layer)

        for r in range(self.rows):
            for c in range(self.cols):
                yaw = vsk.random(self.yaw_min, self.yaw_max)
                pitch = vsk.random(self.pitch_min, self.pitch_max)
                roll = vsk.random(-self.roll_jitter, self.roll_jitter)
                tx = self._ramp(c, self.cols)
                ty = self._ramp(r, self.rows)
                t = max(tx, ty)
                cx = x0 + (c + 0.5) * cell
                cy = y0 + (r + 0.5) * cell

                # Layer 2 (magenta) is the anchor; 1 and 3 split either side.
                for layer, k in ((1, -1), (2, 0), (3, 1)):
                    vsk.stroke(layer)
                    edges = self._cube_edges(
                        yaw + k * t * self.rotate_split,
                        pitch,
                        roll,
                        half * (1 + k * t * self.scale_split),
                    )
                    ox = cx + k * tx * self.shift_x
                    oy = cy + k * ty * self.shift_y
                    for a, b in edges:
                        vsk.line(ox + a[0], oy + a[1], ox + b[0], oy + b[1])

        # Set colors here rather than in finalize(): the `vsk run` viewer
        # only runs finalize() on save, but it does honor layer metadata.
        colors = (self.color_1, self.color_2, self.color_3)
        for lid, layer in vsk.document.layers.items():
            if 1 <= lid <= len(colors):
                layer.set_property(vp.METADATA_FIELD_COLOR, vp.Color(colors[lid - 1]))

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")

    # ------------------------------------------------------------------
    # Cube geometry
    # ------------------------------------------------------------------

    def _ramp(self, i: int, n: int) -> float:
        return (i / (n - 1)) ** self.shift_curve if n > 1 else 0.0

    def _cube_edges(
        self, yaw: float, pitch: float, roll: float, half: float
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """Project a rotated cube to 2D (y down) and return its edges.

        Unless `show_hidden` is set, only edges bordering a face that points
        at the camera are kept, which for a convex solid is exact.
        """
        ry, rp, rr = map(math.radians, (yaw, pitch, roll))
        rot_y = np.array(
            [[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]]
        )
        # Positive pitch tips the top face toward the viewer.
        rot_x = np.array(
            [[1, 0, 0], [0, math.cos(rp), -math.sin(rp)], [0, math.sin(rp), math.cos(rp)]]
        )
        rot_z = np.array(
            [[math.cos(rr), -math.sin(rr), 0], [math.sin(rr), math.cos(rr), 0], [0, 0, 1]]
        )
        v = VERTS @ (rot_z @ rot_x @ rot_y).T

        # Camera on the +z axis; perspective=0 is orthographic.
        cam_z = 1 / self.perspective if self.perspective > 0 else math.inf
        depth = 1 - v[:, 2] / cam_z
        proj = np.column_stack([v[:, 0] / depth, -v[:, 1] / depth]) * half

        edges = set()
        for face in FACES:
            if not self.show_hidden:
                centre = v[list(face)].mean(axis=0)  # also the outward normal
                to_cam = np.array([0.0, 0.0, cam_z]) - centre
                if math.isinf(cam_z):
                    to_cam = np.array([0.0, 0.0, 1.0])
                if centre @ to_cam <= 1e-9:
                    continue
            for i in range(4):
                a, b = face[i], face[(i + 1) % 4]
                edges.add((min(a, b), max(a, b)))
        return [(proj[a], proj[b]) for a, b in sorted(edges)]

    @staticmethod
    def _page_mm(vsk: vsketch.Vsketch) -> tuple[float, float]:
        w, h = vsk.document.page_size
        px_per_mm = 96 / 25.4
        return w / px_per_mm, h / px_per_mm


if __name__ == "__main__":
    ChromaticCubesSketch.display()
