import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
import numpy as np
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class RippleLineGenerator:
    """Generates water ripple patterns from a list of ripples with individual parameters."""

    def generate_ripples(
        self, width: int, height: int, ripple_list: List[Dict[str, Any]]
    ) -> np.ndarray:
        """Generate water ripple pattern from list of ripples with individual parameters."""
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
    """Interactive viewer for advanced ripple line patterns with 3D visualization."""

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
            "resolution": 100,
            "line_spacing": 1,
            "line_direction": "vertical",
            "distortion_scale": 15.0,
            "manual_mode": True,
        }

        # Current ripple parameters (for new ripples)
        self.current_ripple_params = {
            "frequency": 0.025,
            "amplitude": 0.2,
            "decay": 0.02,
        }

        # List of ripples with individual parameters
        self.ripple_list: List[Dict[str, Any]] = []
        self.selected_ripple_index: Optional[int] = None

        # Drag state
        self.dragging = False
        self.drag_ripple_index: Optional[int] = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.colorbar = None
        self.im = None
        self._axes_cleared = True
        self.ripple_data: Optional[np.ndarray] = None

        # Initialize marker and text tracking lists
        self._ripple_markers: List[Any] = []
        self._ripple_texts: List[Any] = []

        # Flag to prevent pattern generation during slider updates
        self._updating_sliders = False

        # Create UI controls
        self.create_controls()

        # Generate initial pattern
        self.generate_pattern()

        # Set up interactivity
        self.setup_interaction()

    def create_controls(self):
        """Create all UI controls (sliders, buttons, radio buttons)."""
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

        # Buttons
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

        # Save Config button
        ax_export = plt.axes((button_left, 0.15, button_width, button_height))
        self.btn_export = Button(ax_export, "Save Config")
        self.btn_export.on_clicked(self.export_parameters)

        # Export SVG button
        ax_export_svg = plt.axes(
            (button_left + button_spacing, 0.15, button_width, button_height)
        )
        self.btn_export_svg = Button(ax_export_svg, "Export SVG")
        self.btn_export_svg.on_clicked(self.export_svg)

        # Reset view button
        ax_reset_view = plt.axes((button_left, 0.10, button_width, button_height))
        self.btn_reset_view = Button(ax_reset_view, "Reset View")
        self.btn_reset_view.on_clicked(self.reset_view)

        # Isometric view button
        ax_iso = plt.axes(
            (button_left + button_spacing, 0.10, button_width, button_height)
        )
        self.btn_iso = Button(ax_iso, "Isometric")
        self.btn_iso.on_clicked(self.isometric_view)

        # Direction radio buttons
        ax_direction = plt.axes((0.85, 0.02, 0.12, 0.08))
        self.radio_direction = RadioButtons(ax_direction, ("vertical", "horizontal"))
        self.radio_direction.on_clicked(self.update_direction)

    def generate_pattern(self):
        """Generate the ripple pattern and update all plots."""
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

        # Update plots
        self.update_3d_plot()
        self.update_ripple_plot()

    def update_3d_plot(self):
        """Update the 3D line plot with current ripple data."""
        if self.ripple_data is None:
            return

        self.ax_3d.clear()
        self.ax_3d.set_axis_off()
        resolution = self.params["resolution"]

        # Create distorted lines based on direction
        if self.params["line_direction"] == "vertical":
            # Vertical lines (constant x, varying y)
            for i in range(0, resolution, self.params["line_spacing"]):
                x_coords = np.full(resolution, i)
                y_coords = np.arange(resolution)
                z_coords = self.ripple_data[:, i] * self.params["distortion_scale"]

                # Apply y-distortion based on ripple height
                y_distorted = (
                    y_coords + self.ripple_data[:, i] * self.params["distortion_scale"]
                )

                self.ax_3d.plot(x_coords, y_distorted, z_coords, "k-", linewidth=0.8)
        else:
            # Horizontal lines (constant y, varying x)
            for i in range(0, resolution, self.params["line_spacing"]):
                y_coords = np.full(resolution, i)
                x_coords = np.arange(resolution)
                z_coords = self.ripple_data[i, :] * self.params["distortion_scale"]

                # Apply x-distortion based on ripple height
                x_distorted = (
                    x_coords + self.ripple_data[i, :] * self.params["distortion_scale"]
                )

                self.ax_3d.plot(x_distorted, y_coords, z_coords, "k-", linewidth=0.8)

        # Mark ripple centers in 3D
        for i, ripple in enumerate(self.ripple_list):
            center_x, center_y = ripple["center"]

            color = "red" if i == self.selected_ripple_index else "blue"
            marker_size = 100 if i == self.selected_ripple_index else 50
            self.ax_3d.scatter(center_x, center_y, c=color, s=marker_size, alpha=0.8)

        # Set limits and aspect
        self.ax_3d.set_xlim(0, resolution)
        self.ax_3d.set_ylim(0, resolution)
        if len(self.ripple_list) > 0:
            z_min, z_max = self.ripple_data.min(), self.ripple_data.max()
            z_range = max(abs(z_min), abs(z_max), 1)
            self.ax_3d.set_zlim(  # type: ignore
                -z_range * self.params["distortion_scale"],
                z_range * self.params["distortion_scale"],
            )

        self.ax_3d.set_title("3D Lines (Drag to Rotate View)")

        # Add instruction text
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
        """Update the 2D ripple height map plot."""
        if self.ripple_data is None:
            return

        # Clear existing elements
        self._clear_ripple_markers()

        if self.im is None:
            self.im = self.ax_ripples.imshow(
                self.ripple_data,
                extent=(0, self.params["resolution"], 0, self.params["resolution"]),
                origin="lower",
                cmap="RdBu_r",
                interpolation="bilinear",
            )

            if self.colorbar is None:
                self.colorbar = plt.colorbar(self.im, ax=self.ax_ripples, shrink=0.8)
        else:
            self.im.set_data(self.ripple_data)
            self.im.set_clim(vmin=self.ripple_data.min(), vmax=self.ripple_data.max())

        # Draw ripple centers and labels
        for i, ripple in enumerate(self.ripple_list):
            center_x, center_y = ripple["center"]

            color = "red" if i == self.selected_ripple_index else "blue"
            marker_size = 100 if i == self.selected_ripple_index else 50

            marker = self.ax_ripples.scatter(
                center_x,
                center_y,
                c=color,
                s=marker_size,
                alpha=0.8,
                edgecolors="white",
            )
            self._ripple_markers.append(marker)

            text = self.ax_ripples.text(
                center_x + 2,
                center_y + 2,
                f"R{i}",
                fontsize=8,
                color="white",
                weight="bold",
            )
            self._ripple_texts.append(text)

        self.ax_ripples.set_title("Ripple Height Map (Click to Add/Select)")
        self.ax_ripples.set_xlabel("X")
        self.ax_ripples.set_ylabel("Y")

    def _clear_ripple_markers(self):
        """Clear existing ripple markers and text annotations."""
        for marker in self._ripple_markers:
            try:
                marker.remove()
            except (ValueError, AttributeError):
                pass

        for text in self._ripple_texts:
            try:
                text.remove()
            except (ValueError, AttributeError):
                pass

        self._ripple_markers = []
        self._ripple_texts = []

    def setup_interaction(self):
        """Set up mouse and keyboard interaction."""
        self.fig.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_mouse_motion)
        self.fig.canvas.mpl_connect("button_release_event", self.on_mouse_release)

    def on_mouse_press(self, event):
        """Handle mouse press events."""
        if event.inaxes != self.ax_ripples or event.button not in [1, 3]:
            return

        click_x, click_y = event.xdata, event.ydata
        if click_x is None or click_y is None:
            return

        # Find closest ripple
        closest_index, closest_distance = self._find_closest_ripple(click_x, click_y)

        if event.button == 1:  # Left click
            if closest_distance < 10 and closest_index is not None:
                # Select and prepare to drag existing ripple
                self.selected_ripple_index = closest_index
                self.dragging = True
                self.drag_ripple_index = closest_index

                ripple_center = self.ripple_list[closest_index]["center"]
                self.drag_offset_x = click_x - ripple_center[0]
                self.drag_offset_y = click_y - ripple_center[1]

                # Update sliders to match selected ripple
                self._update_sliders_for_ripple(closest_index)
            else:
                # Add new ripple
                new_ripple = {
                    "center": (click_x, click_y),
                    "frequency": self.current_ripple_params["frequency"],
                    "amplitude": self.current_ripple_params["amplitude"],
                    "decay": self.current_ripple_params["decay"],
                }
                self.ripple_list.append(new_ripple)
                self.selected_ripple_index = len(self.ripple_list) - 1

        elif event.button == 3:  # Right click - delete ripple
            if closest_distance < 10 and closest_index is not None:
                self.ripple_list.pop(closest_index)
                if self.selected_ripple_index == closest_index:
                    self.selected_ripple_index = None
                elif (
                    self.selected_ripple_index is not None
                    and self.selected_ripple_index > closest_index
                ):
                    self.selected_ripple_index -= 1

        self.generate_pattern()
        self.fig.canvas.draw()

    def _find_closest_ripple(self, x: float, y: float) -> Tuple[Optional[int], float]:
        """Find the closest ripple to the given coordinates."""
        if not self.ripple_list:
            return None, float("inf")

        distances = []
        for i, ripple in enumerate(self.ripple_list):
            center_x, center_y = ripple["center"]
            distance = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            distances.append(distance)

        closest_index = int(np.argmin(distances))
        return closest_index, distances[closest_index]

    def _update_sliders_for_ripple(self, ripple_index: int):
        """Update sliders to match the parameters of the selected ripple."""
        if ripple_index >= len(self.ripple_list):
            return

        ripple = self.ripple_list[ripple_index]
        self._updating_sliders = True

        self.slider_frequency.set_val(ripple["frequency"])
        self.slider_amplitude.set_val(ripple["amplitude"])
        self.slider_decay.set_val(ripple["decay"])

        self._updating_sliders = False

    def on_mouse_motion(self, event):
        """Handle mouse motion events for dragging ripples."""
        if not self.dragging or self.drag_ripple_index is None:
            return

        if (
            event.inaxes != self.ax_ripples
            or event.xdata is None
            or event.ydata is None
        ):
            return

        # Update ripple position
        new_x = event.xdata - self.drag_offset_x
        new_y = event.ydata - self.drag_offset_y

        # Clamp to bounds
        resolution = self.params["resolution"]
        new_x = max(0, min(resolution - 1, new_x))
        new_y = max(0, min(resolution - 1, new_y))

        self.ripple_list[self.drag_ripple_index]["center"] = (new_x, new_y)

        self.generate_pattern()
        self.fig.canvas.draw()

    def on_mouse_release(self, event):
        """Handle mouse release events."""
        self.dragging = False
        self.drag_ripple_index = None

    def clear_ripples(self, event):
        """Clear all ripples."""
        self.ripple_list.clear()
        self.selected_ripple_index = None
        self.dragging = False
        self.drag_ripple_index = None

        self._clear_ripple_markers()
        self.generate_pattern()
        self.fig.canvas.draw()

    def delete_selected_ripple(self, event):
        """Delete the currently selected ripple."""
        if self.selected_ripple_index is not None and self.selected_ripple_index < len(
            self.ripple_list
        ):
            self.ripple_list.pop(self.selected_ripple_index)
            self.selected_ripple_index = None

            self.generate_pattern()
            self.fig.canvas.draw()

    def update_frequency(self, val):
        """Update frequency parameter."""
        self.current_ripple_params["frequency"] = val
        if not self._updating_sliders and self.selected_ripple_index is not None:
            self.ripple_list[self.selected_ripple_index]["frequency"] = val
            self.generate_pattern()
            self.fig.canvas.draw()

    def update_amplitude(self, val):
        """Update amplitude parameter."""
        self.current_ripple_params["amplitude"] = val
        if not self._updating_sliders and self.selected_ripple_index is not None:
            self.ripple_list[self.selected_ripple_index]["amplitude"] = val
            self.generate_pattern()
            self.fig.canvas.draw()

    def update_decay(self, val):
        """Update decay parameter."""
        self.current_ripple_params["decay"] = val
        if not self._updating_sliders and self.selected_ripple_index is not None:
            self.ripple_list[self.selected_ripple_index]["decay"] = val
            self.generate_pattern()
            self.fig.canvas.draw()

    def update_spacing(self, val):
        """Update line spacing parameter."""
        self.params["line_spacing"] = int(val)
        self.generate_pattern()
        self.fig.canvas.draw()

    def update_distortion(self, val):
        """Update distortion scale parameter."""
        self.params["distortion_scale"] = val
        self.generate_pattern()
        self.fig.canvas.draw()

    def update_direction(self, label):
        """Update line direction parameter."""
        self.params["line_direction"] = label
        self.generate_pattern()
        self.fig.canvas.draw()

    def reset_view(self, event):
        """Reset the 3D view to default."""
        self.ax_3d.view_init(elev=20, azim=-60)  # type: ignore
        self.fig.canvas.draw()

    def isometric_view(self, event):
        """Set isometric view for 3D plot."""
        self.ax_3d.view_init(elev=30, azim=45)  # type: ignore
        self.fig.canvas.draw()

    def export_parameters(self, event):
        """Export current parameters to JSON file."""
        # Create config directory if it doesn't exist
        config_dir = "config"
        os.makedirs(config_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ripple_pattern_{timestamp}.json"
        filepath = os.path.join(config_dir, filename)

        export_data = {
            "params": self.params,
            "current_ripple_params": self.current_ripple_params,
            "ripple_list": self.ripple_list,
            "selected_ripple_index": self.selected_ripple_index,
            "export_timestamp": timestamp,
        }

        try:
            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2)
            print(f"Parameters exported to: {filepath}")
        except IOError as e:
            print(f"Error exporting parameters: {e}")

    def export_svg(self, event):
        """Export the 3D plot to SVG format."""
        # Create output directory
        output_dir = "svg_exports"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        svg_filename = f"ripple_pattern_{timestamp}.svg"
        svg_path = os.path.join(output_dir, svg_filename)

        try:
            # Create a new figure with just the 3D subplot
            fig_export = plt.figure(figsize=(9, 12))
            fig_export.subplots_adjust(left=0, right=1, top=1, bottom=0)
            ax_export = fig_export.add_subplot(111, projection="3d")

            # Copy all the lines from the 3D subplot
            for line in self.ax_3d.lines:
                # Get the 3D line data
                xdata, ydata, zdata = line._verts3d  # type: ignore
                ax_export.plot(
                    xdata,
                    ydata,
                    zdata,
                    color=line.get_color(),
                    linewidth=line.get_linewidth(),
                )

            # Apply the current view settings
            ax_export.view_init(elev=self.ax_3d.elev, azim=self.ax_3d.azim)  # type: ignore
            xlim = self.ax_3d.get_xlim()
            ylim = self.ax_3d.get_ylim()
            zlim = self.ax_3d.get_zlim()  # type: ignore
            ax_export.set_xlim(xlim[0], xlim[1])
            ax_export.set_ylim(ylim[0], ylim[1])
            ax_export.set_zlim(zlim[0], zlim[1])  # type: ignore

            # Clean appearance for export
            ax_export.grid(False)
            ax_export.axis("off")

            # Remove 3D axis panes
            ax_export.xaxis.pane.fill = False  # type: ignore
            ax_export.yaxis.pane.fill = False  # type: ignore
            ax_export.zaxis.pane.fill = False  # type: ignore
            ax_export.xaxis.pane.set_edgecolor("none")  # type: ignore
            ax_export.yaxis.pane.set_edgecolor("none")  # type: ignore
            ax_export.zaxis.pane.set_edgecolor("none")  # type: ignore

            # Save as SVG
            fig_export.savefig(
                svg_path,
                format="svg",
                dpi=72,
                bbox_inches=None,
                facecolor="white",
            )
            print(f"SVG exported to: {svg_path}")

        except (IOError, OSError, RuntimeError) as e:
            print(f"Error exporting SVG: {e}")

    def show(self):
        """Show the interactive plot."""
        plt.show()


def main():
    """Main entry point."""
    viewer = AdvancedRippleLineViewer()
    viewer.show()


if __name__ == "__main__":
    main()
