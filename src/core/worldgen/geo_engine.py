from __future__ import annotations

"""Geographical algorithms for world generation

Provides core algorithms for:
- Fractal noise generation for heightmaps
- Water mask derivation from heightmaps
- Connected components labeling for landmasses/water bodies
- Geometric utilities for mask processing
"""

import random
from typing import Any, List, Tuple

import numpy as np
import numpy.typing as npt


def generate_fractal_noise(rng: random.Random, size: int, octaves: int = 4) -> npt.NDArray[np.float32]:
    """Generate fractal noise using simple additive approach.
    
    Args:
        rng: Random number generator for reproducible results
        size: Grid size (size x size output)
        octaves: Number of noise octaves to combine
        
    Returns:
        Normalized heightmap as float32 array in range [0, 1]
    """
    # Very simple additive noise using RNG; replace with Perlin/Simplex later
    base = np.zeros((size, size), dtype=np.float32)
    for o in range(octaves):
        scale = 2 ** o
        weight = 1.0 / (scale)
        grid = np.fromiter((rng.random() for _ in range((size // scale) ** 2)), dtype=np.float32)
        grid = grid.reshape((size // scale, size // scale))
        grid = np.kron(grid, np.ones((scale, scale), dtype=np.float32))
        grid = grid[:size, :size]
        base += weight * grid
    base -= base.min()
    base /= (base.max() + 1e-8)
    return base


def derive_water_mask(height: npt.NDArray[np.float32], water_ratio: float) -> Tuple[float, npt.NDArray[np.uint8]]:
    """Determine sea level and create water mask from heightmap.
    
    Args:
        height: Heightmap array
        water_ratio: Fraction of world that should be water (0.0 to 1.0)
        
    Returns:
        Tuple of (sea_level, water_mask) where water_mask is binary uint8 array
    """
    sea_level = float(np.quantile(height, water_ratio))
    is_water = (height < sea_level).astype(np.uint8)
    return sea_level, is_water


def label_connected_components(mask: npt.NDArray[Any]) -> List[npt.NDArray[np.uint8]]:
    """Find connected components in binary mask using 4-connectivity.
    
    Args:
        mask: Binary mask (0/1 values)
        
    Returns:
        List of binary masks, each representing one connected component
    """
    # naive connected components (4-neighborhood)
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    comps: List[List[Tuple[int, int]]] = []
    
    for i in range(h):
        for j in range(w):
            if mask[i, j] and not visited[i, j]:
                stack = [(i, j)]
                current: List[Tuple[int, int]] = []
                visited[i, j] = True
                while stack:
                    y, x = stack.pop()
                    current.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
                comps.append(current)
    
    # convert to boolean masks
    return [
        _create_component_mask(comp, h, w)
        for comp in comps
    ]


def _create_component_mask(comp: List[Tuple[int, int]], h: int, w: int) -> npt.NDArray[np.uint8]:
    """Create binary mask from list of coordinates."""
    m = np.zeros((h, w), dtype=np.uint8)
    for y, x in comp:
        m[y, x] = 1
    return m


def center_of_mask(mask: npt.NDArray[Any]) -> Tuple[float, float]:
    """Calculate the centroid of a binary mask.
    
    Args:
        mask: Binary mask
        
    Returns:
        Tuple of (x, y) coordinates normalized to [0, 1] range
    """
    ys, xs = np.where(mask > 0)
    if len(ys) == 0:
        return 0.5, 0.5
    return float(xs.mean()) / mask.shape[1], float(ys.mean()) / mask.shape[0]


def find_coastline_pixels(land_mask: npt.NDArray[Any], water_mask: npt.NDArray[Any]) -> npt.NDArray[np.uint8]:
    """Find coastline pixels (land cells adjacent to water).
    
    Args:
        land_mask: Binary mask of land areas
        water_mask: Binary mask of water areas
        
    Returns:
        Binary mask of coastline pixels
    """
    hgt, wdt = land_mask.shape
    coast_mask = np.zeros_like(land_mask, dtype=np.uint8)
    
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny = np.clip(np.arange(hgt)[:, None] + dy, 0, hgt - 1)
        nx = np.clip(np.arange(wdt)[None, :] + dx, 0, wdt - 1)
        coast_mask |= (land_mask & (water_mask[ny, nx] == 1)).astype(np.uint8)
    
    return coast_mask
