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

def build_dependency_link(template):
    if template == "":
        return ""
    if str(template.defining_library.name) == "https://brickschema.org/schema/1.4/Brick":
        ns, _, value = template.body.compute_qname(template.name)
        link = f"https://ontology.brickschema.org/{ns}/{value}.html"
        return f"`{template.name} <{link}>`_"
    else:
        return f":doc:`{template.name}`"

def build_dependencies_string(template):
    dependencies = ""
    for dep in template.get_dependencies():
        link = build_dependency_link(dep.template)
        dependencies += f"- {link}\n"
        #if str(dep.template.defining_library.name) == "https://brickschema.org/schema/1.4/Brick":
        #    ns, _, value = dep.template.body.compute_qname(dep.template.name)
        #    link = f"https://ontology.brickschema.org/{ns}/{value}.html"
        #    dependencies += f"- `{dep.template.name} <{link}>`_\n"
        #else:
        #    dependencies += f"- :doc:`{dep.template.name}`\n"
    return dependencies

def build_graphviz(g: rdflib.Graph, indent=1):
    buf = io.StringIO()
    rdf2dot(g, buf)
    dot = pydot.graph_from_dot_data(buf.getvalue())
    return "\n".join(f"{' '*6*indent}{line}" for line in dot[0].to_string().split("\n"))

def build_dependencies_parameter_string(dependency_map):
    # dependency_map maps our parameter names to the template they depend on
    # build up a list of the parameter names and the template they depend on, with the template name as a link
    dependencies = ""
    for param, template in dependency_map.items():
        # if template is empty string, just add the parameter name
        link = build_dependency_link(template)
        if template == "":
            dependencies += f"- {param}\n"
        else:
            dependencies += f"- {param} is a {link}\n"
    return dependencies

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

        template_dependency_maps = {}

        # First, populate the backlinks map by going through each template's dependencies
        for template in lib.get_templates():
            # keep track of which dependencies map to which parameters
            dependency_map = defaultdict(dict)
            for dep in template.get_dependencies():
                # Record that the current template depends on this dependency template
                backlinks_map[dep.template.name].append(template.name)
                # loop through the dependency's arguments and map them to the current template's parameters
                for _, template_arg in dep.args.items():
                    dependency_map[template_arg] = dep.template
            # add all extra parameters to dependency_map; if they don't already appear in the map, then they have an empty string dependency
            for param in template.parameters:
                if param not in dependency_map:
                    dependency_map[param] = ""
            template_dependency_maps[template.name] = dependency_map


        # Template for .rst files
        rst_template = """
{name}
{padding}

.. tabs::

    .. tab:: Turtle

        .. code:: turtle

{turtle}

    .. tab:: With Inline Dependencies

        .. code:: turtle

{inlined_turtle}

Parameters
----------

{parameter_map}

Dependencies
------------

{dependencies}

Dependents
----------

{backlinks}

Graph Visualization
--------------------

.. tabs::

    .. tab:: Template

        .. graphviz::

    {graphviz_simple}

    .. tab:: With Inline Dependencies

        .. graphviz::

    {graphviz_expanded}
"""

        # Generate .rst files for each template
        for templ in lib.get_templates():
            name = templ.name
            templ.body.bind("P", rdflib.Namespace("urn:___param___#"))
            template_names.append(name)
            parameters = "\n".join(f"- {param}" for param in templ.parameters)
            dependencies = build_dependencies_string(templ)
            padding = "#" * len(name)

            # Generate backlinks section
            backlinks = "\n".join(f"- :doc:`{dep_name}`" for dep_name in backlinks_map[name])
            if not backlinks:
                backlinks = "Nothing depends on this template."

            inlined = templ.inline_dependencies()
            inlined.body.bind("P", rdflib.Namespace("urn:___param___#"))

            # Serialize Turtle representation
            serialized_body = templ.body.serialize(format="turtle")
            serialized_body = "\n".join(f"           {line}" for line in serialized_body.split("\n"))

            serialized_inlined = inlined.body.serialize(format="turtle")
            serialized_inlined = "\n".join(f"            {line}".rstrip() for line in serialized_inlined.split("\n"))

            # Graphviz representations
            graphviz_simple = build_graphviz(templ.body, indent=2)
            graphviz_expanded = build_graphviz(inlined.body, indent=2)

            parameter_map = build_dependencies_parameter_string(template_dependency_maps[name])

            # Create .rst content for each template
            rst_content = rst_template.format(
                name=name, padding=padding, turtle=serialized_body,
                inlined_turtle=serialized_inlined,
                parameters=parameters, dependencies=dependencies,
                backlinks=backlinks,  # Add backlinks here
                parameter_map=parameter_map,
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
