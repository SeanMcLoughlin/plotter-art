#!/usr/bin/env python3
"""
Bezier Truchet tiles. Created by Reinder Nijhoff 2019 - @reindernijhoff
Ported to vsketch with numpy optimizations
"""

import vsketch
import numpy as np
import math
import random


class Polygon:
    """Polygon class for clipping operations"""

    def __init__(self):
        self.cp = []  # clip path: array of (x,y) pairs
        self.dp = []  # 2d lines [(x0,y0), (x1,y1)] to draw
        self.aabb = []  # AABB bounding box

    def add_points(self, *points):
        """Add points to clip path and update bounding box"""
        self.cp.extend(points)

        if self.cp:
            points_array = np.array(self.cp)
            xmin, ymin = np.min(points_array, axis=0)
            xmax, ymax = np.max(points_array, axis=0)
            self.aabb = [
                (xmin + xmax) / 2,
                (ymin + ymax) / 2,
                (xmax - xmin) / 2,
                (ymax - ymin) / 2,
            ]

    def add_segments(self, *points):
        """Add segments (pairs of points)"""
        self.dp.extend(points)

    def add_outline(self):
        """Add outline segments from clip path"""
        for i in range(len(self.cp)):
            self.dp.extend([self.cp[i], self.cp[(i + 1) % len(self.cp)]])

    def draw(self, vsk):
        """Draw the polygon using vsketch"""
        for i in range(0, len(self.dp), 2):
            vsk.line(self.dp[i][0], self.dp[i][1], self.dp[i + 1][0], self.dp[i + 1][1])

    def inside(self, p):
        """Check if point p is inside the polygon"""
        intersections = 0
        for i in range(len(self.cp)):
            if self.segment_intersect(
                p, (0.1, -1000), self.cp[i], self.cp[(i + 1) % len(self.cp)]
            ):
                intersections += 1
        return intersections & 1

    def boolean(self, p, diff=True):
        """Boolean operation with polygon p"""
        # Bounding box optimization
        if len(p.aabb) >= 4 and len(self.aabb) >= 4:
            if (
                abs(self.aabb[0] - p.aabb[0]) - (p.aabb[2] + self.aabb[2]) >= 0
                and abs(self.aabb[1] - p.aabb[1]) - (p.aabb[3] + self.aabb[3]) >= 0
            ):
                return len(self.dp) > 0

        # Polygon diff algorithm
        ndp = []
        for i in range(0, len(self.dp), 2):
            ls0 = self.dp[i]
            ls1 = self.dp[i + 1]

            # Find all intersections with clip path
            intersections = []
            for j in range(len(p.cp)):
                pint = self.segment_intersect(
                    ls0, ls1, p.cp[j], p.cp[(j + 1) % len(p.cp)]
                )
                if pint is not False:
                    intersections.append(pint)

            if len(intersections) == 0:
                # No intersections, check if inside or outside
                if diff == (not p.inside(ls0)):
                    ndp.extend([ls0, ls1])
            else:
                intersections.extend([ls0, ls1])

                # Order intersection points on line using numpy
                ls0_arr = np.array(ls0)
                ls1_arr = np.array(ls1)
                direction = ls1_arr - ls0_arr

                intersections.sort(
                    key=lambda a: np.dot(np.array(a) - ls0_arr, direction)
                )

                for j in range(len(intersections) - 1):
                    p1_arr = np.array(intersections[j])
                    p2_arr = np.array(intersections[j + 1])
                    dist_sq = np.sum((p1_arr - p2_arr) ** 2)

                    if dist_sq >= 0.001:
                        mid_point = (p1_arr + p2_arr) / 2
                        if diff == (not p.inside(tuple(mid_point))):
                            ndp.extend([intersections[j], intersections[j + 1]])

        self.dp = ndp
        return len(self.dp) > 0

    def segment_intersect(self, l1p1, l1p2, l2p1, l2p2):
        """Check if two line segments intersect and return intersection point"""
        l1p1_arr = np.array(l1p1)
        l1p2_arr = np.array(l1p2)
        l2p1_arr = np.array(l2p1)
        l2p2_arr = np.array(l2p2)

        l1_dir = l1p2_arr - l1p1_arr
        l2_dir = l2p2_arr - l2p1_arr

        # Cross product for 2D vectors
        d = l2_dir[1] * l1_dir[0] - l2_dir[0] * l1_dir[1]
        if abs(d) < 1e-10:  # Parallel lines
            return False

        diff = l1p1_arr - l2p1_arr
        n_a = l2_dir[0] * diff[1] - l2_dir[1] * diff[0]
        n_b = l1_dir[0] * diff[1] - l1_dir[1] * diff[0]
        ua = n_a / d
        ub = n_b / d

        if 0 <= ua <= 1 and 0 <= ub <= 1:
            intersection = l1p1_arr + ua * l1_dir
            return tuple(intersection)
        return False


