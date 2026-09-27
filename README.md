# plotter-art

Pen plotter sketches in a uv workspace.

## Run a sketch

```sh
cd sketches/<name>
uv run vsk run main.py      # interactive viewer
uv run vsk save main.py     # SVG into output/
```

## Add a sketch

```sh
uv init --app sketches/<name>
cd sketches/<name> && uv add vsketch numpy "pyside6<6.10"
```
