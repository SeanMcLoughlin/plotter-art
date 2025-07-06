import vsketch
import numpy as np
import matplotlib.tri as mtri
import math

class KumikoGridSketch(vsketch.SketchClass):
    # Parameters
    rows = vsketch.Param(10, min_value=1, max_value=1000)
    cols = vsketch.Param(12, min_value=1, max_value=1000)
    spacing = vsketch.Param(0.25, min_value=0.01, max_value=2.0)
    vertex_connection_ratio = vsketch.Param(1.0, min_value=0.0, max_value=1.0)
    rotate_90 = vsketch.Param(False)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("letter", landscape=False)
        vsk.scale("in")

        # Set up the drawing
        vsk.stroke(1)  # Black stroke
        vsk.noFill()

        # Generate uniform points in triangular lattice pattern
        x_points, y_points = self.generate_triangular_lattice()

        # Apply rotation if specified
        if self.rotate_90:
            x_points, y_points = self.rotate_points(x_points, y_points, 90)

        # Create proper triangular grid connections
        self.draw_triangular_grid(vsk, x_points, y_points, self.rotate_90)

        # Draw frame around the grid
        self.draw_frame(vsk, x_points, y_points)

        # Connect boundary vertices to frame edges
        self.draw_boundary_connections(vsk, x_points, y_points, self.rotate_90)

    def generate_triangular_lattice(self):
        """Generate uniform points in a triangular lattice (hexagonal close-packed)"""
        x_points = []
        y_points = []

        # Calculate spacing for equilateral triangles
        h_spacing = self.spacing  # Horizontal spacing
        v_spacing = self.spacing * math.sqrt(3) / 2  # Vertical spacing for equilateral triangles

        for row in range(self.rows):
            for col in range(self.cols):
                # Offset every other row by half spacing for triangular lattice
                x_offset = (h_spacing / 2) if row % 2 == 1 else 0
                x = col * h_spacing + x_offset
                y = row * v_spacing

                x_points.append(x)
                y_points.append(y)

        # Convert to numpy arrays and center the pattern
        x_points = np.array(x_points)
        y_points = np.array(y_points)

        # Center the points on the page
        x_center = 8.5 / 2  # Letter width center (8.5 inches)
        y_center = 11 / 2   # Letter height center (11 inches)

        # Calculate current bounds
        x_min, x_max = x_points.min(), x_points.max()
        y_min, y_max = y_points.min(), y_points.max()

        # Center the pattern
        x_points = x_points - (x_min + x_max) / 2 + x_center
        y_points = y_points - (y_min + y_max) / 2 + y_center

        return x_points, y_points

    def draw_triangular_grid(self, vsk: vsketch.Vsketch, x_points, y_points, is_rotated=False):
        """Draw a proper triangular grid ensuring all vertices are connected"""

        # Create a mapping from coordinates to point indices for efficient lookup
        point_to_index = {}
        for i, (x, y) in enumerate(zip(x_points, y_points)):
            point_to_index[(round(x, 6), round(y, 6))] = i

        # Calculate spacing for connections
        h_spacing = self.spacing
        v_spacing = self.spacing * math.sqrt(3) / 2

        # Set to store unique edges to avoid duplicates
        edges = set()

        # For each point, connect to its neighbors in the triangular lattice
        for i, (x, y) in enumerate(zip(x_points, y_points)):
            # Define the 6 possible neighbors in a triangular lattice
            if is_rotated:
                # Rotated neighbor offsets (90 degrees counterclockwise)
                neighbor_offsets = [
                    (0, h_spacing),  # Up (was Right)
                    (0, -h_spacing),  # Down (was Left)
                    (-v_spacing, h_spacing/2),  # Up-left (was Down-right)
                    (-v_spacing, -h_spacing/2),  # Down-left (was Down-left)
                    (v_spacing, h_spacing/2),  # Up-right (was Up-right)
                    (v_spacing, -h_spacing/2),  # Down-right (was Up-left)
                ]
            else:
                # Original neighbor offsets
                neighbor_offsets = [
                    (h_spacing, 0),  # Right
                    (-h_spacing, 0),  # Left
                    (h_spacing/2, v_spacing),  # Down-right
                    (-h_spacing/2, v_spacing),  # Down-left
                    (h_spacing/2, -v_spacing),  # Up-right
                    (-h_spacing/2, -v_spacing),  # Up-left
                ]

            neighbors = [(x + dx, y + dy) for dx, dy in neighbor_offsets]

            # Check each neighbor and add edge if it exists
            for nx, ny in neighbors:
                neighbor_key = (round(nx, 6), round(ny, 6))
                if neighbor_key in point_to_index:
                    j = point_to_index[neighbor_key]
                    # Add edge (ensure consistent ordering to avoid duplicates)
                    edge = (min(i, j), max(i, j))
                    edges.add(edge)

        # Draw all edges based on vertex_connection_ratio
        edges_list = list(edges)
        if self.vertex_connection_ratio < 1.0:
            # Randomly select edges but ensure connectivity
            np.random.shuffle(edges_list)
            num_edges = max(1, int(len(edges_list) * self.vertex_connection_ratio))
            edges_list = edges_list[:num_edges]

        # Draw the selected edges
        for i, j in edges_list:
            vsk.line(x_points[i], y_points[i], x_points[j], y_points[j])

    def rotate_points(self, x_points, y_points, rotation_degrees):
        """Rotate points around the center by specified degrees"""
        # Convert to radians
        angle = math.radians(rotation_degrees)

        # Find center point
        center_x = np.mean(x_points)
        center_y = np.mean(y_points)

        # Translate to origin
        x_centered = x_points - center_x
        y_centered = y_points - center_y

        # Apply rotation matrix
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        x_rotated = x_centered * cos_angle - y_centered * sin_angle
        y_rotated = x_centered * sin_angle + y_centered * cos_angle

        # Translate back
        x_final = x_rotated + center_x
        y_final = y_rotated + center_y

        return x_final, y_final

    def draw_frame(self, vsk: vsketch.Vsketch, x_points, y_points):
        """Draw a rectangular frame around the grid points"""
        # Find bounds of the actual grid points
        x_min, x_max = x_points.min(), x_points.max()
        y_min, y_max = y_points.min(), y_points.max()

        # Draw the frame
        vsk.line(x_min, y_min, x_max, y_min)  # Bottom
        vsk.line(x_max, y_min, x_max, y_max)  # Right
        vsk.line(x_max, y_max, x_min, y_max)  # Top
        vsk.line(x_min, y_max, x_min, y_min)  # Left

    def draw_boundary_connections(self, vsk: vsketch.Vsketch, x_points, y_points, is_rotated=False):
            """Draw lines connecting boundary vertices to frame edges"""
            # Find frame bounds
            frame_x_min, frame_x_max = x_points.min(), x_points.max()
            frame_y_min, frame_y_max = y_points.min(), y_points.max()

            # Find boundary vertices
            boundary_vertices = self.find_boundary_vertices(x_points, y_points, is_rotated)

            # Connect each boundary vertex to the appropriate frame edge
            for vertex_idx in boundary_vertices:
                x, y = x_points[vertex_idx], y_points[vertex_idx]

                # Determine which frame edge this vertex should connect to
                # Connect to the closest frame edge
                distances = {
                    'left': abs(x - frame_x_min),
                    'right': abs(x - frame_x_max),
                    'top': abs(y - frame_y_max),
                    'bottom': abs(y - frame_y_min)
                }

                closest_edge = min(distances, key=lambda k: distances[k])

                # Draw line to the closest frame edge
                if closest_edge == 'left':
                    vsk.line(x, y, frame_x_min, y)
                elif closest_edge == 'right':
                    vsk.line(x, y, frame_x_max, y)
                elif closest_edge == 'top':
                    vsk.line(x, y, x, frame_y_max)
                elif closest_edge == 'bottom':
                    vsk.line(x, y, x, frame_y_min)

    def find_boundary_vertices(self, x_points, y_points, is_rotated=False):
        """Find vertices that are on the boundary of the triangular grid"""
        # Create a mapping from coordinates to point indices
        point_to_index = {}
        for i, (x, y) in enumerate(zip(x_points, y_points)):
            point_to_index[(round(x, 6), round(y, 6))] = i

        h_spacing = self.spacing
        v_spacing = self.spacing * math.sqrt(3) / 2
        boundary_indices = []

        # Check each point to see if it's on the boundary
        for i, (x, y) in enumerate(zip(x_points, y_points)):
            # Define the 6 possible neighbors in a triangular lattice
            if is_rotated:
                # Rotated neighbor offsets (90 degrees counterclockwise)
                neighbor_offsets = [
                    (0, h_spacing),  # Up (was Right)
                    (0, -h_spacing),  # Down (was Left)
                    (-v_spacing, h_spacing/2),  # Up-left (was Down-right)
                    (-v_spacing, -h_spacing/2),  # Down-left (was Down-left)
                    (v_spacing, h_spacing/2),  # Up-right (was Up-right)
                    (v_spacing, -h_spacing/2),  # Down-right (was Up-left)
                ]
            else:
                # Original neighbor offsets
                neighbor_offsets = [
                    (h_spacing, 0),  # Right
                    (-h_spacing, 0),  # Left
                    (h_spacing/2, v_spacing),  # Down-right
                    (-h_spacing/2, v_spacing),  # Down-left
                    (h_spacing/2, -v_spacing),  # Up-right
                    (-h_spacing/2, -v_spacing),  # Up-left
                ]

            neighbors = [(x + dx, y + dy) for dx, dy in neighbor_offsets]

            # Count how many neighbors exist
            neighbor_count = 0
            for nx, ny in neighbors:
                neighbor_key = (round(nx, 6), round(ny, 6))
                if neighbor_key in point_to_index:
                    neighbor_count += 1

            # If a point has fewer than 6 neighbors, it's on the boundary
            if neighbor_count < 6:
                boundary_indices.append(i)

        return boundary_indices

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")

if __name__ == "__main__":
    KumikoGridSketch.display()
