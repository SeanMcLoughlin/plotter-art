import numpy as np
import vsketch
import math


def fade(t):
    """Fade function for smooth interpolation"""
    return t * t * t * (t * (t * 6 - 15) + 10)


def lerp(a, b, t):
    """Linear interpolation"""
    return a + t * (b - a)


def grad(hash_val, x, y):
    """Gradient function using hash value"""
    h = hash_val & 15
    u = x if h < 8 else y
    v = y if h < 4 else (x if h == 12 or h == 14 else 0)
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


class PerlinNoise:
    def __init__(self, vsk):
        """Initialize Perlin noise generator using vsketch's random"""
        # Generate permutation table using vsketch's random
        self.p = list(range(256))
        # Shuffle using vsketch's random
        for i in range(255, 0, -1):
            j = int(vsk.random(i + 1))
            self.p[i], self.p[j] = self.p[j], self.p[i]

        # Duplicate for overflow handling
        self.p = self.p + self.p

    def noise(self, x, y):
        """Generate noise value at coordinates (x, y)"""
        # Find unit square coordinates
        X = int(x) & 255
        Y = int(y) & 255

        # Find relative coordinates within unit square
        x -= int(x)
        y -= int(y)

        # Apply fade function
        u = fade(x)
        v = fade(y)

        # Hash coordinates of square corners
        A = self.p[X] + Y
        B = self.p[X + 1] + Y

        # Blend results from corners
        return lerp(
            lerp(grad(self.p[A], x, y), grad(self.p[B], x - 1, y), u),
            lerp(grad(self.p[A + 1], x, y - 1), grad(self.p[B + 1], x - 1, y - 1), u),
            v,
        )


def generate_perlin_noise_2d(vsk, width, height, scale=0.1, octaves=4, persistence=0.5):
    """Generate 2D Perlin noise array with multiple octaves using vsketch random"""
    noise_gen = PerlinNoise(vsk)
    noise_array = np.zeros((height, width))

    for i in range(height):
        for j in range(width):
            amplitude = 1.0
            frequency = scale
            noise_val = 0.0

            # Sum multiple octaves
            for octave in range(octaves):
                x = j * frequency
                y = i * frequency
                noise_val += noise_gen.noise(x, y) * amplitude
                amplitude *= persistence
                frequency *= 2.0

            noise_array[i, j] = noise_val

    return noise_array


