"""
Seigaiha (Wave) Tile Plugin

The seigaiha pattern is a traditional Japanese design that represents ocean waves.
It consists of overlapping semicircular arcs that create a wave-like pattern.
"""

import math
from typing import List, Tuple
from . import BaseTile


class SeigaihaTile(BaseTile):
    """Seigaiha (wave) pattern tile"""

    @property
    def name(self) -> str:
        return "seigaiha"

    @property
    def description(self) -> str:
        return "Seigaiha (wave) - traditional Japanese pattern with overlapping semicircular arcs"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw seigaiha (wave) pattern inside triangle"""
        # Get triangle bounds
        min_x = min(coord[0] for coord in triangle_coords)
        max_x = max(coord[0] for coord in triangle_coords)
        min_y = min(coord[1] for coord in triangle_coords)
        max_y = max(coord[1] for coord in triangle_coords)

        # Draw concentric arcs
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        max_radius = min(max_x - min_x, max_y - min_y) / 2

        # Create multiple wave arcs
        for i in range(4):
            radius = max_radius * (i + 1) / 5

            # Draw partial arcs to create wave effect
            for angle_offset in [0, math.pi/3, 2*math.pi/3]:
                # Calculate arc center
                arc_center_x = center_x + radius * 0.3 * math.cos(angle_offset)
                arc_center_y = center_y + radius * 0.3 * math.sin(angle_offset)

                # Draw arc using a series of short lines
                num_segments = 16
                for j in range(num_segments):
                    angle1 = angle_offset + j * math.pi / num_segments
                    angle2 = angle_offset + (j + 1) * math.pi / num_segments

                    x1 = arc_center_x + radius * math.cos(angle1)
                    y1 = arc_center_y + radius * math.sin(angle1)
                    x2 = arc_center_x + radius * math.cos(angle2)
                    y2 = arc_center_y + radius * math.sin(angle2)

                    # Only draw if points are within reasonable bounds
                    if (min_x <= x1 <= max_x and min_y <= y1 <= max_y and
                        min_x <= x2 <= max_x and min_y <= y2 <= max_y):
                        vsk.line(x1, y1, x2, y2)
