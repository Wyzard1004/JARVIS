"""
Map geometry helpers shared by the live scenario editor.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, Optional, Tuple


WORLD_SIZE = 1000.0
MIN_STRUCTURE_FOOTPRINT = 12.0


def clamp_world_value(value: float | int | None) -> float:
    """Clamp a scalar to the world bounds."""
    return max(0.0, min(WORLD_SIZE, float(value or 0.0)))


def clamp_world_position(point: Iterable[float] | None) -> Tuple[float, float]:
    """Clamp a point into the 1000x1000 world."""
    if point is None:
        return (WORLD_SIZE / 2.0, WORLD_SIZE / 2.0)

    values = list(point)
    if len(values) != 2:
        return (WORLD_SIZE / 2.0, WORLD_SIZE / 2.0)

    return (
        clamp_world_value(values[0]),
        clamp_world_value(values[1]),
    )


def normalize_rect_footprint(footprint: Dict | None) -> Optional[Dict]:
    """Normalize an axis-aligned rectangular footprint inside the world."""
    if not isinstance(footprint, dict):
        return None

    raw_width = float(footprint.get("width") or 0.0)
    raw_height = float(footprint.get("height") or 0.0)
    width = max(MIN_STRUCTURE_FOOTPRINT, min(WORLD_SIZE, raw_width))
    height = max(MIN_STRUCTURE_FOOTPRINT, min(WORLD_SIZE, raw_height))

    x = clamp_world_value(footprint.get("x"))
    y = clamp_world_value(footprint.get("y"))
    x = min(x, WORLD_SIZE - width)
    y = min(y, WORLD_SIZE - height)

    return {
        "kind": "rect",
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(width, 2),
        "height": round(height, 2),
    }


def footprint_center(footprint: Dict | None) -> Optional[Tuple[float, float]]:
    """Return the center of a normalized rectangular footprint."""
    rect = normalize_rect_footprint(footprint)
    if rect is None:
        return None

    return (
        round(rect["x"] + rect["width"] / 2.0, 2),
        round(rect["y"] + rect["height"] / 2.0, 2),
    )


def infer_structure_footprint(entity: Dict | None) -> Optional[Dict]:
    """
    Infer a rectangular footprint for legacy structures that only have a center
    point plus render metadata.
    """
    if not isinstance(entity, dict):
        return None

    position = clamp_world_position(entity.get("position"))
    render = entity.get("render") or {}
    render_size = float(render.get("size") or render.get("radius") or 18.0)
    blocking_size = float(entity.get("blocking_size") or entity.get("size") or 0.8)
    width = max(MIN_STRUCTURE_FOOTPRINT, render_size * 3.6 * max(0.65, blocking_size))
    height = max(
        MIN_STRUCTURE_FOOTPRINT,
        width * (0.58 if render.get("shape") == "rectangle" else 0.86),
    )

    return normalize_rect_footprint(
        {
            "kind": "rect",
            "x": position[0] - width / 2.0,
            "y": position[1] - height / 2.0,
            "width": width,
            "height": height,
        }
    )


def normalize_overlay(overlay: Dict | None) -> Dict:
    """Normalize map-overlay metadata stored in scenario state."""
    if not isinstance(overlay, dict):
        return {
            "asset_url": None,
            "asset_path": None,
            "opacity": 0.72,
            "visible": False,
        }

    asset_path = overlay.get("asset_path") or None
    asset_url = overlay.get("asset_url") or None
    opacity = max(0.0, min(1.0, float(overlay.get("opacity", 0.72))))
    visible = bool(overlay.get("visible", bool(asset_url)))

    return {
        "asset_url": asset_url,
        "asset_path": asset_path,
        "opacity": round(opacity, 3),
        "visible": visible,
    }


def clone_editor_entities(entities: Iterable[Dict] | None) -> list[Dict]:
    """Return a defensive deep copy for editor-managed entities."""
    return [deepcopy(entity) for entity in (entities or []) if isinstance(entity, dict)]
