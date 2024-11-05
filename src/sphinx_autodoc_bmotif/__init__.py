import pathlib
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from docutils.utils import new_document
from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import switch_source_input
from sphinx.errors import ExtensionError
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library

logger = logging.getLogger(__name__)
bm = BuildingMOTIF("sqlite://")
brick = Library.load(ontology_graph="https://brickschema.org/schema/1.4/Brick.ttl", infer_templates=True, run_shacl_inference=False)

class BuildingMOTIFLibraryDirective(Directive):

    required_arguments = 1
    
    def run(self):
        output_nodes = []

        self.env = self.state.document.settings.env
        self.record_dependencies = self.state.document.settings.record_dependencies
        print(f"self.env: {self.env}")
        print(f"self.record_dependencies: {self.record_dependencies}")

        # normalize joining the self.env.srcdir, self.env.config.autotemplate_root, and the directive argument
        srcdir = pathlib.Path(self.env.srcdir)
        #root = pathlib.Path(self.env.config.autobmotiflib_root)
        #template_path = root.joinpath(self.arguments[0])
        #template_path = srcdir.joinpath(template_path)

        self._parse_library(self.arguments[0])

        return output_nodes

    def _build_template(self, template):
        pass

    def _parse_library(self, library_directory):
        print(f"library_directory: {library_directory}")
        lib = Library.load(directory=library_directory, infer_templates=False, run_shacl_inference=False)
        for templ in lib.get_templates():
            print(f"templ: {templ}")
            doc = self._build_template(templ)
            print(f"doc: {doc}")
            yield doc


def setup(app):
    app.add_directive("autobmotiflib", BuildingMOTIFLibraryDirective)
    print("BuildingMOTIFLibraryDirective setup")
