# lindenmayer-system-botanical-test

Renders a branching plant from an L-system (Lindenmayer system) with matplotlib.

```sh
uv run python main.py
```

## The L-system

| | |
|---|---|
| Axiom | `-X` |
| Rules | `F → FF`, `X → F+[[X]-X]-F[-FX]+X` |
| Iterations | 6 |
| Angle | 24° |
| Step | 1 |

The rules are applied to the axiom for each iteration, then the resulting
string is drawn turtle-style:

| Symbol | Meaning |
|---|---|
| `F` | Move forward, drawing a line |
| `+` / `-` | Turn left / right by the angle |
| `[` / `]` | Push / pop position and heading (starts and ends a branch) |
| `X` | Placeholder that drives growth; draws nothing |

`turtle-impl.py` draws the same system with Python's `turtle` module.
