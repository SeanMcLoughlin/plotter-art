import vsketch
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
            xs = [p[0] for p in self.cp]
            ys = [p[1] for p in self.cp]
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)
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

                # Order intersection points on line
                cmpx = ls1[0] - ls0[0]
                cmpy = ls1[1] - ls0[1]
                intersections.sort(
                    key=lambda a: (a[0] - ls0[0]) * cmpx + (a[1] - ls0[1]) * cmpy
                )

                for j in range(len(intersections) - 1):
                    dist_sq = (intersections[j][0] - intersections[j + 1][0]) ** 2 + (
                        intersections[j][1] - intersections[j + 1][1]
                    ) ** 2
                    if dist_sq >= 0.001:
                        mid_point = (
                            (intersections[j][0] + intersections[j + 1][0]) / 2,
                            (intersections[j][1] + intersections[j + 1][1]) / 2,
                        )
                        if diff == (not p.inside(mid_point)):
                            ndp.extend([intersections[j], intersections[j + 1]])

        self.dp = ndp
        return len(self.dp) > 0

    def segment_intersect(self, l1p1, l1p2, l2p1, l2p2):
        """Check if two line segments intersect and return intersection point"""
        d = (l2p2[1] - l2p1[1]) * (l1p2[0] - l1p1[0]) - (l2p2[0] - l2p1[0]) * (
            l1p2[1] - l1p1[1]
        )
        if d == 0:
            return False

        n_a = (l2p2[0] - l2p1[0]) * (l1p1[1] - l2p1[1]) - (l2p2[1] - l2p1[1]) * (
            l1p1[0] - l2p1[0]
        )
        n_b = (l1p2[0] - l1p1[0]) * (l1p1[1] - l2p1[1]) - (l1p2[1] - l1p1[1]) * (
            l1p1[0] - l2p1[0]
        )
        ua = n_a / d
        ub = n_b / d

        if 0 <= ua <= 1 and 0 <= ub <= 1:
            return (
                l1p1[0] + ua * (l1p2[0] - l1p1[0]),
                l1p1[1] + ua * (l1p2[1] - l1p1[1]),
            )
        return False


class Polygons:
    """Container for managing multiple polygons"""

    def __init__(self):
        self.polygon_list = []

    def create(self):
        """Create a new polygon"""
        return Polygon()

    def draw(self, vsk, polygon, add_to_vis_list=True):
        """Draw polygon with clipping against existing polygons"""
        for p in self.polygon_list:
            if not polygon.boolean(p):
                break

        polygon.draw(vsk)
        if add_to_vis_list:
            self.polygon_list.append(polygon)


def vec2_add(a, b):
    """Add two 2D vectors"""
    return (a[0] + b[0], a[1] + b[1])


def vec2_sub(a, b):
    """Subtract two 2D vectors"""
    return (a[0] - b[0], a[1] - b[1])


def vec2_scale(a, s):
    """Scale a 2D vector"""
    return (a[0] * s, a[1] * s)


def vec2_distance(a, b):
    """Calculate distance between two points"""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def bezier_point(p0, p1, p2, p3, t):
    """Calculate point on cubic Bezier curve at parameter t"""
    k = 1 - t
    return (
        k * k * k * p0[0]
        + 3 * k * k * t * p1[0]
        + 3 * k * t * t * p2[0]
        + t * t * t * p3[0],
        k * k * k * p0[1]
        + 3 * k * k * t * p1[1]
        + 3 * k * t * t * p2[1]
        + t * t * t * p3[1],
    )


