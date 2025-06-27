import numpy as np
import vsketch


class RibbonSurfaceSketch(vsketch.SketchClass):
    # Interactive parameters
    # Surface type: 1=Möbius, 2=Twisted Ribbon, 3=Torus Knot, 4=All Surfaces
    surface_type = vsketch.Param(1, choices=[1, 2, 3, 4])
    u_lines = vsketch.Param(100, min_value=20, max_value=200)
    v_lines = vsketch.Param(60, min_value=10, max_value=100)
    twist_factor = vsketch.Param(2.0, min_value=0.5, max_value=5.0)
    amplitude = vsketch.Param(0.25, min_value=0.1, max_value=1.0)
    frequency = vsketch.Param(2.0, min_value=0.5, max_value=5.0)
    view_angle_x = vsketch.Param(0.3, min_value=-1.57, max_value=1.57)
    view_angle_y = vsketch.Param(0.5, min_value=-1.57, max_value=1.57)
    scale_factor = vsketch.Param(8.0, min_value=2.0, max_value=15.0)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a4", landscape=False)
        vsk.scale("cm")

        # Generate and draw the selected surface(s)
        if self.surface_type == 1:  # Möbius
            self._draw_mobius_surface(vsk)
        elif self.surface_type == 2:  # Twisted Ribbon
            self._draw_twisted_ribbon_surface(vsk)
        elif self.surface_type == 3:  # Torus Knot
            self._draw_torus_knot_surface(vsk)
        else:  # All Surfaces
            self._draw_all_surfaces(vsk)

    def _draw_mobius_surface(self, vsk: vsketch.Vsketch) -> None:
        """Draw a Möbius strip surface"""
        lines = self._generate_surface_lines(
            self._mobius_surface,
            u_range=(0, 2 * np.pi),
            v_range=(-1, 1),
            u_lines=self.u_lines,
            v_lines=self.v_lines,
            radius=0.2,
            twist_factor=self.twist_factor,
        )
        self._draw_lines(vsk, lines)

    def _draw_twisted_ribbon_surface(self, vsk: vsketch.Vsketch) -> None:
        """Draw a twisted ribbon surface"""
        lines = self._generate_surface_lines(
            self._twisted_ribbon_surface,
            u_range=(0, 4 * np.pi),
            v_range=(-1, 1),
            u_lines=self.u_lines,
            v_lines=self.v_lines,
            twist_factor=self.twist_factor,
            amplitude=self.amplitude,
            frequency=self.frequency,
        )
        self._draw_lines(vsk, lines)

    def _draw_torus_knot_surface(self, vsk: vsketch.Vsketch) -> None:
        """Draw a torus knot surface"""
        lines = self._generate_surface_lines(
            self._torus_knot_surface,
            u_range=(0, 2 * np.pi),
            v_range=(-1, 1),
            u_lines=self.u_lines // 2,
            v_lines=self.v_lines // 3,
            p=2,
            q=5,
            R=1.8,
            r=0.3,
        )
        self._draw_lines(vsk, lines)

    def _draw_all_surfaces(self, vsk: vsketch.Vsketch) -> None:
        """Draw multiple intersecting surfaces"""
        # Möbius strip
        lines1 = self._generate_surface_lines(
            self._mobius_surface,
            u_range=(0, 2 * np.pi),
            v_range=(-1, 1),
            u_lines=self.u_lines,
            v_lines=self.v_lines,
            radius=0.2,
            twist_factor=self.twist_factor,
        )

        # Rotate the Möbius strip
        angle = np.pi / 3
        rotated_lines1 = []
        for x_line, y_line in lines1:
            x_rot = x_line * np.cos(angle) - y_line * np.sin(angle)
            y_rot = x_line * np.sin(angle) + y_line * np.cos(angle)
            rotated_lines1.append((x_rot, y_rot))

        # Twisted ribbon (smaller)
        lines2 = self._generate_surface_lines(
            self._twisted_ribbon_surface,
            u_range=(0, 3 * np.pi),
            v_range=(-0.8, 0.8),
            u_lines=self.u_lines // 2,
            v_lines=self.v_lines // 2,
            twist_factor=self.twist_factor * 0.8,
            amplitude=self.amplitude * 0.7,
            frequency=self.frequency * 1.5,
        )

        # Translate the twisted ribbon
        translated_lines2 = []
        for x_line, y_line in lines2:
            translated_lines2.append((x_line + 0.3, y_line - 0.2))

        # Draw all surfaces
        all_lines = rotated_lines1 + translated_lines2
        self._draw_lines(vsk, all_lines)

    def _mobius_surface(self, u, v, radius=1, twist_factor=1):
        """Defines a Möbius strip surface"""
        x = (radius + 0.3 * v * np.cos(twist_factor * u / 2)) * np.cos(u)
        y = (radius + 0.3 * v * np.cos(twist_factor * u / 2)) * np.sin(u)
        z = 0.3 * v * np.sin(twist_factor * u / 2)
        return x, y, z

    def _twisted_ribbon_surface(self, u, v, twist_factor=3, amplitude=1, frequency=2):
        """Generate a twisted ribbon surface in 3D"""
        # Base curve
        x_center = amplitude * np.sin(frequency * u)
        y_center = amplitude * np.cos(frequency * u)
        z_center = 0.5 * np.sin(twist_factor * u)

        # Create ribbon width
        width_factor = 0.3
        twist_angle = twist_factor * u

        # Tangent vector
        dx = amplitude * frequency * np.cos(frequency * u)
        dy = -amplitude * frequency * np.sin(frequency * u)
        dz = 0.5 * twist_factor * np.cos(twist_factor * u)

        # Normalize tangent
        tangent_mag = np.sqrt(dx**2 + dy**2 + dz**2)
        tangent_mag = np.where(tangent_mag == 0, 1e-8, tangent_mag)
        tx, ty = dx / tangent_mag, dy / tangent_mag

        # Create binormal
        bx = -ty
        by = tx
        bz = np.zeros_like(tx)

        # Apply twist
        bx_twisted = bx * np.cos(twist_angle) - bz * np.sin(twist_angle)
        by_twisted = by * np.cos(twist_angle)
        bz_twisted = bx * np.sin(twist_angle) + bz * np.cos(twist_angle)

        # Final surface points
        x = x_center + width_factor * v * bx_twisted
        y = y_center + width_factor * v * by_twisted
        z = z_center + width_factor * v * bz_twisted

        return x, y, z

    def _torus_knot_surface(self, u, v, p=2, q=3, R=2, r=0.5):
        """Generate a torus knot surface"""
        # Basic torus knot curve
        x_center = (R + r * np.cos(q * u)) * np.cos(p * u)
        y_center = (R + r * np.cos(q * u)) * np.sin(p * u)
        z_center = r * np.sin(q * u)

        # Tangent vector
        dx = -(R + r * np.cos(q * u)) * p * np.sin(p * u) - r * q * np.sin(
            q * u
        ) * np.cos(p * u)
        dy = (R + r * np.cos(q * u)) * p * np.cos(p * u) - r * q * np.sin(
            q * u
        ) * np.sin(p * u)
        dz = r * q * np.cos(q * u)

        # Normalize tangent
        mag = np.sqrt(dx**2 + dy**2 + dz**2)
        mag = np.maximum(mag, 1e-10)
        tx, ty = dx / mag, dy / mag

        # Normal = tangent × world_z
        nx = ty
        ny = -tx
        nz = np.zeros_like(tx)

        # Normalize normal
        nmag = np.sqrt(nx**2 + ny**2 + nz**2)
        nmag = np.maximum(nmag, 1e-10)
        nx, ny, nz = nx / nmag, ny / nmag, nz / nmag

        # Create ribbon
        ribbon_width = 0.15
        x = x_center + ribbon_width * v * nx
        y = y_center + ribbon_width * v * ny
        z = z_center + ribbon_width * v * nz

        return x, y, z

    def _project_to_2d(self, x, y, z):
        """Project 3D coordinates to 2D using rotation matrices"""
        # Rotation around X axis
        cos_x, sin_x = np.cos(self.view_angle_x), np.sin(self.view_angle_x)
        y_rot = y * cos_x - z * sin_x
        z_rot = y * sin_x + z * cos_x

        # Rotation around Y axis
        cos_y, sin_y = np.cos(self.view_angle_y), np.sin(self.view_angle_y)
        x_final = x * cos_y + z_rot * sin_y
        y_final = y_rot

        return x_final, y_final

    def _generate_surface_lines(
        self,
        surface_func,
        u_range=(0, 2 * np.pi),
        v_range=(-1, 1),
        u_lines=50,
        v_lines=20,
        **surface_params,
    ):
        """Generate line collections from a 3D surface"""
        lines = []

        # Generate u-direction lines
        v_values = np.linspace(v_range[0], v_range[1], v_lines)
        for v_val in v_values:
            u_vals = np.linspace(u_range[0], u_range[1], u_lines)
            v_vals = np.full_like(u_vals, v_val)

            x, y, z = surface_func(u_vals, v_vals, **surface_params)
            x_2d, y_2d = self._project_to_2d(x, y, z)
            lines.append((x_2d, y_2d))

        # Generate v-direction lines
        u_values = np.linspace(u_range[0], u_range[1], u_lines // 2)
        for u_val in u_values:
            v_vals = np.linspace(v_range[0], v_range[1], v_lines)
            u_vals = np.full_like(v_vals, u_val)

            x, y, z = surface_func(u_vals, v_vals, **surface_params)
            x_2d, y_2d = self._project_to_2d(x, y, z)
            lines.append((x_2d, y_2d))

        return lines

    def _draw_lines(self, vsk: vsketch.Vsketch, lines):
        """Draw the lines using vsketch"""
        if not lines:
            return

        # Find bounds for centering and scaling
        all_x = np.concatenate([x for x, y in lines if len(x) > 0])
        all_y = np.concatenate([y for x, y in lines if len(y) > 0])

        if len(all_x) == 0 or len(all_y) == 0:
            return

        x_min, x_max = np.min(all_x), np.max(all_x)
        y_min, y_max = np.min(all_y), np.max(all_y)

        # Scale and center
        scale = self.scale_factor
        center_x = 10.5  # A4 width / 2
        center_y = 14.85  # A4 height / 2
        orig_center_x = (x_max + x_min) / 2
        orig_center_y = (y_max + y_min) / 2

        with vsk.pushMatrix():
            vsk.translate(center_x, center_y)
            vsk.scale(scale)
            vsk.translate(-orig_center_x, -orig_center_y)

            for x_line, y_line in lines:
                if len(x_line) > 1:
                    vsk.polygon(list(zip(x_line, y_line)), close=False)

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    RibbonSurfaceSketch.display()
