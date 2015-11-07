from ast import AST
from pseudon.templates import TEMPLATES


def emit(node):
    return Emitter(TEMPLATES).emit_node(node, 0)


class Emitter:

    def __init__(self, templates, offset=2):
        self.templates = templates
        self.offset = ' ' * offset

    def emit_node(self, node, depth):
        s = self.offset * depth
        if isinstance(node, AST):
            return s + self.emit_template(self.templates[type(node)], node.__dict__, depth)
        elif isinstance(node, list):
            if depth > 0:
                return '\n'.join(self.emit_node(n, depth + 1) for n in node)
            else:
                return ' '.join(self.emit_node(n, 0) for n in node)
        else:
            return s + str(node)

    def emit_template(self, template, fields, depth):
        if isinstance(template, str):
            emitted = {field: self.emit_node(
                node, 0) for field, node in fields.items() if '{%s}' % field in template}
            return template.format(**emitted)

        elif isinstance(template, tuple) and len(template) == 2:
            template, fixer = template
            fix = fixer(fields)
            fields.update(fix)
            emitted = {field: self.emit_node(
                node, 0) for field, node in fields.items() if '{%s}' % field in template}
            return template.format(**emitted)

        elif isinstance(template, tuple) and len(template) == 3:
            template, sep, offset = template
            emitted = {field: sep.join(self._emit_nodes(node, depth + offset))
                       for field, node in fields.items() if '{%s}' % field in template}
            return template.format(**emitted)

    def _emit_nodes(self, nodes, depth):
        return [self.emit_node(node, depth) for node in nodes]
