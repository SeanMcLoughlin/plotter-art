# plotter-chromatic-aberration

A vsketch sketch that draws a grid of wireframe cubes with a CMY chromatic
aberration effect, for pen plotting. Inspired by
[Adam Fuhrer's pen plot](https://adamfuhrer.com/t/pen-plot).

```sh
uv run vsk run main.py      # interactive viewer with parameter sliders
uv run vsk save main.py     # write an SVG to output/
```

## How it works

Every cube is a randomly rotated 3D cube projected to 2D, with back-facing
edges removed. It is drawn three times, once per layer:

| Layer | Pen     | Offset          |
|-------|---------|-----------------|
| 1     | yellow  | `-(dx, dy)`     |
| 2     | magenta | none (anchor)   |
| 3     | cyan    | `+(dx, dy)`     |

`dx` grows from 0 in the first column to `shift_x` in the last, and `dy` from 0
in the first row to `shift_y` in the last. The top-left cube is a clean
overprint and the bottom-right one is fully split. Plot the layers one pen at a
time. Where all three overlap you get a near-black line.

## Parameters

| Param                      | Meaning                                                        |
|----------------------------|----------------------------------------------------------------|
| `cols`, `rows`             | Grid size                                                      |
| `cube_size`                | Cube size relative to its grid cell                            |
| `yaw_*`, `pitch_*`         | Random rotation range in degrees (pitch > 0 shows the top face) |
| `roll_jitter`              | Random in-plane tilt in degrees                                |
| `perspective`              | 0 is orthographic; higher values give stronger perspective     |
| `shift_x`, `shift_y`       | Max split in mm between neighbouring layers                    |
| `shift_curve`              | Exponent on the ramp: >1 keeps early columns/rows clean longer |
| `rotate_split`, `scale_split` | Extra per-layer rotation/scale split, also ramped           |
| `show_hidden`              | Draw the back edges too                                        |
| `color_1..3`, `pen_width`  | Pen preview colors and width                                   |

## Exporting per-pen SVGs

`vsk save` writes one SVG with each pen as an Inkscape layer. To split it into
one file per pen (every file keeps the full page size, so they stay aligned):

```sh
uv run vpype read output/main_s1.svg forlayer write "output/main_s1_layer%_lid%.svg" end
```

This gives `…_layer1.svg` (yellow), `…_layer2.svg` (magenta) and `…_layer3.svg`
(cyan). Plot them in that order, light to dark, without moving the paper.
