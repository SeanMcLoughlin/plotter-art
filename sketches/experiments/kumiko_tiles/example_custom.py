"""
Example Custom Tile Plugin

This is an example of how to create a custom kumiko tile plugin.
Users can copy this file and modify it to create their own tile patterns.

This example creates a "mizuhiki" (decorative cord) pattern with curved lines.
"""

import math
from typing import List, Tuple
from . import BaseTile


class MizuhikiTile(BaseTile):
    """Example custom tile - Mizuhiki (decorative cord) pattern"""

    @property
    def name(self) -> str:
        # This is the name that will be used to reference your tile
        return "mizuhiki"

    @property
    def description(self) -> str:
        # This description will be shown in tile information
        return "Mizuhiki (decorative cord) - curved lines connecting triangle points"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """
        Draw the mizuhiki pattern inside the triangle

        Args:
            vsk: The vsketch context for drawing
            triangle_coords: List of (x, y) coordinates for the triangle vertices
        """
        # Get triangle center
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3

        # Calculate edge midpoints
        midpoints = []
        for i in range(3):
            mid_x = (triangle_coords[i][0] + triangle_coords[(i+1)%3][0]) / 2
            mid_y = (triangle_coords[i][1] + triangle_coords[(i+1)%3][1]) / 2
            midpoints.append((mid_x, mid_y))

        # Draw curved lines from center to vertices
        for vertex in triangle_coords:
            self._draw_curved_line(vsk, center_x, center_y, vertex[0], vertex[1])

        # Draw curved lines from center to midpoints
        for midpoint in midpoints:
            self._draw_curved_line(vsk, center_x, center_y, midpoint[0], midpoint[1])

        # Draw curved lines connecting vertices to opposite midpoints
        for i in range(3):
            vertex = triangle_coords[i]
            opposite_midpoint = midpoints[(i+1)%3]  # Get adjacent midpoint
            self._draw_curved_line(vsk, vertex[0], vertex[1],
                                 opposite_midpoint[0], opposite_midpoint[1])

    def _draw_curved_line(self, vsk, x1: float, y1: float, x2: float, y2: float):
        """
        Draw a curved line between two points using a quadratic Bezier curve

        This is a helper method to create smooth curved lines
        """
        # Calculate control point for the curve
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Calculate perpendicular offset for curve
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)

        if length > 0:
            # Create a control point offset perpendicular to the line
            perp_x = -dy / length * 0.05  # Adjust 0.05 for curve intensity
            perp_y = dx / length * 0.05

            control_x = mid_x + perp_x
            control_y = mid_y + perp_y

            # Draw the curved line using multiple short segments
            num_segments = 8
            for i in range(num_segments):
                t1 = i / num_segments
                t2 = (i + 1) / num_segments

                # Quadratic Bezier curve formula
                p1_x = (1-t1)**2 * x1 + 2*(1-t1)*t1 * control_x + t1**2 * x2
                p1_y = (1-t1)**2 * y1 + 2*(1-t1)*t1 * control_y + t1**2 * y2

                p2_x = (1-t2)**2 * x1 + 2*(1-t2)*t2 * control_x + t2**2 * x2
                p2_y = (1-t2)**2 * y1 + 2*(1-t2)*t2 * control_y + t2**2 * y2

                vsk.line(p1_x, p1_y, p2_x, p2_y)
        else:
            # If points are the same, just draw a straight line
            vsk.line(x1, y1, x2, y2)


# Instructions for creating your own custom tile:
#
# 1. Copy this file and rename it (e.g., "my_custom_tile.py")
# 2. Change the class name (e.g., "MyCustomTile")
# 3. Change the name property to return your tile's unique name
# 4. Update the description property
# 5. Implement your drawing logic in the draw() method
# 6. Save the file in the kumiko_tiles folder
# 7. The tile will be automatically loaded when the program starts
#
# Tips:
# - Use vsk.line(x1, y1, x2, y2) to draw lines
# - Use vsk.circle(x, y, radius) to draw circles
# - triangle_coords is a list of 3 (x, y) tuples representing the triangle vertices
# - You can calculate the triangle center, edge midpoints, and other geometric properties
# - Use math functions for calculations (math.sin, math.cos, math.sqrt, etc.)
# - Keep your tile patterns simple and elegant for best results
