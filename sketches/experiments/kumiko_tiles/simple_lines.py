"""
Simple Lines Tile Plugin

A basic tile that draws simple parallel lines inside the triangle.
This serves as a good example for creating new tile types.
"""

import math
from typing import List, Tuple
from . import BaseTile


class SimpleLinesTile(BaseTile):
    """Simple parallel lines pattern tile"""

    @property
    def name(self) -> str:
        return "simple_lines"

    @property
    def description(self) -> str:
        return "Simple lines - basic parallel lines pattern"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw simple parallel lines inside triangle"""
        # Get triangle bounds
        min_x = min(coord[0] for coord in triangle_coords)
        max_x = max(coord[0] for coord in triangle_coords)
        min_y = min(coord[1] for coord in triangle_coords)
        max_y = max(coord[1] for coord in triangle_coords)

        # Calculate triangle center for reference
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3

        # Calculate triangle size for line spacing
        triangle_width = max_x - min_x
        triangle_height = max_y - min_y
        triangle_size = min(triangle_width, triangle_height)

        # Number of lines based on triangle size
        num_lines = max(2, int(triangle_size / 0.05))  # Adjust 0.05 for line density

        # Draw vertical lines
        for i in range(1, num_lines):
            t = i / num_lines
            x = min_x + t * triangle_width

            # Find intersection points with triangle edges
            intersections = []

            # Check intersection with each triangle edge
            for j in range(3):
                p1 = triangle_coords[j]
                p2 = triangle_coords[(j+1) % 3]

                # Check if vertical line intersects this edge
                if (p1[0] <= x <= p2[0]) or (p2[0] <= x <= p1[0]):
                    if p1[0] != p2[0]:  # Avoid division by zero
                        # Calculate y intersection point
                        t_edge = (x - p1[0]) / (p2[0] - p1[0])
                        y_intersect = p1[1] + t_edge * (p2[1] - p1[1])
                        intersections.append((x, y_intersect))

            # Draw line between intersection points
            if len(intersections) >= 2:
                intersections.sort(key=lambda point: point[1])  # Sort by y coordinate
                vsk.line(intersections[0][0], intersections[0][1],
                        intersections[-1][0], intersections[-1][1])

        # Draw diagonal lines for more interest
        # Calculate diagonal direction based on triangle orientation
        for i in range(3):
            vertex = triangle_coords[i]
            opposite_mid_x = (triangle_coords[(i+1)%3][0] + triangle_coords[(i+2)%3][0]) / 2
            opposite_mid_y = (triangle_coords[(i+1)%3][1] + triangle_coords[(i+2)%3][1]) / 2

            # Draw line from vertex to opposite edge midpoint
            mid_x = (vertex[0] + opposite_mid_x) / 2
            mid_y = (vertex[1] + opposite_mid_y) / 2

            # Draw partial line for subtle effect
            vsk.line(vertex[0] + (mid_x - vertex[0]) * 0.3,
                    vertex[1] + (mid_y - vertex[1]) * 0.3,
                    vertex[0] + (mid_x - vertex[0]) * 0.7,
                    vertex[1] + (mid_y - vertex[1]) * 0.7)
