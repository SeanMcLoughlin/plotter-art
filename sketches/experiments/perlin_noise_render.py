import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, CheckButtons, RadioButtons
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

# Only requires: pip install matplotlib numpy


class PerlinNoise:
    def __init__(self, seed=None):
        if seed is not None:
            np.random.seed(seed)
        self.p = np.arange(256)
        np.random.shuffle(self.p)
        self.p = np.concatenate([self.p, self.p])

    def fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def lerp(self, a, b, t):
        return a + t * (b - a)

    def grad(self, hash_val, x, y):
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h == 12 or h == 14 else 0)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x, y):
        X = int(x) & 255
        Y = int(y) & 255
        x -= int(x)
        y -= int(y)
        u = self.fade(x)
        v = self.fade(y)
        A = self.p[X] + Y
        B = self.p[X + 1] + Y
        return self.lerp(
            self.lerp(self.grad(self.p[A], x, y), self.grad(self.p[B], x - 1, y), u),
            self.lerp(
                self.grad(self.p[A + 1], x, y - 1),
                self.grad(self.p[B + 1], x - 1, y - 1),
                u,
            ),
            v,
        )

    def generate_terrain(self, width, height, scale=0.05, octaves=6, persistence=0.4):
        terrain = np.zeros((height, width))
        for y in range(height):
            for x in range(width):
                amplitude = 1.0
                frequency = scale
                noise_val = 0.0
                for octave in range(octaves):
                    noise_val += self.noise(x * frequency, y * frequency) * amplitude
                    amplitude *= persistence
                    frequency *= 2.0
                terrain[y, x] = noise_val
        return terrain


