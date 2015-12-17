import ast
import yaml

BUILTIN_TYPES = {
    'int': 'Int',
    'float': 'Float',
    'object': 'Object',
    'str': 'String'
}


class ASTTranslator:

    def __init__(self, tree):
        self.tree = tree
        self.in_class = False

    def translate(self):
        return yaml.dump(self._translate_node(self.tree))

    def _translate_node(self, node):
        if isinstance(node, ast.AST):
            return getattr('_translate_%s' % type(node).__name__)(**node.__dict__)
        elif isinstance(node, list):
            return [self._translate_node(n) for n in node]
        elif isinstance(node, dict):
            return {k: self._translate_node(v) for k, v in node.items()}
        else:
            return node

    def _translate_module(self, body):
        return {'type': 'program', 'code': self._translate_node(body)}

    def _translate_int(self, n):
        return {'type': 'int', 'value': n}

    def _translate_name(self, id):
        if id[0].isupper():
            return {'type': 'typename', name: id}
        else:
            return {'type': 'local', name: id}

    def _translate_functiondef(self, name, args, body, decorator_list, returns):
        if decorator_list:
            raise NotImplementedError("Decorators not implemented")
        type = 'function' if not self.in_class else 'method'
        args = arg.args[1:] if self.in_class else arg.args  # noclass methods
        arg_type_hints = [self._type_hint(arg.annotation) for arg in args.args]
        return {'type': type,
                'args': self._translate_node(args),
                'body': self._translate_node(body),
                'type_hint': arg_type_hints + [self._type_hint(returns)]}

    def _type_hint(self, type):
        if type is None:
            return '@unknown'
        elif not hasattr(type, 'id'):
            if isinstance(type, ast.List):
                return [self._type_hint(type.elts[0])]
            else:
                raise NotImplementedError("Unknown type")
        elif type.id in BUILTIN_TYPES:
            return BUILTIN_TYPES[type.id]
        else:
            return type.id
