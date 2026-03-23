# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sphinx-autodoc-bmotif generates documentation for BuildingMOTIF templates, targeting Jupyter Book v2 / mystmd. It provides two modes:

1. **CLI** (`sphinx-autodoc-bmotif generate`) — pre-build command that generates `.md` + `.svg` files per template (multi-page)
2. **mystmd executable plugin** — registers an `autotemplatedoc` directive for inline single-page use

## Build & Run

Uses `uv` for project management with `hatchling` as the build backend.

```bash
# Generate template docs (multi-page)
uv run sphinx-autodoc-bmotif generate <lib_dir> <output_dir>

# Build docs with mystmd
cd docs && myst build

# Test the plugin spec output
uv run python src/sphinx_autodoc_bmotif/myst_plugin.py
```

There are no tests in this project.

## Architecture

### `src/sphinx_autodoc_bmotif/__init__.py` — Core logic
- `load_library(lib_dir)` — loads Brick ontology + specified library via BuildingMOTIF, computes dependency/backlink maps, renders SVGs. Returns list of template data dicts.
- `generate_md_files(lib_dir, output_dir)` — writes MyST markdown `.md` files + `.svg` files using `load_library()` output
- `build_ast_nodes(lib_dir)` — returns MyST AST JSON nodes for the executable plugin
- Helper functions: `_resolve_dependency_link()` (returns link data dicts), `_format_md_link()` (markdown), `_build_ast_link()` (AST nodes), `_render_svg()` (DOT→SVG via pydot)

### `src/sphinx_autodoc_bmotif/myst_plugin.py` — mystmd executable plugin
- Implements the mystmd stdin/stdout JSON protocol (no args → plugin spec; `--directive name` → read JSON stdin, write AST nodes to stdout)

### `src/sphinx_autodoc_bmotif/__main__.py` — CLI entry point
- `generate` subcommand calls `generate_md_files()`

## Key Dependencies

- **BuildingMOTIF** (from git `develop` branch) — template loading, dependency resolution, inline expansion
- **rdflib** (transitive via BuildingMOTIF) — RDF graph handling and Turtle serialization
- **pydot** — DOT→SVG rendering for graph visualizations
