# plotter-sphere-lattice

A sphere made of solid tubes (several families of parallel rings), shaded for
pen plotting. The sketch exists to compare two ways of getting tone from a
plotter:

- **hatch depth**: one black pen. Darker tones add more hatch passes.
- **multi pen**: light grey, dark grey and black markers. Darker tones
  overprint with darker pens.

```sh
uv run vsk run main.py      # interactive viewer with parameter sliders
uv run vsk save main.py     # write an SVG to output/
```

Render every shading combination side by side:

```sh
uv run vsk save main.py -p pen_mode "hatch depth,multi pen" \
    -p hatch_style contour,screen -p layering cross,parallel
```

## How it works

Each tube is a real 3D torus-like sweep. All tubes are rasterized into a
z-buffer (`raster_res` mm per pixel). Silhouettes and hatch lines are then
generated analytically on the tube surfaces and kept only where the buffer
says they are visible. Tone is Lambert shading plus a specular highlight.
Struts on the far side of the sphere are faded by `back_fade`.

Tone is split into three levels (`level_1..3` are darkness thresholds, 0 to 1):

| Level | `hatch depth` pen | `multi pen` pen | `cross` pass            | `parallel` pass       |
|-------|-------------------|-----------------|-------------------------|-----------------------|
| 1     | black             | light grey      | along the tube / 1st angle | lines at 0        |
| 2     | black             | dark grey       | helix / +90°            | lines at 1/3 spacing  |
| 3     | black             | black           | opposite helix / +45°   | lines at 2/3 spacing  |

`hatch_style`: `contour` hatches follow the tube surface, which reads more
sculptural. `screen` uses straight page-space hatching, which is more
graphic and plots faster.

## Layers

| Layer | Pen        |
|-------|------------|
| 1     | light grey |
| 2     | dark grey  |
| 3     | black      |

Plot them light to dark without moving the paper. To split into one SVG per pen:

```sh
uv run vpype read output/main.svg forlayer write "output/main_layer%_lid%.svg" end
```

## Tuning tips

- The hatch lines should be spaced at least about 2× the pen width, or the
  marker ink bleeds into solid black. Raise `hatch_spacing` for fat markers.
- `rim_cutoff` stops contour hatching from piling up at the tube edges.
- `back_to_light` (multi pen) draws the far side in light grey only, which
  gives the see-through depth of the reference image.
- Lower `raster_res` for cleaner occlusion at junctions (slower).
