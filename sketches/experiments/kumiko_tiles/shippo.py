"""
Shippo (Seven Treasures) Tile Plugin

The shippo pattern is a traditional Japanese design that represents the seven treasures.
It consists of interlocking circles that create a decorative overlapping pattern.
"""

import math
from typing import List, Tuple
from . import BaseTile


class ShippoTile(BaseTile):
    """Shippo (seven treasures) pattern tile"""

    @property
    def name(self) -> str:
        return "shippo"

    @property
    def description(self) -> str:
        return "Shippo (seven treasures) - traditional Japanese pattern with interlocking circles"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw shippo (interlocking circles) pattern inside triangle"""
        # Calculate triangle properties
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3

        # Calculate average edge length for sizing circles
        edge_lengths = []
        for i in range(3):
            p1 = triangle_coords[i]
            p2 = triangle_coords[(i+1) % 3]
            length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            edge_lengths.append(length)

        avg_edge_length = sum(edge_lengths) / len(edge_lengths)
        base_radius = avg_edge_length * 0.25

        # Draw circles at triangle vertices
        for coord in triangle_coords:
            vsk.circle(coord[0], coord[1], base_radius)

        # Draw circles at edge midpoints
        for i in range(3):
            mid_x = (triangle_coords[i][0] + triangle_coords[(i+1)%3][0]) / 2
            mid_y = (triangle_coords[i][1] + triangle_coords[(i+1)%3][1]) / 2
            vsk.circle(mid_x, mid_y, base_radius * 0.7)

        # Draw central circle
        vsk.circle(center_x, center_y, base_radius * 0.5)

        # Add smaller interlocking circles for more detail
        for i in range(3):
            # Position circles between center and vertices
            vertex = triangle_coords[i]
            inter_x = center_x + (vertex[0] - center_x) * 0.6
            inter_y = center_y + (vertex[1] - center_y) * 0.6
            vsk.circle(inter_x, inter_y, base_radius * 0.3)
