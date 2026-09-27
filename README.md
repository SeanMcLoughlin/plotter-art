# plotter-art

Pen plotter sketches, mostly [vsketch](https://github.com/abey79/vsketch), in one
[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/).

| Sketch | What it is |
|---|---|
| [`chromatic-aberration`](sketches/chromatic-aberration) | Grid of cubes split into CMY layers |
| [`graph-with-vortex`](sketches/graph-with-vortex) | Graph paper swirled into vortices |
| [`levi-to-scribble`](sketches/levi-to-scribble) | Image to scribble lines (OpenCV) |
| [`lindenmayer-system-botanical-test`](sketches/lindenmayer-system-botanical-test) | L-system plants |
| [`ripples`](sketches/ripples) | Ripple patterns |
| [`test`](sketches/test) | Scratch experiments (kumiko, perlin noise, …) |
| [`tiling`](sketches/tiling) | Tilings and bezier bookmarks |

## Usage

One shared `.venv` and `uv.lock` at the root. Each sketch keeps its own
`pyproject.toml` listing its own dependencies.

```sh
cd sketches/<name>
uv run vsk run main.py      # interactive viewer
uv run vsk save main.py     # SVG into sketches/<name>/output/
```

Run from inside the sketch folder: `vsk` resolves `config/` and `output/`
next to the sketch, and some sketches write to paths relative to the working
directory.

To install everything at once: `uv sync --all-packages`.

## Adding a sketch

```sh
uv init --app sketches/<name>   # or copy an existing sketch
cd sketches/<name> && uv add vsketch numpy "pyside6<6.10"
```

Anything under `sketches/*` is picked up as a workspace member automatically.

## History

Each sketch used to be its own `plotter-<name>` repo. Their histories were
rewritten into `sketches/<name>/` and merged, so `git log sketches/<name>` shows
each sketch's full history.
