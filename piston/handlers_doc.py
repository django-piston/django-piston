from docutils import nodes
from sphinx.util.compat import Directive
from piston.doc import generate_doc

class handlers_doc(nodes.General, nodes.Element): pass

class PistonHandlers(Directive):
    required_arguments = 1

    def run(self):
        module_name = self.arguments[0]
        content = []
        try:
            __import__(module_name)
            content = [handlers_doc()]
        except ImportError:
            self.state.document.reporter.warning("Can't import %s module." % module_name)
        return content

def add_piston_documentation(app, doctree, fromdocname):
    content = []

    from piston.handler import handler_tracker
    for handler in handler_tracker:
        doc = generate_doc(handler)
        title = nodes.title()
        title += nodes.Text(doc.name)
        content.append(title)
        if doc.doc:
            doctitle = nodes.paragraph()
            doctitle += nodes.Text('Docstring:')
            content.append(doctitle)
            docstring = nodes.literal_block()
            docstring += nodes.Text(doc.doc, doc.doc)
            content.append(docstring)
        uri = nodes.literal_block()
        uri += nodes.Text(doc.get_resource_uri_template())
        content.append(uri)
        methods = nodes.paragraph()
        methods_text = nodes.paragraph()
        methods_text += nodes.Text("Accepted methods:")
        methods += methods_text
        accepted_methods = nodes.bullet_list()
        for accepted_method in doc.allowed_methods:
            item = nodes.list_item()
            item_para = nodes.paragraph()
            item_para += nodes.Text(accepted_method)
            item += item_para
            accepted_methods += item
        methods += accepted_methods
        content.append(methods)

    for node in doctree.traverse(handlers_doc):
        node.replace_self(content)

def setup(app):
    app.add_node(handlers_doc)
    app.add_directive('piston_handlers', PistonHandlers)
    app.connect('doctree-resolved', add_piston_documentation)
