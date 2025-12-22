"""Rendering subpackage.

Provides sprite assembly, recoloring and layering logic for turning immutable
``State`` snapshots into visual representations. The renderer focuses on:

* Deterministic layering based on component appearance priorities.
* Optional palette / hue adjustments for entity grouping (team colors, etc.).
* Lightweight Pillow + NumPy based compositing suitable for small tile grids.

See `grid_universe.renderer.texture` for the core texture map and
composition routines.
"""
