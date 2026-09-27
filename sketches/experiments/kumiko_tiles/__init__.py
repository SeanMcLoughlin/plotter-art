"""
Kumiko Tiles Plugin System

This module provides a base class for kumiko tiles and a registry system
for automatically discovering and loading tile plugins.
"""

import inspect
import importlib
import pkgutil
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Type


class BaseTile(ABC):
    """Base class for all kumiko tiles"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this tile type"""
        pass

    @property
    def description(self) -> str:
        """Return a description of this tile type"""
        return f"{self.name} tile"

    @abstractmethod
    def draw(self, vsk, triangle_coords: List[Tuple[float, float]]) -> None:
        """
        Draw the tile pattern inside the given triangle

        Args:
            vsk: The vsketch context
            triangle_coords: List of (x, y) coordinates for the triangle vertices
        """
        pass


class TileRegistry:
    """Registry for managing kumiko tiles"""

    def __init__(self):
        self._tiles: Dict[str, Type[BaseTile]] = {}
        self._instances: Dict[str, BaseTile] = {}

    def register(self, tile_class: Type[BaseTile]) -> None:
        """Register a tile class"""
        if not issubclass(tile_class, BaseTile):
            raise ValueError(f"Tile class {tile_class.__name__} must inherit from BaseTile")

        instance = tile_class()
        name = instance.name
        self._tiles[name] = tile_class
        self._instances[name] = instance

    def get_tile(self, name: str) -> BaseTile:
        """Get a tile instance by name"""
        if name not in self._instances:
            raise KeyError(f"Tile '{name}' not found. Available tiles: {list(self._tiles.keys())}")
        return self._instances[name]

    def list_tiles(self) -> List[str]:
        """List all available tile names"""
        return list(self._tiles.keys())

    def get_tile_info(self) -> Dict[str, str]:
        """Get information about all available tiles"""
        return {name: tile.description for name, tile in self._instances.items()}


# Global registry instance
registry = TileRegistry()


def load_tiles():
    """Load all tile plugins from the current package"""
    import kumiko_tiles

    # Get the package path
    package_path = kumiko_tiles.__path__

    # Import all modules in the package
    for importer, modname, ispkg in pkgutil.iter_modules(package_path):
        if not ispkg and modname != '__init__':
            try:
                module = importlib.import_module(f'kumiko_tiles.{modname}')

                # Find all classes that inherit from BaseTile
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BaseTile) and
                        obj is not BaseTile):
                        registry.register(obj)

            except Exception as e:
                print(f"Warning: Could not load tile module {modname}: {e}")


def get_available_tiles() -> List[str]:
    """Get list of available tile names"""
    return registry.list_tiles()


def get_tile(name: str) -> BaseTile:
    """Get a tile by name"""
    return registry.get_tile(name)


def draw_tile(vsk, triangle_coords: List[Tuple[float, float]], tile_name: str) -> None:
    """Draw a tile by name"""
    tile = get_tile(tile_name)
    tile.draw(vsk, triangle_coords)


# Auto-load tiles when module is imported
load_tiles()