def generate_tile(x, y, tile_type):
    """Generate tile configuration based on type"""
    if tile_type == 0:  # Quad
        return {
            "center": (x, y),
            "lineWidth": 1,
            "points": [
                ((0, 0.5), (0, -1)),
                ((0, -0.5), (0, 1)),
                ((0.5, 0), (-1, 0)),
                ((-0.5, 0), (1, 0)),
            ],
        }
    elif tile_type == 1:  # Double Quad
        return {
            "center": (x, y),
            "lineWidth": 0.5,
            "points": [
                ((0.25, 0.5), (0, -1)),
                ((0.25, -0.5), (0, 1)),
                ((0.5, 0.25), (-1, 0)),
                ((-0.5, 0.25), (1, 0)),
                ((-0.25, 0.5), (0, -1)),
                ((-0.25, -0.5), (0, 1)),
                ((0.5, -0.25), (-1, 0)),
                ((-0.5, -0.25), (1, 0)),
            ],
        }
    elif tile_type == 2:  # Double Quad - Brick layout
        return {
            "center": (x + (0.5 if y % 2 == 0 else 0), y),
            "lineWidth": 0.5,
            "points": [
                ((0.25, 0.5), (0, -1)),
                ((0.25, -0.5), (0, 1)),
                ((0.5, 0.25), (-1, 0)),
                ((-0.5, 0.25), (1, 0)),
                ((-0.25, 0.5), (0, -1)),
                ((-0.25, -0.5), (0, 1)),
                ((0.5, -0.25), (-1, 0)),
                ((-0.5, -0.25), (1, 0)),
            ],
        }
    elif tile_type == 3:  # Double Triangle
        h = math.sqrt(3) / 4
        points = [
            ((-0.25, -h), (0, 1)),
            ((0.25, -h), (0, 1)),
            ((-1 / 3, -h / 3), (2 * h, -0.5)),
            ((-1 / 6, h / 3), (2 * h, -0.5)),
            ((1 / 3, -h / 3), (-2 * h, -0.5)),
            ((1 / 6, h / 3), (-2 * h, -0.5)),
        ]
        if x % 2 != 0:
            points = [((p[0][0], -p[0][1]), (p[1][0], -p[1][1])) for p in points]
        return {
            "center": (x * 0.5 + (0.5 if y % 2 == 0 else 0), y * h * 2),
            "lineWidth": 0.35,
            "points": points,
        }
    elif tile_type == 4:  # Hexagon
        h = math.sqrt(3) / 4
        return {
            "center": (x * 0.75, y * 2 * h + (0 if x % 2 != 0 else h)),
            "lineWidth": 0.6,
            "points": [
                ((0, -h), (0, 1)),
                ((0, h), (0, -1)),
                ((-3 / 8, -h / 2), (2 * h, 0.5)),
                ((-3 / 8, h / 2), (2 * h, -0.5)),
                ((3 / 8, -h / 2), (-2 * h, 0.5)),
                ((3 / 8, h / 2), (-2 * h, -0.5)),
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
        return (scale * (p[0] + tile_center[0]), scale * (p[1] + tile_center[1]))

    # Scale distance based on x position and gradient
    dist0 = dist * (ts(p0)[0] / 200 * -line_w_gradient + 1 - 0.5 * abs(line_w_gradient))
    dist1 = dist * (ts(p1)[0] / 200 * -line_w_gradient + 1 - 0.5 * abs(line_w_gradient))

    # Calculate start, end and control points
    sp = vec2_sub(p0, vec2_scale((d0[1], -d0[0]), dist0))
    ep = vec2_add(p1, vec2_scale((d1[1], -d1[0]), dist1))
    curve = curviness * (vec2_distance(sp, ep) ** (2 / 3)) * line_width
    sc = vec2_add(sp, vec2_scale(d0, curve))
    ec = vec2_add(ep, vec2_scale(d1, curve))

    # Generate points along the curve
    points = []
    steps = 10
    for i in range(steps + 1):
        t = i / steps
        points.append(ts(bezier_point(sp, sc, ec, ep, t)))

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
    if (
        abs(scale * tile["center"][0]) > 100 + scale
        or abs(scale * tile["center"][1]) > 100 + scale
    ):
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
            s[0],
            s[1],
            e[0],
            e[1],
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
    """

    # Configuration parameters
    scale = vsketch.Param(12, min_value=1, max_value=50, step=1)
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
        vsk.size("9in", "12in")
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
