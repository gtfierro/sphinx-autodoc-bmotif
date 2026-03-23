import os
import logging
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library
import rdflib
from rdflib.tools.rdf2dot import rdf2dot
import pydot
import io
from collections import defaultdict

logger = logging.getLogger(__name__)


def _resolve_dependency_link(template):
    """Return a dict describing a dependency link.

    Returns {"text": ..., "url": ...} for external Brick links,
    {"text": ..., "doc": ...} for local template references,
    or None for empty templates.
    """
    if template == "":
        return None
    if str(template.defining_library.name) == "https://brickschema.org/schema/1.4/Brick":
        ns, _, value = template.body.compute_qname(template.name)
        url = f"https://ontology.brickschema.org/{ns}/{value}.html"
        return {"text": str(template.name), "url": url}
    else:
        return {"text": str(template.name), "doc": str(template.name)}


def _format_md_link(link_info):
    """Format a link dict as a MyST markdown link."""
    if link_info is None:
        return ""
    if "url" in link_info:
        return f"[{link_info['text']}]({link_info['url']})"
    else:
        return f"[{link_info['text']}]({link_info['doc']}.md)"


def _render_svg(g: rdflib.Graph) -> str:
    """Render an RDF graph to SVG string via DOT/pydot."""
    buf = io.StringIO()
    rdf2dot(g, buf)
    dot = pydot.graph_from_dot_data(buf.getvalue())
    return dot[0].create_svg().decode("utf-8")


def _build_ast_link(link_info):
    """Convert a link dict to a MyST AST node."""
    if link_info is None:
        return None
    if "url" in link_info:
        return {
            "type": "link",
            "url": link_info["url"],
            "children": [{"type": "text", "value": link_info["text"]}],
        }
    else:
        return {
            "type": "crossReference",
            "identifier": link_info["doc"],
            "children": [{"type": "text", "value": link_info["text"]}],
        }


def load_library(lib_dir):
    """Load a BuildingMOTIF library and return structured template data.

    Returns a list of dicts, each containing:
        name, turtle, inlined_turtle, parameter_map, dependencies,
        backlinks, svg_simple, svg_expanded
    """
    bm = BuildingMOTIF("sqlite://")
    Library.load(
        ontology_graph="https://brickschema.org/schema/1.4/Brick.ttl",
        infer_templates=True,
        run_shacl_inference=False,
    )
    lib = Library.load(directory=lib_dir, infer_templates=False, run_shacl_inference=False)

    # Build backlinks map and dependency maps
    backlinks_map = defaultdict(set)
    template_dependency_maps = {}

    for template in lib.get_templates():
        dependency_map = defaultdict(dict)
        for dep in template.get_dependencies():
            backlinks_map[dep.template.name].add(template.name)
            for _, template_arg in dep.args.items():
                dependency_map[template_arg] = dep.template
        for param in template.parameters:
            if param not in dependency_map:
                dependency_map[param] = ""
        template_dependency_maps[template.name] = dependency_map

    results = []
    for templ in lib.get_templates():
        name = templ.name
        templ.body.bind("P", rdflib.Namespace("urn:___param___#"))

        inlined = templ.inline_dependencies()
        inlined.body.bind("P", rdflib.Namespace("urn:___param___#"))

        # Serialize Turtle
        turtle = templ.body.serialize(format="turtle")
        inlined_turtle = inlined.body.serialize(format="turtle")

        # Build parameter map: list of (param_name, link_info_or_none)
        param_map = []
        for param, dep_template in template_dependency_maps[name].items():
            link = _resolve_dependency_link(dep_template)
            param_map.append((param, link))

        # Build dependencies: list of link_info dicts
        dep_links = set()
        for dep in templ.get_dependencies():
            link = _resolve_dependency_link(dep.template)
            if link is not None:
                dep_links.add((link["text"], link.get("url", ""), link.get("doc", "")))
        dependencies = []
        for text, url, doc in sorted(dep_links):
            if url:
                dependencies.append({"text": text, "url": url})
            else:
                dependencies.append({"text": text, "doc": doc})

        # Build backlinks: list of local template names
        backlinks = sorted(backlinks_map.get(name, set()))

        # Render SVGs
        svg_simple = _render_svg(templ.body)
        svg_expanded = _render_svg(inlined.body)

        results.append({
            "name": name,
            "turtle": turtle,
            "inlined_turtle": inlined_turtle,
            "parameter_map": param_map,
            "dependencies": dependencies,
            "backlinks": backlinks,
            "svg_simple": svg_simple,
            "svg_expanded": svg_expanded,
        })

    return results