class Point3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def rotate_x(self, angle):
        """Rotate point around X axis"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_y = self.y * cos_a - self.z * sin_a
        new_z = self.y * sin_a + self.z * cos_a
        return Point3D(self.x, new_y, new_z)

    def rotate_y(self, angle):
        """Rotate point around Y axis"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_x = self.x * cos_a + self.z * sin_a
        new_z = -self.x * sin_a + self.z * cos_a
        return Point3D(new_x, self.y, new_z)

    def rotate_z(self, angle):
        """Rotate point around Z axis"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        new_x = self.x * cos_a - self.y * sin_a
        new_y = self.x * sin_a + self.y * cos_a
        return Point3D(new_x, new_y, self.z)

    def project_to_2d(self, scale=1.0):
        """Project 3D point to 2D screen coordinates"""
        screen_x = self.x * scale
        screen_y = self.y * scale - self.z * scale
        return (screen_x, screen_y)


class Terrain3DSketch(vsketch.SketchClass):
    # Parameters that can be controlled in vsketch GUI
    # Terrain parameters
    terrain_resolution = vsketch.Param(40, min_value=20, max_value=80)
    scale = vsketch.Param(0.05, min_value=0.01, max_value=0.1)
    octaves = vsketch.Param(6, min_value=1, max_value=10)
    persistence = vsketch.Param(0.4, min_value=0.1, max_value=0.8)
    height_scale = vsketch.Param(30.0, min_value=10.0, max_value=100.0)

    # Viewing angle parameters (defaults to isometric)
    rotation_x = vsketch.Param(
        math.radians(35.26), min_value=0, max_value=math.pi / 2
    )  # Isometric X rotation
    rotation_y = vsketch.Param(
        0.0, min_value=0, max_value=math.pi
    )  # Default Y rotation
    rotation_z = vsketch.Param(
        math.radians(45), min_value=0, max_value=math.pi
    )  # Isometric Z rotation

    # Display parameters
    draw_wireframe = vsketch.Param(True)
    draw_contours = vsketch.Param(False)
    line_weight = vsketch.Param(0.1, min_value=0.05, max_value=0.5)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        """Draw 3D isometric terrain using Perlin noise"""
        # Set up canvas
        vsk.size("400px", "600px")
        vsk.scale("px")

        # Generate terrain noise
        resolution = self.terrain_resolution
        terrain_noise = generate_perlin_noise_2d(
            vsk,
            resolution,
            resolution,
            scale=self.scale,
            octaves=self.octaves,
            persistence=self.persistence,
        )

        # Normalize noise to 0-1 range
        noise_min = terrain_noise.min()
        noise_max = terrain_noise.max()
        terrain_noise = (terrain_noise - noise_min) / (noise_max - noise_min)

        # Create 3D mesh
        mesh_3d = self.create_3d_mesh(terrain_noise, resolution)

        # Apply rotations and project to 2D
        mesh_2d = self.project_mesh_to_2d(mesh_3d, resolution)

        # Draw the mesh
        vsk.penWidth(self.line_weight)

        if self.draw_wireframe:
            self.draw_wireframe_mesh(vsk, mesh_2d, resolution)

        if self.draw_contours:
            self.draw_contour_lines(vsk, mesh_2d, terrain_noise, resolution)

    def create_3d_mesh(self, noise_array, resolution):
        """Create 3D mesh from 2D noise array"""
        mesh = []
        center = resolution // 2

        for y in range(resolution):
            row = []
            for x in range(resolution):
                # Center the coordinates around origin
                world_x = x - center
                world_y = y - center
                world_z = noise_array[y, x] * self.height_scale

                point = Point3D(world_x, world_y, world_z)
                row.append(point)
            mesh.append(row)

        return mesh

    def project_mesh_to_2d(self, mesh_3d, resolution):
        """Apply rotations and project 3D mesh to 2D"""
        mesh_2d = []

        for y in range(resolution):
            row = []
            for x in range(resolution):
                # Apply rotations
                point = mesh_3d[y][x]
                point = point.rotate_x(self.rotation_x)
                point = point.rotate_y(self.rotation_y)
                point = point.rotate_z(self.rotation_z)

                # Project to 2D and center on canvas
                screen_x, screen_y = point.project_to_2d(scale=3.0)
                screen_x += 200  # Center X
                screen_y += 300  # Center Y

                row.append((screen_x, screen_y))
            mesh_2d.append(row)

        return mesh_2d

    def draw_wireframe_mesh(self, vsk, mesh_2d, resolution):
        """Draw wireframe mesh"""
        # Draw horizontal lines
        for y in range(resolution):
            for x in range(resolution - 1):
                x1, y1 = mesh_2d[y][x]
                x2, y2 = mesh_2d[y][x + 1]
                vsk.line(x1, y1, x2, y2)

        # Draw vertical lines
        for x in range(resolution):
            for y in range(resolution - 1):
                x1, y1 = mesh_2d[y][x]
                x2, y2 = mesh_2d[y + 1][x]
                vsk.line(x1, y1, x2, y2)

    def draw_contour_lines(self, vsk, mesh_2d, noise_array, resolution):
        """Draw contour lines at specific heights"""
        contour_levels = [0.2, 0.4, 0.6, 0.8]

        for level in contour_levels:
            # Find points at this elevation level
            for y in range(resolution - 1):
                for x in range(resolution - 1):
                    # Check if contour passes through this cell
                    corners = [
                        noise_array[y, x],
                        noise_array[y, x + 1],
                        noise_array[y + 1, x],
                        noise_array[y + 1, x + 1],
                    ]

                    # Simple contour detection
                    if min(corners) <= level <= max(corners):
                        # Draw contour segment
                        x1, y1 = mesh_2d[y][x]
                        x2, y2 = mesh_2d[y][x + 1]
                        x3, y3 = mesh_2d[y + 1][x]
                        x4, y4 = mesh_2d[y + 1][x + 1]

                        # Draw lines connecting midpoints (simplified)
                        mid_x = (x1 + x2 + x3 + x4) / 4
                        mid_y = (y1 + y2 + y3 + y4) / 4
                        vsk.point(mid_x, mid_y)

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        """Finalize the sketch"""
        vsk.vpype("linemerge linesimplify reloop linesort")


# This is the main sketch that vsketch will run
if __name__ == "__main__":
    Terrain3DSketch().display()
