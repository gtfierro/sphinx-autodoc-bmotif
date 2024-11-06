import os
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library
import rdflib
from rdflib.tools.rdf2dot import rdf2dot
import pydot
import io
from collections import defaultdict

logger = logging.getLogger(__name__)

def build_dependencies_string(template):
    dependencies = ""
    for dep in template.get_dependencies():
        if str(dep.template.defining_library.name) == "https://brickschema.org/schema/1.4/Brick":
            ns, _, value = dep.template.body.compute_qname(dep.template.name)
            link = f"https://ontology.brickschema.org/{ns}/{value}.html"
            dependencies += f"- `{dep.template.name} <{link}>`_\n"
        else:
            dependencies += f"- :doc:`{dep.template.name}`\n"
    return dependencies

def build_graphviz(g: rdflib.Graph, indent=1):
    buf = io.StringIO()
    rdf2dot(g, buf)
    dot = pydot.graph_from_dot_data(buf.getvalue())
    return "\n".join(f"{' '*4*indent}{line}" for line in dot[0].to_string().split("\n"))

class AutoTemplateDoc(SphinxDirective):
    has_content = True
    required_arguments = 2  # Directory for templates, and output directory for .rst files

    def run(self):
        bm = BuildingMOTIF("sqlite://")
        # Load Brick library
        Library.load(ontology_graph="https://brickschema.org/schema/1.4/Brick.ttl", infer_templates=True, run_shacl_inference=False)

        # Load specified library
        lib_dir = self.arguments[0]
        output_dir = self.arguments[1]

        # Create library-specific directory
        lib_name = os.path.basename(lib_dir)
        lib_output_dir = os.path.join(output_dir, lib_name)
        os.makedirs(lib_output_dir, exist_ok=True)

        lib = Library.load(directory=lib_dir, infer_templates=False, run_shacl_inference=False)
        template_names = []

        # Create a map to track backlinks (i.e., which templates depend on each template)
        backlinks_map = defaultdict(list)

        # First, populate the backlinks map by going through each template's dependencies
        for template in lib.get_templates():
            for dep in template.get_dependencies():
                # Record that the current template depends on this dependency template
                backlinks_map[dep.template.name].append(template.name)

        # Template for .rst files
        rst_template = """
{name}
{padding}

.. code-block:: turtle

{turtle}

Parameters
----------

{parameters}

Dependencies
------------

{dependencies}

Backlinks
---------

{backlinks}

Graphviz
--------

.. graphviz::

    {graphviz_simple}

.. collapse:: Template With Inline Dependencies

    .. graphviz::

        {graphviz_expanded}
"""

        # Generate .rst files for each template
        for templ in lib.get_templates():
            name = templ.name
            template_names.append(name)
            parameters = "\n".join(f"- {param}" for param in templ.parameters)
            dependencies = build_dependencies_string(templ)
            padding = "#" * len(name)

            # Generate backlinks section
            backlinks = "\n".join(f"- :doc:`{dep_name}`" for dep_name in backlinks_map[name])
            if not backlinks:
                backlinks = "No templates depend on this template."

            # Serialize Turtle representation
            serialized_body = templ.body.serialize(format="turtle")
            serialized_body = "\n".join(f"    {line}" for line in serialized_body.split("\n"))

            # Graphviz representations
            graphviz_simple = build_graphviz(templ.body)
            graphviz_expanded = build_graphviz(templ.inline_dependencies().body, indent=2)

            # Create .rst content for each template
            rst_content = rst_template.format(
                name=name, padding=padding, turtle=serialized_body,
                parameters=parameters, dependencies=dependencies,
                backlinks=backlinks,  # Add backlinks here
                graphviz_simple=graphviz_simple, graphviz_expanded=graphviz_expanded
            )

            # Write to a .rst file in the library-specific output directory
            with open(os.path.join(lib_output_dir, f"{name}.rst"), "w") as f:
                f.write(rst_content)

        # Generate an index.rst file in the library's subdirectory with a toctree for all template files
        index_content = f"""
{lib_name} Templates
====================

.. toctree::
   :maxdepth: 1
   :caption: Template Documentation

"""
        index_content += "\n".join(f"   {name}" for name in template_names)

        # Write the library's index.rst file in the library-specific output directory
        with open(os.path.join(lib_output_dir, "index.rst"), "w") as f:
            f.write(index_content)

        logger.info(f"Generated {len(template_names)} template docs in {lib_output_dir}")

        # Return an empty list as this directive does not produce in-memory nodes
        return []

def setup(app):
    app.add_directive("autotemplatedoc", AutoTemplateDoc)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True
    }
