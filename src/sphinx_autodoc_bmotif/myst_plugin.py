#!/usr/bin/env python3
"""MyST executable plugin for sphinx-autodoc-bmotif.

Usage in myst.yml:
    project:
      plugins:
        - type: executable
          path: myst_plugin.py

Or if installed as a package:
    project:
      plugins:
        - type: executable
          path: sphinx-autodoc-bmotif-plugin
"""
import argparse
import json
import sys

PLUGIN_SPEC = {
    "name": "sphinx-autodoc-bmotif",
    "directives": [
        {
            "name": "autotemplatedoc",
            "doc": "Generate documentation for all templates in a BuildingMOTIF library. "
                   "Renders Turtle serializations, parameters, dependencies, backlinks, "
                   "and graph visualizations.",
            "arg": {
                "type": "string",
                "doc": "Path to the BuildingMOTIF template library directory",
                "required": True,
            },
        },
    ],
}


def declare_result(content):
    json.dump(content, sys.stdout, indent=2)
    sys.stdout.write("\n")
    raise SystemExit(0)


def run_directive(name, data):
    if name != "autotemplatedoc":
        print(f"Unknown directive: {name}", file=sys.stderr)
        raise SystemExit(1)

    lib_dir = data.get("arg", "")
    if not lib_dir:
        print("autotemplatedoc requires a library directory argument", file=sys.stderr)
        raise SystemExit(1)

    from sphinx_autodoc_bmotif import build_ast_nodes

    return build_ast_nodes(lib_dir)


def main():
    parser = argparse.ArgumentParser(description="MyST plugin for BuildingMOTIF template docs")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--role", type=str)
    group.add_argument("--directive", type=str)
    group.add_argument("--transform", type=str)
    args = parser.parse_args()

    if args.directive:
        data = json.load(sys.stdin)
        declare_result(run_directive(args.directive, data))
    elif args.role:
        print("No roles defined", file=sys.stderr)
        raise SystemExit(1)
    elif args.transform:
        print("No transforms defined", file=sys.stderr)
        raise SystemExit(1)
    else:
        declare_result(PLUGIN_SPEC)


if __name__ == "__main__":
    main()
