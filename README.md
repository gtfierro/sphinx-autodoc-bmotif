# sphinx-autodoc-bmotif

Generate documentation for [BuildingMOTIF](https://github.com/NREL/buildingmotif) templates, compatible with [Jupyter Book v2](https://jupyterbook.org/) / [mystmd](https://mystmd.org/).

## Installation

```bash
uv add sphinx-autodoc-bmotif
```

## Usage

### Option 1: CLI (multi-page, pre-build)

Generate `.md` and `.svg` files for each template, then include them in your `myst.yml` table of contents:

```bash
sphinx-autodoc-bmotif generate <template-library-dir> <output-dir>
# or
python -m sphinx_autodoc_bmotif generate <template-library-dir> <output-dir>
```

Then build with `myst build` or `jb build .`.

### Option 2: MyST executable plugin (single-page, inline)

Add the plugin to your `myst.yml`:

```yaml
project:
  plugins:
    - type: executable
      path: path/to/myst_plugin.py
```

Or if installed as a package:

```yaml
project:
  plugins:
    - type: executable
      path: sphinx-autodoc-bmotif-plugin
```

Then use the directive in your `.md` files:

````markdown
```{autotemplatedoc} path/to/template-library
```
````

### Required Sphinx extensions (for the inline plugin)

None — this plugin uses the mystmd plugin protocol directly. Tabs, code blocks, and links are rendered natively by mystmd.

## Build docs

```bash
# Pre-generate template docs
uv run sphinx-autodoc-bmotif generate templates docs/libraries

# Build with mystmd
cd docs && myst build
```
