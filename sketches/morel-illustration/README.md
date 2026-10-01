# plotter-morel-illustration

Turns a botanical illustration into a pen-and-ink drawing for a plotter, in
four Stabilo Point 88 (0.4) pens. Lines follow the illustration's brush
strokes, and each pen's line density follows how much of that pen's ink
reproduces the illustration's colour. It's the image-driven successor to the
procedural `sketches/morel`.

```sh
uv run vsk run main.py      # tune tone, hatching and pens
uv run vsk save main.py     # write an SVG to output/
```

Put the source image in `images/` (git-ignored, since illustrations are
usually someone else's artwork) and set `image` to its path. It works best
with a single subject on plain white or cream paper, at least ~1000 px tall.

## How it works

1. **Colour separation.** For each colour in the image, solve how much area
   each pen must cover so the pens and paper mix (by area, as hatching does)
   to that colour. First the tones are compressed so the subject's lightest
   parts become paper (`white_pct`, `tone_gamma`). Pens can't reach the
   illustration's darks without near-solid ink. Then ink is boosted again
   where a lot is needed, so pits stay dense (`density`). The pen colour
   params feed this, so set them from swatches of the real pens on your
   paper.
2. **Stroke direction.** The image's structure tensor gives the direction of
   its brush strokes (`stroke_scale`). Where that's unclear, such as flat
   areas or pit centres, it blends toward a coarser direction that follows
   the big forms (`form_scale`).
3. **Flowing lines.** Each pen gets evenly spaced streamlines along that
   direction, spaced so the pen covers its share of the area, between
   `min_spacing` and `max_spacing`. Where a pen needs more coverage than
   `cross_at`, straight lines cross the flowing ones (`cross_angle`, turning
   30° per pen).
4. **Outline**: the silhouette, in `outline_pen`.

Each stage is cached. Pen toggles redraw instantly, and hatching changes
rerun only the line layout (about 7 s at the default `render_res`; raise it
for quicker previews). Changing the image, analysis or tone settings reruns
everything after that stage.

## Main knobs

| Want | Change |
|------|--------|
| Darker / denser pits | `density` up, or `min_spacing` down |
| Lighter overall | `white_pct` down, or `tone_gamma` up |
| More cross-hatching | `cross_at` down |
| Longer, calmer lines | `stroke_scale` up, `min_length` up |
| Check one pen | the `draw_*` toggles |

## Layers

| Layer | Pen |
|-------|-----|
| 1     | yellow (Stabilo 88/54) |
| 2     | light brown (88/89) |
| 3     | dark brown (88/45) |
| 4     | black (88/46) |

Plot light to dark without moving the paper. To split into one SVG per pen:

```sh
uv run vpype read output/main.svg forlayer write "output/main_layer%_lid%.svg" end
```
