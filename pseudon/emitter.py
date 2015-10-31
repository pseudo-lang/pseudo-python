from ast import *

def emit(node):
    return Emitter(TEMPLATES).emit_node(node, 0)

#TODO: support w,s = 4, 2

TEMPLATES = {
    Num:            '{n}',
    Name:           '{id}',
    Assign:         ('(= {target} {value})', lambda f: {'target': f['targets'][0]}),
    Module:         ('(Cell \n{body})\n', "\n", 1)
}

class Emitter:
    def __init__(self, templates, offset=2):
        self.templates = templates
        self.offset = ' ' * offset

    def emit_node(self, node, depth):
        s = self.offset * depth
        if isinstance(node, AST):
            return s + self.emit_template(self.templates[type(node)], node.__dict__, depth)
        else:
            return s + str(node)
    def emit_template(self, template, fields, depth):
        if isinstance(template, str):
            emitted = {field: self.emit_node(node, 0) for field, node in fields.items() if '{%s}' % field in template}
            return template.format(**emitted)
        elif isinstance(template, tuple) and len(template) == 2:
            template, fixer = template
            fix = fixer(fields)
            fields.update(fix)
            emitted = {field: self.emit_node(node, 0) for field, node in fields.items() if '{%s}' % field in template}
            return template.format(**emitted)
        elif isinstance(template, tuple) and len(template) == 3:
            template, sep, offset = template
            emitted = {field: sep.join(self._emit_nodes(node, depth + offset)) for field, node in fields.items() if '{%s}' % field in template}
            return template.format(**emitted)

    def _emit_nodes(self, nodes, depth):
        return [self.emit_node(node, depth) for node in nodes]
