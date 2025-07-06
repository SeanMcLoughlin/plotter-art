import vsketch
import numpy as np

class NoiseStipplingSketch(vsketch.SketchClass):
    """Simple noise-based stippling"""

    # Parameters
    noise_scale = vsketch.Param(0.01, min_value=0.001, max_value=0.05, step=0.001)
    density_multiplier = vsketch.Param(0.02, min_value=0.005, max_value=0.1, step=0.001)
    threshold = vsketch.Param(0.3, min_value=0.0, max_value=1.0, step=0.05)

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("400px", "600px")
        vsk.stroke(1)
        vsk.strokeWeight(1)
        vsk.noFill()

        vsk.noiseSeed(42)
        vsk.randomSeed(42)

        # Calculate number of sample points based on canvas area
        area = vsk.width * vsk.height
        num_samples = int(area * self.density_multiplier)

        # Sample points across the canvas
        for _ in range(num_samples):
            x = vsk.random(0, vsk.width)
            y = vsk.random(0, vsk.height)

            # Get noise value at this point
            noise_value = vsk.noise(x * self.noise_scale, y * self.noise_scale)

            # Place point if noise is above threshold
            if noise_value > self.threshold:
                vsk.point(x, y)

if __name__ == "__main__":
    NoiseStipplingSketch().display()
