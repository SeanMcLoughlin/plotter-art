# Kumiko Tiles Plugin System

This plugin system allows you to create custom kumiko tile patterns that can be used in the triangular grid generator. Each tile is a self-contained module that defines how to draw a specific pattern within a triangle.

## Overview

The plugin system automatically discovers and loads all tile modules in this directory. Each tile must inherit from the `BaseTile` class and implement the required methods.

## Available Tiles

The following tiles are included by default:

- **asanoha** - Hemp leaf pattern with radiating lines from center
- **seigaiha** - Wave pattern with overlapping semicircular arcs
- **kikko** - Tortoise shell pattern with hexagonal shapes
- **shippo** - Seven treasures pattern with interlocking circles
- **yabane** - Arrow feather pattern with arrow-like lines and feather details
- **simple_lines** - Basic parallel lines pattern
- **mizuhiki** - Decorative cord pattern with curved lines (example custom tile)

## Using Tiles

In the main sketch, you can specify which tile to use for each layer by setting the `layer_N_tile_type` parameters to any of the available tile names.

## Creating Custom Tiles

### Quick Start

1. Copy the `example_custom.py` file and rename it (e.g., `my_tile.py`)
2. Change the class name (e.g., `MyTile`)
3. Update the `name` property to return a unique name
4. Update the `description` property
5. Implement your drawing logic in the `draw()` method
6. Save the file in this directory

The tile will be automatically loaded when the program starts.

### Tile Structure

Every tile must follow this structure:

```python
from . import BaseTile
from typing import List, Tuple

class MyCustomTile(BaseTile):
    @property
    def name(self) -> str:
        return "my_custom_tile"
    
    @property
    def description(self) -> str:
        return "My custom tile description"
    
    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        # Your drawing code here
        pass
```

### Drawing Methods

The `vsk` parameter provides access to vsketch drawing methods:

- `vsk.line(x1, y1, x2, y2)` - Draw a line
- `vsk.circle(x, y, radius)` - Draw a circle
- `vsk.arc(x, y, radius, start_angle, end_angle)` - Draw an arc
- `vsk.polygon(points)` - Draw a polygon

### Triangle Coordinates

The `triangle_coords` parameter is a list of 3 tuples representing the triangle vertices:
```python
triangle_coords = [(x1, y1), (x2, y2), (x3, y3)]
```

### Common Calculations

Here are some useful calculations for working with triangles:

```python
# Triangle center
center_x = sum(coord[0] for coord in triangle_coords) / 3
center_y = sum(coord[1] for coord in triangle_coords) / 3

# Edge midpoints
midpoints = []
for i in range(3):
    mid_x = (triangle_coords[i][0] + triangle_coords[(i+1)%3][0]) / 2
    mid_y = (triangle_coords[i][1] + triangle_coords[(i+1)%3][1]) / 2
    midpoints.append((mid_x, mid_y))

# Triangle bounds
min_x = min(coord[0] for coord in triangle_coords)
max_x = max(coord[0] for coord in triangle_coords)
min_y = min(coord[1] for coord in triangle_coords)
max_y = max(coord[1] for coord in triangle_coords)

# Edge lengths
edge_lengths = []
for i in range(3):
    p1 = triangle_coords[i]
    p2 = triangle_coords[(i+1) % 3]
    length = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    edge_lengths.append(length)
```

## Best Practices

1. **Keep patterns simple** - Complex patterns may not scale well in small triangles
2. **Use relative sizing** - Base your pattern size on the triangle dimensions
3. **Handle edge cases** - Check for zero-length edges or degenerate triangles
4. **Test with different triangle sizes** - Your pattern should work with various triangle scales
5. **Use descriptive names** - Choose clear, unique names for your tiles
6. **Add comments** - Document your drawing logic for future reference

## Examples

### Simple Geometric Pattern
```python
class CrossTile(BaseTile):
    @property
    def name(self) -> str:
        return "cross"
    
    def draw(self, vsk, triangle_coords):
        center_x = sum(coord[0] for coord in triangle_coords) / 3
        center_y = sum(coord[1] for coord in triangle_coords) / 3
        
        # Draw cross lines
        size = 0.05
        vsk.line(center_x - size, center_y, center_x + size, center_y)
        vsk.line(center_x, center_y - size, center_x, center_y + size)
```

### Pattern with Circles
```python
class DotsTile(BaseTile):
    @property
    def name(self) -> str:
        return "dots"
    
    def draw(self, vsk, triangle_coords):
        # Draw circles at each vertex
        for coord in triangle_coords:
            vsk.circle(coord[0], coord[1], 0.02)
```

## Troubleshooting

- **Tile not appearing**: Check that your file is in the `kumiko_tiles` directory and has a `.py` extension
- **Import errors**: Make sure you import `BaseTile` from the current package using `from . import BaseTile`
- **Pattern too large/small**: Adjust your sizing calculations based on triangle dimensions
- **Pattern not visible**: Ensure you're using the correct vsketch drawing methods

## File Organization

```
kumiko_tiles/
├── __init__.py          # Plugin system core
├── README.md            # This file
├── asanoha.py           # Hemp leaf pattern
├── seigaiha.py          # Wave pattern
├── kikko.py             # Tortoise shell pattern
├── shippo.py            # Seven treasures pattern
├── yabane.py            # Arrow feather pattern
├── simple_lines.py      # Simple lines pattern
├── example_custom.py    # Example custom tile
└── your_custom_tile.py  # Your custom tiles here
```

## API Reference

### BaseTile Class

```python
class BaseTile(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of this tile type"""
        pass
    
    @property
    def description(self) -> str:
        """Return a description of this tile type"""
        return f"{self.name} tile"
    
    @abstractmethod
    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """Draw the tile pattern inside the given triangle"""
        pass
```

### TileRegistry Methods

```python
# Get a tile instance
tile = kumiko_tiles.get_tile("asanoha")

# List available tiles
tiles = kumiko_tiles.get_available_tiles()

# Draw a tile
kumiko_tiles.draw_tile(vsk, triangle_coords, "asanoha")
```
