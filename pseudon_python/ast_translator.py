import ast
import pseudon_python.env
from pseudon_python.builtin_typed_api import TYPED_API
from pseudon_python.errors import PseudonPythonNotTranslatableError

BUILTIN_TYPES = {
    'int':      'Int',
    'float':    'Float',
    'object':   'Object',
    'str':      'String',
}

OPS = {
    ast.Add:  '+',
    ast.Sub:  '-',
    ast.Div:  '/',
    ast.Pow:  '**',
    ast.Mult: '*'
}


class ASTTranslator:

    def __init__(self, tree):
        self.tree = tree
        self.in_class = False
        self.type_env = pseudon_python.env.Env(TYPED_API, None)

    def translate(self):
        self.dependencies = []
        self.definitions = []
        self.main = []
        return self._translate_node(self.tree)

    def _translate_node(self, node):
        if isinstance(node, ast.AST):
            fields = {field: getattr(node, field) for field in node._fields}
            return getattr(self, '_translate_%s' % type(node).__name__.lower())(**fields)
        elif isinstance(node, list):
            return [self._translate_node(n) for n in node]
        elif isinstance(node, dict):
            return {k: self._translate_node(v) for k, v in node.items()}
        else:
            return node

    def _translate_module(self, body):
        ordered = []
        main = []
        for c in body:
            if isinstance(c, (ast.FunctionDef, ast.ClassDef)):
                ordered.append(c)
            else:
                main.append(c)
        main_node = self._translate_main(main)
        ordered_nodes = [self._translate_node(node) for node in ordered[:-1]][:-1]
        return {'type': 'module', 'code': ordered_nodes, 'main': main}


    def _translate_num(self, n):
        type = 'int' if isinstance(n, int) else 'float'
        return {'type': type, 'value': n}

    def _translate_name(self, id, ctx):
        if id[0].isupper():
            return {'type': 'typename', 'name': id}
        else:
            return {'type': 'local', 'name': id}

    def _translate_call(self, func, args, keywords, stararg, kwarg):
        self.assert_translatable('call', keywords=([], keywords), stararg=(None, stararg), kwarg=(None, kwarg))
        func_node = self._translate_node(func)
        arg_nodes = self._translate_node(args)

        if self.is_name(func_node) and self.in_class and self.is_self_method_call(func_node):
            c = self.type_env.top[self.current_class]
            if func_node.func.id in c:
                q = self.type_check(c[func_node.func.id], arg_nodes)
            else:
                c[func_node.func.id] = tuple([arg_node['pseudon_type'] for arg_node in arg_nodes] + [None])
                for j, (l, f) in enumerate(self.definitions):
                    if l == func_node.func.id:
                        self.definitions[j] = self._translate_node(f)
                q = c[func_node.func.id]

            return {'type': 'this_method_call', 'message': func_node.func.id, 'args': arg_nodes, 'pseudon_type': q}

    def _translate_functiondef(self, name, args, body, decorator_list, returns):
        if decorator_list:
            raise NotImplementedError("Decorators not implemented")
        type = 'function' if not self.in_class else 'method'
        args = args.args[1:] if self.in_class else args.args  # noclass methods
        arg_type_hints = [self._type_hint(arg.annotation) for arg in args]
        return {'type': type,
                'name': name,
                'args': [{'type': 'local', 'name': arg.arg, 'type_hint': type_a} for arg, type_a in zip(args, arg_type_hints)],
                'body': self._translate_node(body),
                'type_hint': arg_type_hints + [self._type_hint(returns)]}

    def _translate_expr(self, value):
        return self._translate_node(value)

    def _translate_return(self, value):
        return {'type': 'return', 'value': self._translate_node(value)}

    def _translate_binop(self, op, left, right):
        return {'type': 'binary', 'left': self._translate_node(left),
                'right': self._translate_node(right), 'op': OPS[op.__class__]}

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

    def assert_translatable(self, node, **pairs):
        for label, (expected, actual) in pairs.items():
            if actual != expected:
                raise PseudonPythonNotTranslatableError("%s in %s is not a part of pseudon-translatable python" % (label, node))

    def is_self_method_call(self, node):
        return node.type == 'method_call' and node.receiver.type == 'local' and node.receiver.name == 'self'
