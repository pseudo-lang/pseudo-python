import ast 
import pseudo_python.env
from pseudo_python.builtin_typed_api import TYPED_API, serialize_type
from pseudo_python.errors import PseudoPythonNotTranslatableError, PseudoPythonTypeCheckError
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
        self.definition_index = {'functions': {}}
        self.constants = []
        self.main = []
        self._translate_top_level(self.tree)
        self._translate_pure_functions()
        main = self._translate_main()
        definitions = self._translate_definitions()
        return {'type': 'module', 'dependencies': self.dependencies, 'definitions': definitions, 'main': main}

    def _translate_definitions(self):
        definitions = []
        for definition in self.definitions:
            if definition[0] == 'function':
                if not isinstance(self.definition_index[definition[1]], dict):
                    raise PseudoPythonTypeCheckError("pseudo-python can't infer the types for %s" % definition[1])
                
                definitions.append(self.definition_index[definition[1]])
            elif definition[0] == 'class':
                c = {'type': 'class_definition', 'name': definition[1], 'base': definition[2], 'attrs': self.attrs[definition[1]], 'methods': [], 'constructor': None}
                for method in definition[3]:
                    m = self.definition_index[definition[1][method]]
                    if not isinstance(m, dict):
                        raise PseudoPythonTypeCheckError("pseudo-python can't infer the types for %s#%s" % (definition[1], method))
                    
                    if method == '__init__':
                        c['constructor'] = m
                    else:
                        c['methods'].append(m)

                definitions.append(c)

        return definitions


    def _translate_main(self):
        return list(map(self._translate_node, self.main))

    def _translate_top_level(self, node):
        nodes = node.body
        self.current_constant = None
        for z, n in enumerate(nodes): # placeholders and index 
                                      # for function/class defs to be filled by type inference later
            if isinstance(n, ast.FunctionDef):
                self.definitions.append(('function', n.name))
                self.definition_index['functions'][n.name] = n
                self.type_env.top[n.name] = ([None] * len(n.args.args)) + [None]
            elif isinstance(n, ast.ClassDef):
                self.assert_translatable(decorator_list=([], n.decorator_list))

                if n.bases:
                    if len(n.bases) != 0 or not isinstance(n.bases[0], ast.Name) or n.bases[0].id not in self.definition_index:
                        raise PseudoPythonNotTranslatableError('only single inheritance from an already defined class is supported class %s' % n.name)
                        
                    base = n.bases[0].id
                    self.type_env.top[n.name] = self.type_env.to[base][:]
                else:
                    base = None

                self.definitions.append(('class', n.name, base, []))
                
                self.definition_index[n.name] = {}

                for y, m in enumerate(n.body):
                    if isinstance(m, ast.FunctionDef):
                        if not m.args.args or m.args.args[0].arg != 'self':
                            raise PseudoPythonNotTranslatableError('only methods with a self arguments are supported: %s#%s' % (n.name, m.name))
                        self.definitions[-1][2].append(m.name)
                        self.definition_index[n.name][m.name] = m
                        self.type_env.top[n.name][m.name] = ([None] * (len(m.args.args) - 1)) + [None]
                    else:
                        raise PseudoPythonNotTranslatableError('only methods are supported in classes: %s' % type(m).__name__)
            elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if n.targets[0].id[0].islower():
                    self.main.append(n)
                elif any(letter.isalpha() and letter.islower() for letter in n.targets[0].id[1:]):
                    raise PseudoPythonTypeCheckError('you make pseudo-python very pseudo-confused: please use only snake_case or SCREAMING_SNAKE_CASE for variables %s' % n.targets[0].id)
                elif self.main:
                    raise PseudoPythonNotTranslatableError('%s: constants must be initialized before all other top level code' % n.targets[0].id)
                elif n.targets[0].id in self.type_env.top:
                    raise PseudoPythonNotTranslatableError("you can't override a constant in pseudo-python %s" % n.targets[0].id)
                else:
                    self.current_constant = n.targets[0].id
                    init = self._translate_node(n.value)
                    self.constants.append({
                        'type': 'constant',
                        'name': n.targets[0].id,
                        'init': init,
                        'pseudo_type': init['pseudo_type']
                    })
                    self.type_env.top[init] = init['pseudo_type']
                    self.current_constant = None
            else:
                self.current_constant = None
                self.main.append(n)

    def _translate_node(self, node):
        if isinstance(node, ast.AST):
            if self.current_constant and type(node) not in [ast.Num, ast.Str, ast.List]:
                raise PseudoPythonNotTranslatableError('You can initialize constants only with literals %s' % self.current_constant)
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
        return {'type': type, 'value': n, 'pseudo_type': type.title()}

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
            elif self.general_type(func_node['object']['pseudo_type']) in PSEUDON_BUILTIN_TYPES: # [2].append
                return self._translate_builtin_method_call(self.general_type(func_node['object']['pseudo_type']), func_node['object'], func_node['attr'], arg_nodes)
            else:
                node_type = 'method_call'

            return self._translate_real_method_call(node_type, self.general_type(func_node['object']['pseudo_type']), receiver, func_node['attr'], arg_nodes)

        else:
            if func_node['type'] == 'local' and func_node['pseudo_type'][-1] is None:
                return self._translate_real_method_call('call', 'functions', None, func_node['name'], arg_nodes)
            elif func_node['type'] == 'typename':
                return self._translate_init(func_node['name'], arg_nodes)
            else:
                z = func_node['pseudo_type'][-1]
                return {'type': 'call', 'function': func_node, 'args': arg_nodes, 'pseudo_type': z}

    def _translate_init(self, name, params):

        # check or save with the params
        # translate this function and then the pure functions in class
        class_types = self.type_env.top.get(func_node['name'], None)
        if class_types is None:
            raise PseudoPythonTypeCheckError("%s doesnt't exist" % name)
        init = class_types.get('__init__')
        if init is None and arg_nodes:
            raise PseudoPythonTypeCheckError('constructor of %s didn\'t expect %d arguments' % (name, len(params)))

        if init:
            self._translate_function(self.definition_index[name]['__init__'], name, {'pseudo_type': name}, '__init__', [p['pseudo_type'] for p in params])
            init[-1] = name

        for label, m in self.definition_index[name].items():
            if len(self.type_env.top[name][label]) == 1:
                self._translate_function(m, name, {'pseudo_type': name}, label, [])


    def _translate_real_method_call(node_type, z, receiver, message, params):
        c = self.type_env.top[z]
        if message in c:
            q = self.type_check(z, message, params)[-1]
        else:
            param_types = [param['pseudo_type'] for param in params]
            self.definition_index[z][message] = self._translate_function(self.definition_index[z][message], z, receiver, message, param_types)
            q = c[message][-1]

        if node_type == 'call':
            result = {'type': node_type, 'function': {'type': 'local', 'name': message}, 'args': params, 'pseudo_type': q}
        else:
            result = {'type': node_type, 'message': message, 'args': params, 'pseudo_type': q}
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

    def _translate_builtin_method_call(self, class_type, base, message, args):
        api = METHOD_API.get(class_type, {}).get(message)
        if not api:
            raise PseudoPythonNotTranslatableError('pseudo-python doesn\'t support %s#%s' % (serialize_type(class_type), message))

        if isinstance(api, Standard):
            return api.expand([base] + args)
        else:
            for count,(a, b)  in api.items():
                if len(args) == count:
                    return b.expand([base] + args)
            raise PseudoPythonNotTranslatableError(
                'pseudo-python doesn\'t support %s%s with %d args' % (serialize_type(class_type), message, len(args)))

    def _translate_function(self, node, z, receiver, name, args):
        self.assert_translatable('functiondef', 
            vararg=([], node.arg.vararg), kwonlyargs=([], node.arg.kwonlyargs), 
            kw_defaults=([], node.arg.kw_defaults), defaults=([], node.arg.defaults), 
            decorator_list=([], node.decorator_list))

        node_args = node.args.args if z == 'functions' else node.args.args[1:]

        if len(node.args.args) != len(args):
            raise PseudoPythonTypeCheckError('%s expecting %d args' % (node.name, len(node.args.args)))
        
        # 0-arg functions are inferred only in the beginning

        if args and self.type_env.top[z][name][0]:
            raise PseudoPythonTypeCheckError("please move recursion in a next branch in %s" % node.name)

        env = {a.arg: type for a, type in zip(node_args, args)}
        env['self'] = receiver['pseudo_type']
        self.type_env, old_type_env = self.type_env.top.child_env(env), self.type_env
        self.type_env.top[z][name][:-1] = args

        outer_current_class, self.current_class = self.current_class, z
        outer_function_name, self.function_name = self.function_name, message

        children = list(map(self._generate_node, node.body))

        self.function_name = outer_function_name
        self.current_class = outer_current_class

        self.type_env = old_type_env


        if z == 'functions':
            type = 'function_definition'
        elif name == '__init__':
            type = 'constructor'
        else:
            type = 'function_definition' 
             
        q = {
            'type':   type,
            'name':   name,
            'params': [node_arg.arg for node_arg in node_args],
            'pseudo_type': self.type_env.top[z][name],
            'return_type': self.type_env.top[z][name][-1],
            'block': children
        }
        if z != 'functions':
            q['this'] = {'type': 'typename', 'name': z}
        return q

    def _translate_expr(self, value):
        return self._translate_node(value)

    def _translate_return(self, value):
        value_node = self._translate_node(value)
        whiplash = self.type_env.top[self.current_class][self.function_name]
        if whiplash[-1] and whiplash[-1] != value_node['pseudo_type']:
            raise PseudoPythonTypeCheckError("didn't expect %s return type for %s" % (value_node['pseudo_type'], self.function_name))
        elif whiplash[-1] is None:
            whiplash[-1] = value_node['type_env']
        
        return {
            'type': 'explicit_return', 
            'value': value_node,
            'pseudo_type': value_node['pseudo_type']
        }

    def _translate_binop(self, op, left, right):
        return {'type': 'binary', 'left': self._translate_node(left),
                'right': self._translate_node(right), 'op': OPS[op.__class__]}

    def assert_translatable(self, node, **pairs):
        for label, (expected, actual) in pairs.items():
            if actual != expected:
                raise PseudoPythonNotTranslatableError("%s in %s is not a part of pseudo-translatable python" % (label, node))

    def _translate_pure_functions(self):
        for f in self.definitions:
            if f[0] == 'function' and len(self.type_env['functions'][f[1]]) == 1:
                self.definition_index['functions'][f[1]] = self._translate_function(self.definition_index['functions'][f[1]], 'functions', None, f[1], [])
