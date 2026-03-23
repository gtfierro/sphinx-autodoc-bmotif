"""CLI entry point for sphinx-autodoc-bmotif.

Usage:
    python -m sphinx_autodoc_bmotif generate <lib_dir> <output_dir>
    sphinx-autodoc-bmotif generate <lib_dir> <output_dir>
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="sphinx-autodoc-bmotif",
        description="Generate MyST markdown documentation for BuildingMOTIF templates",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen = subparsers.add_parser(
        "generate",
        help="Generate .md and .svg files for each template in a library",
    )
    gen.add_argument("lib_dir", help="Path to the BuildingMOTIF template library directory")
    gen.add_argument("output_dir", help="Output directory for generated files")

    args = parser.parse_args()

    if args.command == "generate":
        from sphinx_autodoc_bmotif import generate_md_files

        names = generate_md_files(args.lib_dir, args.output_dir)
        print(f"Generated {len(names)} template docs in {args.output_dir}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
