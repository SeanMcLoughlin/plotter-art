# plotter-graph-with-vortex

A vsketch sketch that draws graph paper and swirls it into one or more vortices,
for pen plotting.

```sh
uv run vsk run main.py      # interactive viewer with parameter sliders
uv run vsk save main.py     # write an SVG to output/
```

## How it works

Each grid line is a polyline pushed through every enabled vortex in turn. A vortex
rotates points around its center by an angle that fades with distance, and
squeezes them toward the center. Segments are subdivided until every warped
segment is shorter than `max_segment`, so tight spirals stay smooth.

## Parameters

Per vortex (`v0_*` … `v3_*`, toggle with `vN_on`):

| Param       | Meaning                                                              |
|-------------|----------------------------------------------------------------------|
| `x`, `y`    | Center, as a fraction (0–1) of the grid width/height                 |
| `turns`     | Full rotations at the center. Negative values spin the other way     |
| `radius`    | Reach in mm; the grid is untouched well beyond it                    |
| `tightness` | 0 gives a soft swirl; higher values pack the twist into the core     |
| `pull`      | Radial squeeze toward the center (0–1). Near 1 gives a dense drain   |
| `hole`      | Radius in mm of the core that's cut out (and optionally filled in)   |

Global: page size/orientation, `margin`, `cell_size`, `overshoot` (how far lines
run past the last crossing), toggles for horizontal/vertical lines, clipping to
the frame, `wobble`/`wobble_scale` for a hand-drawn look, and `fill_holes` +
`pen_width` to fill each core with a single spiral stroke.