def generate_md_files(lib_dir, output_dir):
    """Generate MyST markdown files for each template in a library.

    Creates one .md file per template plus an index.md, along with .svg
    files for graph visualizations.
    """
    lib_name = os.path.basename(lib_dir)
    lib_output_dir = os.path.join(output_dir, lib_name)
    os.makedirs(lib_output_dir, exist_ok=True)

    templates = load_library(lib_dir)
    template_names = []

    for tmpl in templates:
        name = tmpl["name"]
        template_names.append(name)

        # Write SVG files
        svg_simple_path = f"{name}.svg"
        svg_expanded_path = f"{name}-inlined.svg"
        with open(os.path.join(lib_output_dir, svg_simple_path), "w") as f:
            f.write(tmpl["svg_simple"])
        with open(os.path.join(lib_output_dir, svg_expanded_path), "w") as f:
            f.write(tmpl["svg_expanded"])

        # Build parameter map section
        param_lines = []
        for param, link_info in tmpl["parameter_map"]:
            if link_info is None:
                param_lines.append(f"- {param}")
            else:
                param_lines.append(f"- {param} is a {_format_md_link(link_info)}")
        param_section = "\n".join(param_lines) if param_lines else "No parameters."

        # Build dependencies section
        dep_lines = []
        for link_info in tmpl["dependencies"]:
            dep_lines.append(f"- {_format_md_link(link_info)}")
        dep_section = "\n".join(dep_lines) if dep_lines else "No dependencies."

        # Build backlinks section
        if tmpl["backlinks"]:
            backlink_lines = [f"- [{bl}]({bl}.md)" for bl in tmpl["backlinks"]]
            backlink_section = "\n".join(backlink_lines)
        else:
            backlink_section = "Nothing depends on this template."

        md_content = f"""# {name}

::::{{tab-set}}

:::{{tab-item}} Turtle
```turtle
{tmpl["turtle"]}```
:::

:::{{tab-item}} With Inline Dependencies
```turtle
{tmpl["inlined_turtle"]}```
:::

::::

## Parameters

{param_section}

## Dependencies

{dep_section}

## Dependents

{backlink_section}

## Graph Visualization

::::{{tab-set}}

:::{{tab-item}} Template
![]({svg_simple_path})
:::

:::{{tab-item}} With Inline Dependencies
![]({svg_expanded_path})
:::

::::
"""
        with open(os.path.join(lib_output_dir, f"{name}.md"), "w") as f:
            f.write(md_content)

    # Generate index.md
    toc_entries = "\n".join(f"- [{name}]({name}.md)" for name in template_names)
    index_content = f"""# {lib_name} Templates

{toc_entries}
"""
    with open(os.path.join(lib_output_dir, "index.md"), "w") as f:
        f.write(index_content)

    logger.info(f"Generated {len(template_names)} template docs in {lib_output_dir}")
    return template_names


def build_ast_nodes(lib_dir):
    """Build MyST AST nodes for all templates in a library.

    Returns a list of AST nodes suitable for the mystmd executable plugin protocol.
    """
    templates = load_library(lib_dir)
    nodes = []

    for tmpl in templates:
        name = tmpl["name"]

        # Heading
        nodes.append({
            "type": "heading",
            "depth": 2,
            "children": [{"type": "text", "value": name}],
        })

        # Tabs: Turtle / Inlined
        nodes.append({
            "type": "tabSet",
            "children": [
                {
                    "type": "tabItem",
                    "title": "Turtle",
                    "children": [
                        {"type": "code", "lang": "turtle", "value": tmpl["turtle"]},
                    ],
                },
                {
                    "type": "tabItem",
                    "title": "With Inline Dependencies",
                    "children": [
                        {"type": "code", "lang": "turtle", "value": tmpl["inlined_turtle"]},
                    ],
                },
            ],
        })

        # Parameters heading
        nodes.append({
            "type": "heading",
            "depth": 3,
            "children": [{"type": "text", "value": "Parameters"}],
        })

        param_items = []
        for param, link_info in tmpl["parameter_map"]:
            if link_info is None:
                param_items.append({
                    "type": "listItem",
                    "children": [{"type": "paragraph", "children": [
                        {"type": "text", "value": param},
                    ]}],
                })
            else:
                ast_link = _build_ast_link(link_info)
                param_items.append({
                    "type": "listItem",
                    "children": [{"type": "paragraph", "children": [
                        {"type": "text", "value": f"{param} is a "},
                        ast_link,
                    ]}],
                })
        if param_items:
            nodes.append({"type": "list", "ordered": False, "children": param_items})
        else:
            nodes.append({"type": "paragraph", "children": [
                {"type": "text", "value": "No parameters."},
            ]})

        # Dependencies heading
        nodes.append({
            "type": "heading",
            "depth": 3,
            "children": [{"type": "text", "value": "Dependencies"}],
        })

        dep_items = []
        for link_info in tmpl["dependencies"]:
            ast_link = _build_ast_link(link_info)
            dep_items.append({
                "type": "listItem",
                "children": [{"type": "paragraph", "children": [ast_link]}],
            })
        if dep_items:
            nodes.append({"type": "list", "ordered": False, "children": dep_items})
        else:
            nodes.append({"type": "paragraph", "children": [
                {"type": "text", "value": "No dependencies."},
            ]})

        # Dependents heading
        nodes.append({
            "type": "heading",
            "depth": 3,
            "children": [{"type": "text", "value": "Dependents"}],
        })

        if tmpl["backlinks"]:
            bl_items = []
            for bl in tmpl["backlinks"]:
                bl_items.append({
                    "type": "listItem",
                    "children": [{"type": "paragraph", "children": [
                        _build_ast_link({"text": bl, "doc": bl}),
                    ]}],
                })
            nodes.append({"type": "list", "ordered": False, "children": bl_items})
        else:
            nodes.append({"type": "paragraph", "children": [
                {"type": "text", "value": "Nothing depends on this template."},
            ]})

        # Graph Visualization heading
        nodes.append({
            "type": "heading",
            "depth": 3,
            "children": [{"type": "text", "value": "Graph Visualization"}],
        })

        nodes.append({
            "type": "tabSet",
            "children": [
                {
                    "type": "tabItem",
                    "title": "Template",
                    "children": [
                        {"type": "html", "value": tmpl["svg_simple"]},
                    ],
                },
                {
                    "type": "tabItem",
                    "title": "With Inline Dependencies",
                    "children": [
                        {"type": "html", "value": tmpl["svg_expanded"]},
                    ],
                },
            ],
        })

    return nodes
