"""
Asanoha (Hemp Leaf) Tile Plugin

The asanoha pattern is a traditional Japanese design that resembles hemp leaves.
It consists of lines radiating from the center to create a star-like pattern.
"""

import math
from typing import List, Tuple
from . import BaseTile


class AsanohaTile(BaseTile):
    """Asanoha (hemp leaf) pattern tile"""

    @property
    def name(self) -> str:
        return "asanoha"

    @property
    def description(self) -> str:
        return "Asanoha (hemp leaf) - traditional Japanese pattern with radiating lines"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw asanoha (hemp leaf) pattern inside triangle"""
        # Get triangle center
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3

        # Draw lines from center to each vertex
        for coord in triangle_coords:
            vsk.line(center_x, center_y, coord[0], coord[1])

        # Draw lines from center to edge midpoints
        for i in range(3):
            mid_x = (triangle_coords[i][0] + triangle_coords[(i+1)%3][0]) / 2
            mid_y = (triangle_coords[i][1] + triangle_coords[(i+1)%3][1]) / 2
            vsk.line(center_x, center_y, mid_x, mid_y)