class Polygons:
    """Container for managing multiple polygons"""

    def __init__(self):
        self.polygon_list = []

    def create(self):
        """Create a new polygon"""
        return Polygon()

    # def draw(self, vsk, polygon, add_to_vis_list=True):
    #     """Draw polygon with clipping against existing polygons"""
    #     for p in self.polygon_list:
    #         if not polygon.boolean(p):
    #             break

    #     polygon.draw(vsk)
    #     if add_to_vis_list:
    #         self.polygon_list.append(polygon)

    def draw(self, vsk, polygon, add_to_vis_list=True):
        # Simple spatial culling instead of expensive boolean ops
        if len(self.polygon_list) > 100:  # Only check recent polygons
            recent_polys = self.polygon_list[-100:]
        else:
            recent_polys = self.polygon_list

        for p in recent_polys:
            if not polygon.boolean(p):
                break

        polygon.draw(vsk)
        if add_to_vis_list:
            self.polygon_list.append(polygon)


def bezier_point(p0, p1, p2, p3, t):
    """Calculate point on cubic Bezier curve at parameter t using numpy"""
    p0_arr = np.array(p0)
    p1_arr = np.array(p1)
    p2_arr = np.array(p2)
    p3_arr = np.array(p3)

    k = 1 - t
    result = (
        k**3 * p0_arr + 3 * k**2 * t * p1_arr + 3 * k * t**2 * p2_arr + t**3 * p3_arr
    )
    return tuple(result)


def generate_tile(x, y, tile_type):
    """Generate tile configuration based on type"""
    if tile_type == 0:  # Quad
        return {
            "center": np.array([x, y]),
            "lineWidth": 1,
            "points": [
                (np.array([0, 0.5]), np.array([0, -1])),
                (np.array([0, -0.5]), np.array([0, 1])),
                (np.array([0.5, 0]), np.array([-1, 0])),
                (np.array([-0.5, 0]), np.array([1, 0])),
            ],
        }
    elif tile_type == 1:  # Double Quad
        return {
            "center": np.array([x, y]),
            "lineWidth": 0.5,
            "points": [
                (np.array([0.25, 0.5]), np.array([0, -1])),
                (np.array([0.25, -0.5]), np.array([0, 1])),
                (np.array([0.5, 0.25]), np.array([-1, 0])),
                (np.array([-0.5, 0.25]), np.array([1, 0])),
                (np.array([-0.25, 0.5]), np.array([0, -1])),
                (np.array([-0.25, -0.5]), np.array([0, 1])),
                (np.array([0.5, -0.25]), np.array([-1, 0])),
                (np.array([-0.5, -0.25]), np.array([1, 0])),
            ],
        }
    elif tile_type == 2:  # Double Quad - Brick layout
        center_x = x + (0.5 if y % 2 == 0 else 0)
        return {
            "center": np.array([center_x, y]),
            "lineWidth": 0.5,
            "points": [
                (np.array([0.25, 0.5]), np.array([0, -1])),
                (np.array([0.25, -0.5]), np.array([0, 1])),
                (np.array([0.5, 0.25]), np.array([-1, 0])),
                (np.array([-0.5, 0.25]), np.array([1, 0])),
                (np.array([-0.25, 0.5]), np.array([0, -1])),
                (np.array([-0.25, -0.5]), np.array([0, 1])),
                (np.array([0.5, -0.25]), np.array([-1, 0])),
                (np.array([-0.5, -0.25]), np.array([1, 0])),
            ],
        }
    elif tile_type == 3:  # Double Triangle
        h = math.sqrt(3) / 4
        points = [
            (np.array([-0.25, -h]), np.array([0, 1])),
            (np.array([0.25, -h]), np.array([0, 1])),
            (np.array([-1 / 3, -h / 3]), np.array([2 * h, -0.5])),
            (np.array([-1 / 6, h / 3]), np.array([2 * h, -0.5])),
            (np.array([1 / 3, -h / 3]), np.array([-2 * h, -0.5])),
            (np.array([1 / 6, h / 3]), np.array([-2 * h, -0.5])),
        ]
        if x % 2 != 0:
            points = [
                (np.array([p[0][0], -p[0][1]]), np.array([p[1][0], -p[1][1]]))
                for p in points
            ]
        return {
            "center": np.array([x * 0.5 + (0.5 if y % 2 == 0 else 0), y * h * 2]),
            "lineWidth": 0.35,
            "points": points,
        }
    elif tile_type == 4:  # Hexagon
        h = math.sqrt(3) / 4
        center_x = x * 0.75
        center_y = y * 2 * h + (0 if x % 2 != 0 else h)
        return {
            "center": np.array([center_x, center_y]),
            "lineWidth": 0.6,
            "points": [
                (np.array([0, -h]), np.array([0, 1])),
                (np.array([0, h]), np.array([0, -1])),
                (np.array([-3 / 8, -h / 2]), np.array([2 * h, 0.5])),
                (np.array([-3 / 8, h / 2]), np.array([2 * h, -0.5])),
                (np.array([3 / 8, -h / 2]), np.array([-2 * h, 0.5])),
                (np.array([3 / 8, h / 2]), np.array([-2 * h, -0.5])),
            ],
        }


