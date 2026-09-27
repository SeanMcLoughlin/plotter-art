"""
Yabane (Arrow Feather) Tile Plugin

The yabane pattern is a traditional Japanese design that represents arrow feathers.
It consists of arrow-like lines with small perpendicular feather details.
"""

import math
from typing import List, Tuple
from . import BaseTile


class YabaneTile(BaseTile):
    """Yabane (arrow feather) pattern tile"""

    @property
    def name(self) -> str:
        return "yabane"

    @property
    def description(self) -> str:
        return "Yabane (arrow feather) - traditional Japanese pattern with arrow-like lines and feather details"

    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw yabane (arrow feather) pattern inside triangle"""
        # Get triangle center
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3

        # Calculate average edge length for sizing
        edge_lengths = []
        for i in range(3):
            p1 = triangle_coords[i]
            p2 = triangle_coords[(i+1) % 3]
            length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            edge_lengths.append(length)

        avg_edge_length = sum(edge_lengths) / len(edge_lengths)
        feather_size = avg_edge_length * 0.08

        # Draw arrow-like patterns from center
        for i in range(3):
            # Line to vertex (main arrow shaft)
            vertex = triangle_coords[i]
            vsk.line(center_x, center_y, vertex[0], vertex[1])

            # Calculate direction vector
            dx = vertex[0] - center_x
            dy = vertex[1] - center_y
            length = math.sqrt(dx**2 + dy**2)

            if length > 0:
                # Normalize direction
                dx_norm = dx / length
                dy_norm = dy / length

                # Perpendicular direction for feathers
                perp_x = -dy_norm * feather_size
                perp_y = dx_norm * feather_size

                # Draw multiple feathers along the arrow shaft
                num_feathers = 3
                for j in range(1, num_feathers + 1):
                    # Position feathers at regular intervals
                    t = j / (num_feathers + 1)
                    feather_x = center_x + t * dx
                    feather_y = center_y + t * dy

                    # Draw feather lines (perpendicular to main line)
                    vsk.line(feather_x - perp_x, feather_y - perp_y,
                            feather_x + perp_x, feather_y + perp_y)

                    # Draw angled feather lines for more detail
                    angle_offset = 0.3
                    angled_perp_x = perp_x * math.cos(angle_offset) - perp_y * math.sin(angle_offset)
                    angled_perp_y = perp_x * math.sin(angle_offset) + perp_y * math.cos(angle_offset)

                    vsk.line(feather_x, feather_y,
                            feather_x + angled_perp_x, feather_y + angled_perp_y)
                    vsk.line(feather_x, feather_y,
                            feather_x - angled_perp_x, feather_y - angled_perp_y)

        # Draw lines to edge midpoints for additional detail
        for i in range(3):
            mid_x = (triangle_coords[i][0] + triangle_coords[(i+1)%3][0]) / 2
            mid_y = (triangle_coords[i][1] + triangle_coords[(i+1)%3][1]) / 2

            # Draw line from center to midpoint
            vsk.line(center_x, center_y, mid_x, mid_y)

            # Add a small feather at the midpoint
            dx = mid_x - center_x
            dy = mid_y - center_y
            length = math.sqrt(dx**2 + dy**2)

            if length > 0:
                dx_norm = dx / length
                dy_norm = dy / length
                perp_x = -dy_norm * feather_size * 0.7
                perp_y = dx_norm * feather_size * 0.7

                vsk.line(mid_x - perp_x, mid_y - perp_y,
                        mid_x + perp_x, mid_y + perp_y)