class InteractiveTerrainViewer:
    def __init__(self):
        # Set up the figure with proper layout
        self.fig = plt.figure(figsize=(16, 10))
        plt.subplots_adjust(left=0.02, bottom=0.25, right=0.98, top=0.95)

        # Main 3D plot
        self.ax_3d = self.fig.add_subplot(121, projection="3d")

        # 2D height map
        self.ax_2d = self.fig.add_subplot(122)

        # Terrain parameters
        self.terrain_params = {
            "resolution": 40,
            "scale": 0.05,
            "octaves": 6,
            "persistence": 0.4,
            "height_scale": 20.0,
            "seed": 42,
        }

        self.wireframe = False
        self.colormap = "terrain"
        self.show_axes = True  # New option to show/hide 3D axes
        self.colorbar = None  # Store colorbar reference
        self.im = None  # Store image reference for updating
        self._axes_cleared = True  # Track if axes were cleared

        # Create UI controls
        self.create_controls()

        # Generate initial terrain
        self.generate_terrain()

        # Set up interactivity
        self.setup_interaction()

    def create_controls(self):
        # Create sliders at the bottom of the figure
        slider_height = 0.03
        slider_spacing = 0.025
        slider_left = 0.15
        slider_width = 0.3

        # Scale slider
        ax_scale = plt.axes([slider_left, 0.15, slider_width, slider_height])
        self.slider_scale = Slider(
            ax_scale,
            "Scale",
            0.01,
            0.1,
            valinit=self.terrain_params["scale"],
            valfmt="%.3f",
        )
        self.slider_scale.on_changed(self.update_scale)

        # Octaves slider
        ax_octaves = plt.axes(
            [slider_left, 0.15 - slider_spacing, slider_width, slider_height]
        )
        self.slider_octaves = Slider(
            ax_octaves,
            "Octaves",
            1,
            10,
            valinit=self.terrain_params["octaves"],
            valfmt="%d",
            valstep=1,
        )
        self.slider_octaves.on_changed(self.update_octaves)

        # Persistence slider
        ax_persistence = plt.axes(
            [slider_left, 0.15 - 2 * slider_spacing, slider_width, slider_height]
        )
        self.slider_persistence = Slider(
            ax_persistence,
            "Persistence",
            0.1,
            0.8,
            valinit=self.terrain_params["persistence"],
            valfmt="%.2f",
        )
        self.slider_persistence.on_changed(self.update_persistence)

        # Height scale slider
        ax_height = plt.axes(
            [slider_left, 0.15 - 3 * slider_spacing, slider_width, slider_height]
        )
        self.slider_height = Slider(
            ax_height,
            "Height",
            5,
            50,
            valinit=self.terrain_params["height_scale"],
            valfmt="%.1f",
        )
        self.slider_height.on_changed(self.update_height)

        # Resolution slider
        ax_resolution = plt.axes(
            [slider_left, 0.15 - 4 * slider_spacing, slider_width, slider_height]
        )
        self.slider_resolution = Slider(
            ax_resolution,
            "Resolution",
            20,
            80,
            valinit=self.terrain_params["resolution"],
            valfmt="%d",
            valstep=1,
        )
        self.slider_resolution.on_changed(self.update_resolution)

        # Buttons
        button_width = 0.08
        button_height = 0.04
        button_left = 0.55

        # Generate new terrain button
        ax_generate = plt.axes([button_left, 0.15, button_width, button_height])
        self.btn_generate = Button(ax_generate, "New Terrain")
        self.btn_generate.on_clicked(self.generate_new_terrain)

        # Reset view button
        ax_reset = plt.axes(
            [button_left, 0.15 - slider_spacing, button_width, button_height]
        )
        self.btn_reset = Button(ax_reset, "Reset View")
        self.btn_reset.on_clicked(self.reset_view)

        # Isometric view button
        ax_iso = plt.axes(
            [button_left, 0.15 - 2 * slider_spacing, button_width, button_height]
        )
        self.btn_iso = Button(ax_iso, "Isometric")
        self.btn_iso.on_clicked(self.isometric_view)

        # Export button
        ax_export = plt.axes(
            [button_left, 0.15 - 3 * slider_spacing, button_width, button_height]
        )
        self.btn_export = Button(ax_export, "Export")
        self.btn_export.on_clicked(self.export_parameters)

        # Wireframe checkbox
        ax_wireframe = plt.axes(
            [button_left + button_width + 0.02, 0.15, 0.08, button_height]
        )
        self.check_wireframe = CheckButtons(
            ax_wireframe, ["Wireframe"], [self.wireframe]
        )
        self.check_wireframe.on_clicked(self.toggle_wireframe)

        # Show axes checkbox
        ax_show_axes = plt.axes(
            [
                button_left + button_width + 0.02,
                0.15 - slider_spacing,
                0.08,
                button_height,
            ]
        )
        self.check_show_axes = CheckButtons(
            ax_show_axes, ["Show Axes"], [self.show_axes]
        )
        self.check_show_axes.on_clicked(self.toggle_axes)

        # Colormap radio buttons (moved down slightly)
        ax_colormap = plt.axes([button_left + button_width + 0.12, 0.08, 0.1, 0.08])
        self.radio_colormap = RadioButtons(
            ax_colormap, ("terrain", "viridis", "plasma", "coolwarm")
        )
        self.radio_colormap.on_clicked(self.update_colormap)

    def generate_terrain(self):
        # Generate terrain data
        resolution = self.terrain_params["resolution"]
        noise_gen = PerlinNoise(self.terrain_params["seed"])

        terrain_data = noise_gen.generate_terrain(
            resolution,
            resolution,
            self.terrain_params["scale"],
            self.terrain_params["octaves"],
            self.terrain_params["persistence"],
        )

        # Normalize and scale height
        terrain_data = (terrain_data - terrain_data.min()) / (
            terrain_data.max() - terrain_data.min()
        )
        terrain_data *= self.terrain_params["height_scale"]

        # Create meshgrid
        x = np.linspace(-resolution // 2, resolution // 2, resolution)
        y = np.linspace(-resolution // 2, resolution // 2, resolution)
        self.X, self.Y = np.meshgrid(x, y)
        self.Z = terrain_data

        # Update plots
        self.update_3d_plot()
        self.update_2d_plot()

    def update_3d_plot(self):
        self.ax_3d.clear()

        if self.wireframe:
            self.ax_3d.plot_wireframe(
                self.X, self.Y, self.Z, color="black", linewidth=0.5, alpha=0.8
            )
        else:
            surf = self.ax_3d.plot_surface(
                self.X,
                self.Y,
                self.Z,
                cmap=self.colormap,
                alpha=0.9,
                antialiased=True,
                linewidth=0,
                shade=True,
            )

        # Show or hide axes based on setting
        if self.show_axes:
            self.ax_3d.set_xlabel("X")
            self.ax_3d.set_ylabel("Y")
            self.ax_3d.set_zlabel("Height")
        else:
            # Hide axis labels and ticks
            self.ax_3d.set_xlabel("")
            self.ax_3d.set_ylabel("")
            self.ax_3d.set_zlabel("")
            self.ax_3d.set_xticks([])
            self.ax_3d.set_yticks([])
            self.ax_3d.set_zticks([])
            # Hide the axis lines/panes
            self.ax_3d.grid(False)
            self.ax_3d.xaxis.pane.fill = False
            self.ax_3d.yaxis.pane.fill = False
            self.ax_3d.zaxis.pane.fill = False
            self.ax_3d.xaxis.pane.set_edgecolor("none")
            self.ax_3d.yaxis.pane.set_edgecolor("none")
            self.ax_3d.zaxis.pane.set_edgecolor("none")
            # Hide the axis spines (the outer frame)
            self.ax_3d.xaxis.line.set_color("none")
            self.ax_3d.yaxis.line.set_color("none")
            self.ax_3d.zaxis.line.set_color("none")
            # Make axes completely invisible
            self.ax_3d.set_axis_off()

        self.ax_3d.set_title(f"3D Terrain (Seed: {self.terrain_params['seed']})")

        # Set aspect ratio and limits
        max_range = (
            np.array(
                [
                    self.X.max() - self.X.min(),
                    self.Y.max() - self.Y.min(),
                    self.Z.max() - self.Z.min(),
                ]
            ).max()
            / 2.0
        )
        mid_x = (self.X.max() + self.X.min()) * 0.5
        mid_y = (self.Y.max() + self.Y.min()) * 0.5
        mid_z = (self.Z.max() + self.Z.min()) * 0.5
        self.ax_3d.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax_3d.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax_3d.set_zlim(mid_z - max_range, mid_z + max_range)

    def update_2d_plot(self):
        # Clear only the contour lines, keep the image
        if hasattr(self, "_contours"):
            try:
                for coll in self._contours.collections:
                    coll.remove()
            except AttributeError:
                # Handle different matplotlib versions
                try:
                    if hasattr(self._contours, "remove"):
                        self._contours.remove()
                    else:
                        # Fallback: just clear the whole axes and recreate
                        self.ax_2d.clear()
                        if self.im is not None:
                            self.im = None
                except:
                    pass

        if self.im is None:
            # First time setup - create image and colorbar
            if not hasattr(self, "_axes_cleared") or self._axes_cleared:
                self.ax_2d.clear()
                self._axes_cleared = False

            self.im = self.ax_2d.imshow(
                self.Z,
                cmap=self.colormap,
                origin="lower",
                extent=[self.X.min(), self.X.max(), self.Y.min(), self.Y.max()],
            )

            self.ax_2d.set_xlabel("X")
            self.ax_2d.set_ylabel("Y")
            self.ax_2d.set_title("Height Map with Contours")
            self.ax_2d.set_aspect("equal")

            # Create colorbar once
            if self.colorbar is None:
                self.colorbar = plt.colorbar(
                    self.im, ax=self.ax_2d, shrink=0.8, label="Height"
                )
        else:
            # Update existing image data
            self.im.set_array(self.Z)
            self.im.set_extent([self.X.min(), self.X.max(), self.Y.min(), self.Y.max()])

            # Update colorbar range
            self.im.set_clim(vmin=self.Z.min(), vmax=self.Z.max())
            if self.colorbar is not None:
                self.colorbar.update_normal(self.im)

        # Add new contour lines
        try:
            self._contours = self.ax_2d.contour(
                self.X,
                self.Y,
                self.Z,
                levels=8,
                colors="black",
                alpha=0.4,
                linewidths=0.5,
            )
        except Exception:
            # If contour creation fails, continue without contours
            pass

    def setup_interaction(self):
        # Add key press event handler
        self.fig.canvas.mpl_connect("key_press_event", self.on_key_press)

    def update_scale(self, val):
        self.terrain_params["scale"] = val
        self.generate_terrain()
        self.fig.canvas.draw()

    def update_octaves(self, val):
        self.terrain_params["octaves"] = int(val)
        self.generate_terrain()
        self.fig.canvas.draw()

    def update_persistence(self, val):
        self.terrain_params["persistence"] = val
        self.generate_terrain()
        self.fig.canvas.draw()

    def update_height(self, val):
        self.terrain_params["height_scale"] = val
        self.generate_terrain()
        self.fig.canvas.draw()

    def update_resolution(self, val):
        self.terrain_params["resolution"] = int(val)
        # Resolution change requires recreating the image due to size change
        if self.im is not None:
            self.im.remove()
            self.im = None
            self._axes_cleared = True
        self.generate_terrain()
        self.fig.canvas.draw()

    def generate_new_terrain(self, event):
        self.terrain_params["seed"] = np.random.randint(0, 10000)
        # Reset image for completely new terrain
        if self.im is not None:
            self.im.remove()
            self.im = None
            self._axes_cleared = True
        self.generate_terrain()
        self.fig.canvas.draw()

    def reset_view(self, event):
        self.ax_3d.view_init(elev=30, azim=45)
        self.fig.canvas.draw()

    def isometric_view(self, event):
        self.ax_3d.view_init(elev=35.26, azim=45)
        self.fig.canvas.draw()

    def toggle_wireframe(self, label):
        self.wireframe = not self.wireframe
        self.update_3d_plot()
        # No need to update 2D plot for wireframe toggle
        self.fig.canvas.draw()

    def toggle_axes(self, label):
        self.show_axes = not self.show_axes
        self.update_3d_plot()
        self.fig.canvas.draw()

    def update_colormap(self, label):
        self.colormap = label
        # Need to recreate image for colormap change
        if self.im is not None:
            self.im.remove()
            self.im = None
            self._axes_cleared = True
        self.update_3d_plot()
        self.update_2d_plot()
        self.fig.canvas.draw()

    def export_parameters(self, event):
        params = f"""# Terrain Parameters for vsketch
terrain_params = {{
    'resolution': {self.terrain_params["resolution"]},
    'scale': {self.terrain_params["scale"]:.3f},
    'octaves': {self.terrain_params["octaves"]},
    'persistence': {self.terrain_params["persistence"]:.2f},
    'height_scale': {self.terrain_params["height_scale"]:.1f},
    'seed': {self.terrain_params["seed"]}
}}

# Current viewing angle (for isometric):
elev = {self.ax_3d.elev:.1f}
azim = {self.ax_3d.azim:.1f}"""

        print("=" * 50)
        print("EXPORTED TERRAIN PARAMETERS")
        print("=" * 50)
        print(params)
        print("=" * 50)

    def on_key_press(self, event):
        if event.key == "r":
            self.generate_new_terrain(None)
        elif event.key == "w":
            self.toggle_wireframe(None)
        elif event.key == "a":
            self.toggle_axes(None)
        elif event.key == "i":
            self.isometric_view(None)
        elif event.key == "e":
            self.export_parameters(None)

    def show(self):
        plt.show()


def main():
    print("Starting Interactive 3D Terrain Viewer...")
    print("\nKeyboard shortcuts:")
    print("  R - Generate new terrain")
    print("  W - Toggle wireframe")
    print("  A - Toggle axes visibility")
    print("  I - Isometric view")
    print("  E - Export parameters")
    print("\nMouse controls:")
    print("  Left drag - Rotate 3D view")
    print("  Right drag - Pan")
    print("  Scroll - Zoom")
    print("\nAdjust sliders for real-time terrain modification!")

    viewer = InteractiveTerrainViewer()
    viewer.show()


if __name__ == "__main__":
    main()
