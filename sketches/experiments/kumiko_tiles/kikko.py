"""
Kikko (Tortoise Shell) Tile Plugin

The kikko pattern is a traditional Japanese design that represents tortoise shell.
It consists of hexagonal shapes that create a honeycomb-like pattern.
"""

import math
from typing import List, Tuple
from . import BaseTile


class KikkoTile(BaseTile):
    """Kikko (tortoise shell) pattern tile"""

    @property
    def name(self) -> str:
        return "kikko"

    @property
    def description(self) -> str:
        return "Kikko (tortoise shell) - traditional Japanese hexagonal pattern"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw kikko (hexagonal) pattern inside triangle"""
        # Get triangle center
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3

        # Calculate radius for hexagon
        distances = [math.sqrt((coord[0] - center_x)**2 + (coord[1] - center_y)**2)
                    for coord in triangle_coords]
        radius = min(distances) * 0.6

        # Draw hexagon
        hexagon_points = []
        for i in range(6):
            angle = i * math.pi / 3
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            hexagon_points.append((x, y))

        # Draw hexagon edges
        for i in range(6):
            vsk.line(hexagon_points[i][0], hexagon_points[i][1],
                    hexagon_points[(i+1)%6][0], hexagon_points[(i+1)%6][1])

        # Draw inner hexagon for more detail
        inner_radius = radius * 0.5
        inner_hexagon_points = []
        for i in range(6):
            angle = i * math.pi / 3
            x = center_x + inner_radius * math.cos(angle)
            y = center_y + inner_radius * math.sin(angle)
            inner_hexagon_points.append((x, y))

        # Draw inner hexagon edges
        for i in range(6):
            vsk.line(inner_hexagon_points[i][0], inner_hexagon_points[i][1],
                    inner_hexagon_points[(i+1)%6][0], inner_hexagon_points[(i+1)%6][1])

        # Connect outer and inner hexagons
        for i in range(6):
            vsk.line(hexagon_points[i][0], hexagon_points[i][1],
                    inner_hexagon_points[i][0], inner_hexagon_points[i][1])
