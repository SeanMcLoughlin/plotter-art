import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
import numpy as np


class RippleLineGenerator:
    def __init__(self):
        pass

    def generate_ripples(self, width, height, ripple_list):
        """Generate water ripple pattern from list of ripples with individual parameters"""
        x = np.arange(width)
        y = np.arange(height)
        X, Y = np.meshgrid(x, y)

        ripples = np.zeros((height, width))

        for ripple in ripple_list:
            center_x, center_y = ripple["center"]
            frequency = ripple["frequency"]
            amplitude = ripple["amplitude"]
            decay = ripple["decay"]

            # Calculate distance from this center
            distance = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)

            # Create ripple pattern
            single_ripple = amplitude * np.sin(2 * np.pi * frequency * distance)

            # Apply decay with distance
            decay_factor = np.exp(-decay * distance)
            single_ripple *= decay_factor

            ripples += single_ripple

        return ripples


class AdvancedRippleLineViewer:
    def __init__(self):
        # Set up the figure
        self.fig = plt.figure(figsize=(18, 10))
        plt.subplots_adjust(left=0.02, bottom=0.3, right=0.98, top=0.95)

        # Main 3D line distortion plot (rotatable)
        self.ax_3d = self.fig.add_subplot(121, projection="3d")

        # Ripple height map
        self.ax_ripples = self.fig.add_subplot(122)

        # Parameters
        self.params = {
            "resolution": 200,
            "line_spacing": 4,
            "line_direction": "vertical",
            "distortion_scale": 15.0,
            "manual_mode": True,
        }

        # Current ripple parameters (for new ripples)
        self.current_ripple_params = {
            "frequency": 0.08,
            "amplitude": 1.0,
            "decay": 0.02,
        }

        # List of ripples with individual parameters
        self.ripple_list = []
        self.selected_ripple_index = None

        # Drag state
        self.dragging = False
        self.drag_ripple_index = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.colorbar = None
        self.im = None
        self._axes_cleared = True

        # Initialize marker and text tracking lists
        self._ripple_markers = []
        self._ripple_texts = []

        # Flag to prevent pattern generation during slider updates
        self._updating_sliders = False

        # Create UI controls
        self.create_controls()

        # Generate initial pattern
        self.generate_pattern()

        # Set up interactivity
        self.setup_interaction()

    def create_controls(self):
        # Create sliders at the bottom of the figure
        slider_height = 0.025
        slider_spacing = 0.03
        slider_left = 0.1
        slider_width = 0.25

        # Current ripple parameters (for new ripples or editing selected)
        ax_frequency = plt.axes((slider_left, 0.22, slider_width, slider_height))
        self.slider_frequency = Slider(
            ax_frequency,
            "Frequency",
            0.01,
            0.2,
            valinit=self.current_ripple_params["frequency"],
            valfmt="%.3f",
        )
        self.slider_frequency.on_changed(self.update_frequency)

        ax_amplitude = plt.axes(
            (slider_left, 0.22 - slider_spacing, slider_width, slider_height)
        )
        self.slider_amplitude = Slider(
            ax_amplitude,
            "Amplitude",
            0.1,
            3.0,
            valinit=self.current_ripple_params["amplitude"],
            valfmt="%.2f",
        )
        self.slider_amplitude.on_changed(self.update_amplitude)

        ax_decay = plt.axes(
            (slider_left, 0.22 - 2 * slider_spacing, slider_width, slider_height)
        )
        self.slider_decay = Slider(
            ax_decay,
            "Decay",
            0.005,
            0.1,
            valinit=self.current_ripple_params["decay"],
            valfmt="%.3f",
        )
        self.slider_decay.on_changed(self.update_decay)

        # Global parameters
        ax_spacing = plt.axes(
            (slider_left, 0.22 - 3 * slider_spacing, slider_width, slider_height)
        )
        self.slider_spacing = Slider(
            ax_spacing,
            "Line Spacing",
            1,
            10,
            valinit=self.params["line_spacing"],
            valfmt="%d",
            valstep=1,
        )
        self.slider_spacing.on_changed(self.update_spacing)

        ax_distortion = plt.axes(
            (slider_left, 0.22 - 4 * slider_spacing, slider_width, slider_height)
        )
        self.slider_distortion = Slider(
            ax_distortion,
            "Distortion",
            1,
            50,
            valinit=self.params["distortion_scale"],
            valfmt="%.1f",
        )
        self.slider_distortion.on_changed(self.update_distortion)

        # Buttons - reorganized to avoid overlaps
        button_width = 0.08
        button_height = 0.035
        button_left = 0.4
        button_spacing = 0.1

        # Clear ripples button
        ax_clear = plt.axes((button_left, 0.20, button_width, button_height))
        self.btn_clear = Button(ax_clear, "Clear All")
        self.btn_clear.on_clicked(self.clear_ripples)

        # Delete selected ripple button
        ax_delete = plt.axes(
            (button_left + button_spacing, 0.20, button_width, button_height)
        )
        self.btn_delete = Button(ax_delete, "Delete Selected")
        self.btn_delete.on_clicked(self.delete_selected_ripple)

        # Export button
        ax_export = plt.axes((button_left, 0.15, button_width, button_height))
        self.btn_export = Button(ax_export, "Export")
        self.btn_export.on_clicked(self.export_parameters)

        # Reset view button
        ax_reset_view = plt.axes(
            (button_left + button_spacing, 0.15, button_width, button_height)
        )
        self.btn_reset_view = Button(ax_reset_view, "Reset View")
        self.btn_reset_view.on_clicked(self.reset_view)

        # Isometric view button
        ax_iso = plt.axes(
            (button_left + button_spacing, 0.10, button_width, button_height)
        )
        self.btn_iso = Button(ax_iso, "Isometric")
        self.btn_iso.on_clicked(self.isometric_view)

        # Direction radio buttons - moved to bottom right corner
        ax_direction = plt.axes((0.85, 0.02, 0.12, 0.08))
        self.radio_direction = RadioButtons(ax_direction, ("vertical", "horizontal"))
        self.radio_direction.on_clicked(self.update_direction)

        # Add ripple info text
        self.info_text = self.fig.text(
            0.02,
            0.02,
            "",
            fontsize=10,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8),
        )
        self.update_info_text()

    def generate_pattern(self):
        resolution = self.params["resolution"]

        # Generate ripple height map
        ripple_gen = RippleLineGenerator()

        if len(self.ripple_list) == 0:
            # No ripples - create flat surface

            self.ripple_data = np.zeros((resolution, resolution))
        else:
            self.ripple_data = ripple_gen.generate_ripples(
                resolution, resolution, self.ripple_list
            )

        # Update plots - complete redraw each time
        try:
            self.update_3d_plot()
        except Exception:
            pass

        try:
            self.update_ripple_plot()
        except Exception:
            import traceback

            traceback.print_exc()

        try:
            self.update_info_text()
        except Exception:
            pass

    def update_3d_plot(self):
        self.ax_3d.clear()

        resolution = self.params["resolution"]
        line_spacing = self.params["line_spacing"]
        distortion_scale = self.params["distortion_scale"]

        # Remove all axes elements for clean view
        self.ax_3d.set_axis_off()

        if self.params["line_direction"] == "vertical":
            # Vertical lines distorted by ripples
            for x in range(0, resolution, line_spacing):
                if x < resolution:
                    line_heights = self.ripple_data[:, x]
                    y_coords = np.arange(len(line_heights))
                    x_distorted = x + line_heights * distortion_scale
                    z_coords = line_heights  # Use height for 3D effect

                    self.ax_3d.plot(
                        x_distorted, y_coords, z_coords, "k-", linewidth=0.8
                    )
        else:
            # Horizontal lines distorted by ripples
            for y in range(0, resolution, line_spacing):
                if y < resolution:
                    line_heights = self.ripple_data[y, :]
                    x_coords = np.arange(len(line_heights))
                    y_distorted = y + line_heights * distortion_scale
                    z_coords = line_heights  # Use height for 3D effect

                    self.ax_3d.plot(
                        x_coords, y_distorted, z_coords, "k-", linewidth=0.8
                    )

        # Mark ripple centers in 3D
        for i, ripple in enumerate(self.ripple_list):
            center_x, center_y = ripple["center"]
            z_height = (
                self.ripple_data[center_y, center_x]
                if center_y < resolution and center_x < resolution
                else 0
            )

            color = "red" if i == self.selected_ripple_index else "blue"
            marker_size = 100 if i == self.selected_ripple_index else 50
            self.ax_3d.scatter(
                [center_x], [center_y], c=color, s=marker_size, alpha=0.8
            )

        # Set limits and aspect
        self.ax_3d.set_xlim(0, resolution)
        self.ax_3d.set_ylim(0, resolution)
        if len(self.ripple_list) > 0:
            z_min, z_max = self.ripple_data.min(), self.ripple_data.max()
            z_range = max(abs(z_min), abs(z_max), 1)
            self.ax_3d.set_zlim(-z_range, z_range)  # type: ignore

        self.ax_3d.set_title("3D Lines (Drag to Rotate View)")

        # Add text overlay to make it clear
        self.ax_3d.text2D(  # type: ignore
            0.02,
            0.98,
            "Drag to rotate view",
            transform=self.ax_3d.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
        )

    def update_ripple_plot(self):
        # Clear existing contours
        if hasattr(self, "_contours"):
            try:
                for coll in self._contours.collections:  # type: ignore
                    coll.remove()
            except (AttributeError, TypeError):
                try:
                    if hasattr(self._contours, "remove"):
                        self._contours.remove()
                    else:
                        self.ax_ripples.clear()
                        if self.im is not None:
                            self.im = None
                except:
                    pass

        # Clear existing ripple markers and text annotations
        if hasattr(self, "_ripple_markers"):
            for marker in self._ripple_markers:
                try:
                    marker.remove()
                except:
                    pass
        if hasattr(self, "_ripple_texts"):
            for text in self._ripple_texts:
                try:
                    text.remove()
                except:
                    pass

        # Initialize marker and text tracking lists
        self._ripple_markers = []
        self._ripple_texts = []

        if self.im is None:
            if not hasattr(self, "_axes_cleared") or self._axes_cleared:
                self.ax_ripples.clear()
                self._axes_cleared = False

            self.im = self.ax_ripples.imshow(
                self.ripple_data,
                cmap="RdBu",
                origin="upper",
                extent=(0, self.params["resolution"], 0, self.params["resolution"]),
            )

            self.ax_ripples.set_xlabel("X")
            self.ax_ripples.set_ylabel("Y")
            self.ax_ripples.set_title("Height Map - CLICK to Add, DRAG to Move Ripples")
            self.ax_ripples.set_aspect("equal")

            if self.colorbar is None:
                self.colorbar = plt.colorbar(
                    self.im, ax=self.ax_ripples, shrink=0.8, label="Height"
                )
        else:
            self.im.set_array(self.ripple_data)
            self.im.set_clim(vmin=self.ripple_data.min(), vmax=self.ripple_data.max())
            if self.colorbar is not None:
                self.colorbar.update_normal(self.im)

        # Add contour lines
        try:
            x = np.arange(self.params["resolution"])
            y = np.arange(self.params["resolution"])
            X, Y = np.meshgrid(x, y)
            self._contours = self.ax_ripples.contour(
                X,
                Y,
                self.ripple_data,
                levels=10,
                colors="black",
                alpha=0.3,
                linewidths=0.5,
            )
        except Exception:
            pass

        # Mark ripple centers with selection indication
        for i, ripple in enumerate(self.ripple_list):
            center_x, center_y = ripple["center"]

            if i == self.selected_ripple_index:
                # Selected ripple - red with larger size
                marker = self.ax_ripples.plot(
                    center_x,
                    center_y,
                    "ro",
                    markersize=12,
                    markeredgecolor="darkred",
                    markeredgewidth=2,
                )
                self._ripple_markers.extend(marker)

                # Add text with parameters
                text = self.ax_ripples.text(
                    center_x + 5,
                    center_y + 5,
                    f"F:{ripple['frequency']:.3f}\nA:{ripple['amplitude']:.2f}\nD:{ripple['decay']:.3f}",
                    fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8),
                )
                self._ripple_texts.append(text)
            else:
                # Unselected ripples - blue
                marker = self.ax_ripples.plot(
                    center_x,
                    center_y,
                    "bo",
                    markersize=8,
                    markeredgecolor="darkblue",
                    markeredgewidth=1,
                )
                self._ripple_markers.extend(marker)

    def update_info_text(self):
        if self.selected_ripple_index is not None and self.selected_ripple_index < len(
            self.ripple_list
        ):
            ripple = self.ripple_list[self.selected_ripple_index]
            info = f"Selected Ripple {self.selected_ripple_index + 1}: Center({ripple['center'][0]}, {ripple['center'][1]}) | "
            info += f"Freq: {ripple['frequency']:.3f} | Amp: {ripple['amplitude']:.2f} | Decay: {ripple['decay']:.3f}"
        else:
            info = f"Total Ripples: {len(self.ripple_list)} | Click RIGHT plot to add ripples | Drag existing ripples to move"

        info += "\nLEFT: Drag to rotate 3D view | RIGHT: Click=add, Drag=move ripples"
        self.info_text.set_text(info)

    def setup_interaction(self):
        # Add mouse events for drag functionality
        self.cid_press = self.fig.canvas.mpl_connect(
            "button_press_event", self.on_mouse_press
        )
        self.cid_motion = self.fig.canvas.mpl_connect(
            "motion_notify_event", self.on_mouse_motion
        )
        self.cid_release = self.fig.canvas.mpl_connect(
            "button_release_event", self.on_mouse_release
        )
        self.fig.canvas.mpl_connect("key_press_event", self.on_key_press)

    def on_mouse_press(self, event):
        if event.button == 1 and event.inaxes == self.ax_ripples:
            click_x = event.xdata
            click_y = event.ydata

            if click_x is not None and click_y is not None:
                resolution = self.params["resolution"]
                grid_x = max(0, min(resolution - 1, int(click_x)))
                grid_y = max(0, min(resolution - 1, int(click_y)))

                # Check if clicking near existing ripple (within 15 pixels for easier dragging)
                clicked_ripple = None
                for i, ripple in enumerate(self.ripple_list):
                    cx, cy = ripple["center"]
                    if abs(cx - grid_x) < 15 and abs(cy - grid_y) < 15:
                        clicked_ripple = i
                        break

                if clicked_ripple is not None:
                    # Start dragging existing ripple - DON'T regenerate anything

                    self.dragging = True
                    self.drag_ripple_index = clicked_ripple
                    self.selected_ripple_index = clicked_ripple

                    # Calculate offset for smooth dragging
                    cx, cy = self.ripple_list[clicked_ripple]["center"]
                    self.drag_offset_x = cx - grid_x
                    self.drag_offset_y = cy - grid_y

                    # Update sliders to show this ripple's parameters WITHOUT triggering regeneration
                    ripple = self.ripple_list[clicked_ripple]
                    # Set flag to prevent pattern generation during slider updates
                    self._updating_sliders = True

                    self.slider_frequency.set_val(ripple["frequency"])
                    self.slider_amplitude.set_val(ripple["amplitude"])
                    self.slider_decay.set_val(ripple["decay"])

                    # Clear flag after updating sliders
                    self._updating_sliders = False

                    # Update display but don't regenerate pattern
                    self.update_info_text()
                else:
                    # Add new ripple only if not dragging

                    new_ripple = {
                        "center": (grid_x, grid_y),
                        "frequency": self.current_ripple_params["frequency"],
                        "amplitude": self.current_ripple_params["amplitude"],
                        "decay": self.current_ripple_params["decay"],
                    }
                    self.ripple_list.append(new_ripple)
                    self.selected_ripple_index = len(self.ripple_list) - 1

                    # Only regenerate for new ripples, not for drag start
                    self.generate_pattern()
                    self.fig.canvas.draw()

    def on_mouse_motion(self, event):
        if self.dragging and event.inaxes == self.ax_ripples:
            click_x = event.xdata
            click_y = event.ydata

            if click_x is not None and click_y is not None:
                resolution = self.params["resolution"]
                # Apply offset for smooth dragging
                new_x = max(0, min(resolution - 1, int(click_x + self.drag_offset_x)))
                new_y = max(0, min(resolution - 1, int(click_y + self.drag_offset_y)))

                # Update ripple position and show real-time feedback
                if self.drag_ripple_index is not None and self.drag_ripple_index < len(
                    self.ripple_list
                ):
                    self.ripple_list[self.drag_ripple_index]["center"] = (new_x, new_y)

                    # Update only the ripple plot for real-time feedback
                    self.update_ripple_plot()
                    self.fig.canvas.draw()

    def on_mouse_release(self, event):
        if self.dragging:
            self.dragging = False
            self.drag_ripple_index = None
            # Only do full regeneration when drag is complete

            self.generate_pattern()
            self.fig.canvas.draw()

    def clear_ripples(self, event):
        # Clear the ripple data
        self.ripple_list = []
        self.selected_ripple_index = None
        self.dragging = False
        self.drag_ripple_index = None

        # Clear existing ripple markers and text annotations from plot
        if hasattr(self, "_ripple_markers"):
            for marker in self._ripple_markers:
                try:
                    marker.remove()
                except:
                    pass
        if hasattr(self, "_ripple_texts"):
            for text in self._ripple_texts:
                try:
                    text.remove()
                except:
                    pass

        # Clear marker and text tracking lists
        self._ripple_markers = []
        self._ripple_texts = []

        # Force complete regeneration
        self.generate_pattern()
        self.fig.canvas.draw()

    def delete_selected_ripple(self, event):
        if self.selected_ripple_index is not None and self.selected_ripple_index < len(
            self.ripple_list
        ):
            self.ripple_list.pop(self.selected_ripple_index)
            self.selected_ripple_index = None
            self.dragging = False
            self.drag_ripple_index = None

            self.generate_pattern()
            self.fig.canvas.draw()

    def update_frequency(self, val):
        self.current_ripple_params["frequency"] = val
        if self.selected_ripple_index is not None and self.selected_ripple_index < len(
            self.ripple_list
        ):
            self.ripple_list[self.selected_ripple_index]["frequency"] = val
            if not self._updating_sliders:
                self.generate_pattern()
                self.fig.canvas.draw()

    def update_amplitude(self, val):
        self.current_ripple_params["amplitude"] = val
        if self.selected_ripple_index is not None and self.selected_ripple_index < len(
            self.ripple_list
        ):
            self.ripple_list[self.selected_ripple_index]["amplitude"] = val
            if not self._updating_sliders:
                self.generate_pattern()
                self.fig.canvas.draw()

    def update_decay(self, val):
        self.current_ripple_params["decay"] = val
        if self.selected_ripple_index is not None and self.selected_ripple_index < len(
            self.ripple_list
        ):
            self.ripple_list[self.selected_ripple_index]["decay"] = val
            if not self._updating_sliders:
                self.generate_pattern()
                self.fig.canvas.draw()

    def update_spacing(self, val):
        self.params["line_spacing"] = int(val)
        self.update_3d_plot()
        self.fig.canvas.draw()

    def update_distortion(self, val):
        self.params["distortion_scale"] = val
        self.update_3d_plot()
        self.fig.canvas.draw()

    def update_direction(self, label):
        self.params["line_direction"] = label
        self.update_3d_plot()
        self.fig.canvas.draw()

    def reset_view(self, event):
        self.ax_3d.view_init(elev=30, azim=-45)  # type: ignore
        self.fig.canvas.draw()

    def isometric_view(self, event):
        self.ax_3d.view_init(elev=30, azim=-60)  # type: ignore
        self.fig.canvas.draw()

    def export_parameters(self, event):
        params = f"""# Advanced Ripple Line Distortion Parameters
params = {{
    'resolution': {self.params["resolution"]},
    'line_spacing': {self.params["line_spacing"]},
    'line_direction': '{self.params["line_direction"]}',
    'distortion_scale': {self.params["distortion_scale"]:.1f},
    'ripple_list': ["""

        for ripple in self.ripple_list:
            params += f"""
        {{
            'center': {ripple["center"]},
            'frequency': {ripple["frequency"]:.3f},
            'amplitude': {ripple["amplitude"]:.2f},
            'decay': {ripple["decay"]:.3f}
        }},"""

        params += """
    ]
}}

# Current 3D view angle:
elev = {:.1f}
azim = {:.1f}""".format(self.ax_3d.elev, self.ax_3d.azim)  # type: ignore

        print("=" * 60)
        print("EXPORTED ADVANCED RIPPLE LINE PARAMETERS")
        print("=" * 60)
        print(params)
        print("=" * 60)

    def on_key_press(self, event):
        if event.key == "c":
            self.clear_ripples(None)
        elif event.key == "d":
            # Toggle direction
            current = self.params["line_direction"]
            new_direction = "horizontal" if current == "vertical" else "vertical"
            options = ["vertical", "horizontal"]
            self.radio_direction.set_active(options.index(new_direction))
        elif event.key == "r":
            self.reset_view(None)
        elif event.key == "i":
            self.isometric_view(None)
        elif event.key == "delete" or event.key == "backspace":
            self.delete_selected_ripple(None)
        elif event.key == "e":
            self.export_parameters(None)

    def show(self):
        plt.show()


def main():
    viewer = AdvancedRippleLineViewer()
    viewer.show()


if __name__ == "__main__":
    main()