def add_bezier(
    polygon,
    p0,
    d0,
    p1,
    d1,
    dist,
    tile_center,
    line_width,
    scale,
    line_w_gradient,
    curviness,
    as_edge=True,
    as_line=True,
):
    """Add a Bezier curve to polygon"""

    # Transform function
    def ts(p):
        transformed = scale * (p + tile_center)
        return tuple(transformed)

    # Scale distance based on x position and gradient
    ts_p0 = ts(p0)
    ts_p1 = ts(p1)
    dist0 = dist * (ts_p0[0] / 200 * -line_w_gradient + 1 - 0.5 * abs(line_w_gradient))
    dist1 = dist * (ts_p1[0] / 200 * -line_w_gradient + 1 - 0.5 * abs(line_w_gradient))

    # Calculate start, end and control points using numpy
    perpendicular_d0 = np.array([d0[1], -d0[0]])
    perpendicular_d1 = np.array([d1[1], -d1[0]])

    sp = p0 - perpendicular_d0 * dist0
    ep = p1 + perpendicular_d1 * dist1

    curve_strength = curviness * (np.linalg.norm(sp - ep) ** (2 / 3)) * line_width
    sc = sp + d0 * curve_strength
    ec = ep + d1 * curve_strength

    # Generate points along the curve
    points = []
    steps = 10
    for i in range(steps + 1):
        t = i / steps
        point = bezier_point(sp, sc, ec, ep, t)
        points.append(ts(np.array(point)))

    if as_edge:
        polygon.add_points(*points)
    if as_line:
        for i in range(steps):
            polygon.add_segments(points[i], points[i + 1])


def draw_tile(
    vsk, tile, polys, scale, line_width, inner_lines, line_w_gradient, curviness
):
    """Draw a single tile"""
    # Early discard if outside visible area
    center = tile["center"]
    if abs(scale * center[0]) > 100 + scale or abs(scale * center[1]) > 100 + scale:
        return

    lw = line_width * tile["lineWidth"]

    # Shuffle points for random connections
    points = tile["points"][:]
    random.shuffle(points)

    # Create and draw Bezier-based polygons for each connection
    for i in range(0, len(points), 2):
        s = points[i]
        e = points[i + 1]
        polygon = polys.create()

        # Add main bezier curves
        add_bezier(
            polygon,
            s[0],  # position
            s[1],  # direction
            e[0],  # position
            e[1],  # direction
            lw,
            tile["center"],
            tile["lineWidth"],
            scale,
            line_w_gradient,
            curviness,
        )
        add_bezier(
            polygon,
            e[0],
            e[1],
            s[0],
            s[1],
            lw,
            tile["center"],
            tile["lineWidth"],
            scale,
            line_w_gradient,
            curviness,
        )

        # Add inner lines
        for j in range(inner_lines):
            dist = 2 * lw * (j + 1) / (inner_lines + 1) - lw
            add_bezier(
                polygon,
                e[0],
                e[1],
                s[0],
                s[1],
                dist,
                tile["center"],
                tile["lineWidth"],
                scale,
                line_w_gradient,
                curviness,
                as_edge=False,
                as_line=True,
            )

        polys.draw(vsk, polygon)


class BezierTruchetSketch(vsketch.SketchClass):
    """
    Bezier Truchet tiles sketch for vsketch.

    Creates complex Truchet patterns using Bezier curves with various tile types
    including quad, double quad, triangular, and hexagonal patterns.
    Optimized with numpy for better performance.
    """

    # Configuration parameters
    scale = vsketch.Param(50, min_value=25, max_value=200, step=1)
    tile_type = vsketch.Param(
        1,
        min_value=0,
        max_value=4,
        step=1,
        choices=[
            0,
            1,
            2,
            3,
            4,
        ],  # Quad, Double Quad, Double Quad/Brick, Double Triangle, Hexagon
    )
    line_width = vsketch.Param(0.4, min_value=0.1, max_value=2.0, step=0.1)
    curviness = vsketch.Param(0.95, min_value=0.0, max_value=1.0, step=0.05)
    inner_lines = vsketch.Param(2, min_value=0, max_value=9, step=1)
    line_w_gradient = vsketch.Param(0.0, min_value=-1.0, max_value=1.0, step=0.1)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        # Set up the sketch
        vsk.size("10in", "10in")
        vsk.scale("mm")
        vsk.stroke(1)
        vsk.strokeWeight(1)

        # Set random seed for reproducible results
        vsk.randomSeed(42)
        random.seed(42)

        # Create polygons container
        polys = Polygons()

        # Calculate grid size
        s = int(200 / self.scale) + 2

        # Center the drawing
        vsk.translate(148.5, 148.5)  # Center on 10in x 10in (297mm x 297mm)

        # Draw tiles
        for i in range(s * s * 4):
            y = i // (s * 2) - s
            x = (i % (s * 2)) - s

            tile = generate_tile(x, y, self.tile_type)
            draw_tile(
                vsk,
                tile,
                polys,
                self.scale,
                self.line_width,
                self.inner_lines,
                self.line_w_gradient,
                self.curviness,
            )

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        """Optimize the sketch for plotting"""
        # Apply vpype optimizations for better plotting performance
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    BezierTruchetSketch.display()
