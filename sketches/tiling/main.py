import vsketch

import math


class TruchetTilingSketch(vsketch.SketchClass):
    """
    A VSketch program for generating Truchet tilings suitable for pen plotting.

    Truchet tiles are square tiles decorated with patterns that can be oriented
    in different ways to create complex, flowing designs when tessellated.
    """

    # Parameters for customization
    grid_width = vsketch.Param(
        20,
        min_value=1,
        max_value=200,
        step=1,
    )
    grid_height = vsketch.Param(
        20,
        min_value=1,
        max_value=200,
        step=1,
    )
    tile_size = vsketch.Param(
        2.0,
        min_value=0.1,
        max_value=50.0,
        step=0.5,
        unit="mm",
    )
    tile_type = vsketch.Param(
        "quarter_circles",
        choices=["quarter_circles", "diagonal_lines", "curves", "dots_lines", "mixed"],
    )
    line_weight = vsketch.Param(1, min_value=1, max_value=5, step=1)
    randomize_orientation = vsketch.Param(True)
    show_grid = vsketch.Param(False)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        # Set up the sketch
        vsk.size(width="9in", height="12in", landscape=True)
        vsk.scale("mm")  # Work in millimeters for precision
        vsk.strokeWeight(self.line_weight)
        vsk.stroke(1)  # Use layer 1 for main lines

        # Calculate total size and center the grid
        total_width = self.grid_width * self.tile_size
        total_height = self.grid_height * self.tile_size

        # Center on A4 landscape (297mm x 210mm)
        start_x = (297 - total_width) / 2
        start_y = (210 - total_height) / 2

        # Optional: draw grid boundaries
        if self.show_grid:
            vsk.stroke(2)  # Use layer 2 for grid
            vsk.strokeWeight(1)
            self.draw_grid(vsk, start_x, start_y, total_width, total_height)
            vsk.stroke(1)  # Back to main layer
            vsk.strokeWeight(self.line_weight)

        # Generate the tiling
        for row in range(self.grid_height):
            for col in range(self.grid_width):
                x = start_x + col * self.tile_size
                y = start_y + row * self.tile_size

                # Determine orientation
                if self.randomize_orientation:
                    orientation = int(vsk.random(4))  # 0°, 90°, 180°, 270°
                else:
                    # Use a checkerboard pattern for non-random
                    orientation = (row + col) % 2 * 2

                # Draw the tile with transformation
                with vsk.pushMatrix():
                    vsk.translate(x + self.tile_size / 2, y + self.tile_size / 2)
                    vsk.rotate(orientation * math.pi / 2)
                    vsk.translate(-self.tile_size / 2, -self.tile_size / 2)

                    self.draw_tile(vsk)

    def draw_tile(self, vsk: vsketch.Vsketch) -> None:
        """Draw a single tile based on the selected tile type"""
        if self.tile_type == "quarter_circles":
            self.draw_quarter_circles(vsk)
        elif self.tile_type == "diagonal_lines":
            self.draw_diagonal_lines(vsk)
        elif self.tile_type == "curves":
            self.draw_curves(vsk)
        elif self.tile_type == "dots_lines":
            self.draw_dots_lines(vsk)
        elif self.tile_type == "mixed":
            # Randomly choose a tile type for variety
            tile_types = ["quarter_circles", "diagonal_lines", "curves", "dots_lines"]
            chosen_index = int(vsk.random(len(tile_types)))
            chosen_type = tile_types[chosen_index]
            if chosen_type == "quarter_circles":
                self.draw_quarter_circles(vsk)
            elif chosen_type == "diagonal_lines":
                self.draw_diagonal_lines(vsk)
            elif chosen_type == "curves":
                self.draw_curves(vsk)
            else:
                self.draw_dots_lines(vsk)

    def draw_quarter_circles(self, vsk: vsketch.Vsketch) -> None:
        """Draw the classic Truchet tile with quarter circles"""
        size = self.tile_size

        # Quarter circle from top-left corner
        vsk.arc(0, 0, size, size, 0, math.pi / 2, mode="corner")

        # Quarter circle from bottom-right corner
        vsk.arc(size, size, size, size, math.pi, 3 * math.pi / 2, mode="corner")

    def draw_diagonal_lines(self, vsk: vsketch.Vsketch) -> None:
        """Draw straight diagonal line Truchet tiles"""
        size = self.tile_size

        # Two diagonal lines creating an X pattern
        vsk.line(0, 0, size, size)
        vsk.line(0, size, size, 0)

    def draw_curves(self, vsk: vsketch.Vsketch) -> None:
        """Draw curved Truchet tiles using smooth bezier curves"""
        size = self.tile_size

        # S-curve connecting opposite sides with smoother control points
        # Curve from left middle to top middle
        vsk.bezier(
            0,
            size / 2,  # start: left edge middle
            size / 4,
            size / 2,  # control point 1: gentle horizontal departure
            size / 2,
            size / 4,  # control point 2: gentle vertical approach
            size / 2,
            0,
        )  # end: top edge middle

        # Curve from bottom middle to right middle
        vsk.bezier(
            size / 2,
            size,  # start: bottom edge middle
            size / 2,
            3 * size / 4,  # control point 1: gentle vertical departure
            3 * size / 4,
            size / 2,  # control point 2: gentle horizontal approach
            size,
            size / 2,
        )  # end: right edge middle

    def draw_dots_lines(self, vsk: vsketch.Vsketch) -> None:
        """Draw a tile with dots and connecting lines"""
        size = self.tile_size
        dot_radius = size / 20

        # Draw corner dots
        vsk.circle(size / 4, size / 4, dot_radius * 2)
        vsk.circle(3 * size / 4, 3 * size / 4, dot_radius * 2)

        # Draw connecting lines
        vsk.line(size / 4, size / 4, 3 * size / 4, 3 * size / 4)  # Diagonal
        vsk.line(0, size / 2, size / 2, 0)  # Side connections
        vsk.line(size / 2, size, size, size / 2)

    def draw_grid(
        self,
        vsk: vsketch.Vsketch,
        start_x: float,
        start_y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw grid lines to show tile boundaries"""
        # Vertical lines
        for i in range(self.grid_width + 1):
            x = start_x + i * self.tile_size
            vsk.line(x, start_y, x, start_y + height)

        # Horizontal lines
        for i in range(self.grid_height + 1):
            y = start_y + i * self.tile_size
            vsk.line(start_x, y, start_x + width, y)

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        """Optimize the sketch for plotting"""
        # Apply vpype optimizations for better plotting performance
        # - linemerge: merge lines that share endpoints
        # - linesimplify: reduce unnecessary points in paths
        # - reloop: randomize the start point of closed paths
        # - linesort: optimize drawing order to minimize pen travel
        vsk.vpype("linemerge linesimplify reloop linesort")
