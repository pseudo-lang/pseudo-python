import ast 
import pseudo_python.env
from pseudo_python.builtin_typed_api import TYPED_API, serialize_type
from pseudo_python.errors import PseudoPythonNotTranslatableError
from pseudo_python.api_translator import Standard, StandardCall, StandardMethodCall, FUNCTION_API, METHOD_API

BUILTIN_TYPES = {
    'int':      'Int',
    'float':    'Float',
    'object':   'Object',
    'str':      'String',
    'list':     'List',
    'dict':     'Dictionary',

}

PSEUDON_BUILTIN_TYPES = {v: k for k, v in BUILTIN_TYPES.items()}

BUILTIN_FUNCTIONS = {'print', 'input', 'str', 'int'}

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
        self.type_env = pseudo_python.env.Env(TYPED_API, None)

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
        arg_nodes = self._translate_node(args)

        if isinstance(func_node, ast.Name) and func_node.id in BUILTIN_FUNCTIONS:
            return self._translate_builtin_call('global', func.node.id, arg_nodes)

        func_node = self._translate_node(func)

        if func_node['type'] == 'attr':
            if func_node['object']['pseudo_type'] == 'library': # math.log
                return self._translate_builtin_call(func_node['object']['name'], func_node['attr'], arg_nodes)
            elif self.in_class and isinstance(func.value, ast.Name) and func.value.id == 'self':
                node_type = 'this_method_call'
            elif func_node['object']['pseudo_type'] in PSEUDON_BUILTIN_TYPES: # [2].append
                return self._translate_builtin_method_call(func_node['object'], func_node['attr'], arg_nodes)
            else:
                node_type = 'method_call'

            return self._translate_real_method_call(node_type, func_node['object']['pseudo_type'], receiver, func_node['attr'], arg_nodes)

        else:
            if func_node['type'] == 'local' and func_node['pseudo_type'] == 'unknown_type':
                return self._translate_real_method_call('call', 'functions', None, func_node['name'], arg_nodes)
            else:
                z = func_node['pseudo_type'][-1]
                return {'type': 'call', 'function': func_node, 'args': arg_nodes, 'pseudo_type': z}

    def _translate_real_method_call(node_type, z, receiver, message, arg_nodes):
        c = self.type_env.top[z]
        if message in c:
            q = self.type_check(z, message, arg_nodes)[-1]
        else:
            arg_types = [arg_node['pseudo_type'] for arg_node in arg_nodes]
            for j, (l, f) in enumerate(self.definitions):
                if l == message:
                    self.definitions[j] = self._translate_function(f, z, arg_types)
                    break
            q = c[message][-1]

        if node_type == 'call':
            result = {'type': node_type, 'function': {'type': 'local', 'name': message}, 'args': arg_nodes, 'pseudo_type': q}
        else:
            result = {'type': node_type, 'message': message, 'args': arg_nodes, 'pseudo_type': q}
            if node_type == 'method_call':
                result['receiver'] = receiver
        return result

    def _translate_builtin_call(self, namespace, function, args):
        api = FUNCTION_API.get(namespace, {}).get(function)
        if not api:
            raise PseudoPythonNotTranslatableError('pseudo doesn\'t support %s%s' % (namespace, function))

        if isinstance(api, tuple):
            return api.expand(args)
        else:
            for count,(a, b)  in api.items():
                if len(args) == count:
                    return b.expand(args)
            raise PseudoPythonNotTranslatableError(
                'pseudo-python doesn\'t support %s%s with %d args' % (namespace, function, len(args)))

    def _translate_builtin_method_call(self, class_type, message, args):
        api = METHOD_API.get(class_type, {}).get(message)
        if not api:
            raise PseudoPythonNotTranslatableError('pseudo-python doesn\'t support %s#%s' % (serialize_type(class_type), message))

        if isinstance(api, Standard):
            return api.expand(args)
        else:
            for count,(a, b)  in api.items():
                if len(args) == count:
                    return b.expand(args)
            raise PseudoPythonNotTranslatableError(
                'pseudo-python doesn\'t support %s%s with %d args' % (serialize_type(class_type), message, len(args)))

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

    def assert_translatable(self, node, **pairs):
        for label, (expected, actual) in pairs.items():
            if actual != expected:
                raise PseudoPythonNotTranslatableError("%s in %s is not a part of pseudo-translatable python" % (label, node))

    def is_self_method_call(self, node):
        return node.type == 'method_call' and node.receiver.type == 'local' and node.receiver.name == 'self'
