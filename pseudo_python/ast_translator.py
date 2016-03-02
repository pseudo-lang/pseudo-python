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
        self._definition_index = {'functions': {}}
        self.constants = []
        self.main = []
        self._hierarchy = {}
        self._attr_index = {}
        self._attrs = {}
        self.type_env['functions'] = {}
        self._translate_top_level(self.tree)
        self._translate_pure_functions()
        main = self._translate_main()
        definitions = self._translate_definitions()

        return {'type': 'module', 'dependencies': self.dependencies, 'constants': self.constants, 'definitions': definitions, 'main': main}

    def _translate_definitions(self):
        definitions = []
        for definition in self.definitions:
            if definition[0] == 'function':
                if not isinstance(self._definition_index['functions'][definition[1]], dict):
                    raise PseudoPythonTypeCheckError("pseudo-python can't infer the types for %s" % definition[1])

                definitions.append(self._definition_index['functions'][definition[1]])
            elif definition[0] == 'class':  #inherited
                c = {'type': 'class_definition', 'name': definition[1], 'base': definition[2],
                     'attrs': [self._attr_index[definition[1]][a][0]
                               for a
                               in self._attrs[definition[1]] if not self._attr_index[definition[1]][a][0]], 'methods': [], 'constructor': None}
                for method in definition[3]:
                    m = self._definition_index[definition[1][method]]
                    if not isinstance(m, dict):
                        raise PseudoPythonTypeCheckError("pseudo-python can't infer the types for %s#%s" % (definition[1], method))

                    if method == '__init__':
                        c['constructor'] = m
                    else:
                        c['methods'].append(m)

                definitions.append(c)

        return definitions

    # def _serialize_node(self, node):
    #     if isinstance(node, dict):
    #         pseudo_type = node.get('pseudo_type')
    #         if pseudo_type:
    #             node['pseudo_type'] = serialize_type(node['pseudo_type'])
    #         for _, child in node.items():
    #             self._serialize_node(child)
    #     elif isinstance(node, list):
    #         for l in node:
    #             self._serialize_node(l)
    #     return node

    def _translate_main(self):
        self.current_class = None
        self.function_name = 'global scope'
        return list(map(self._translate_node, self.main))

    def _translate_top_level(self, node):
        nodes = node.body
        self.current_constant = None
        for z, n in enumerate(nodes): # placeholders and index
                                      # for function/class defs to be filled by type inference later
            if isinstance(n, ast.FunctionDef):
                self.definitions.append(('function', n.name))
                self._definition_index['functions'][n.name] = n
                self.type_env.top['functions'][n.name] = ['Function'] + ([None] * len(n.args.args)) + [None]
                self.type_env.top[n.name] = self.type_env.top['functions'][n.name]
            elif isinstance(n, ast.ClassDef):
                self.assert_translatable(decorator_list=([], n.decorator_list))
                self._hierarchy[n.name] = (None, set())
                if n.bases:
                    if len(n.bases) != 0 or not isinstance(n.bases[0], ast.Name) or n.bases[0].id not in self._definition_index:
                        raise PseudoPythonNotTranslatableError('only single inheritance from an already defined class is supported class %s' % n.name)

                    base = n.bases[0].id
                    self.type_env.top[n.name] = self.type_env.to[base][:]
                    self._attr_index[n.name][l] = {l: [t[0], True] for l, t in self._attr_index[base].items()}
                    self._hierarchy[n.name] = (base, set())
                    self._hierarchy[base][1].add(n.name)
                else:
                    base = None

                self.definitions.append(('class', n.name, base, []))

                self._definition_index[n.name] = {}
                self._attrs[n.name] = []


                for y, m in enumerate(n.body):
                    if isinstance(m, ast.FunctionDef):
                        if not m.args.args or m.args.args[0].arg != 'self':
                            raise PseudoPythonNotTranslatableError('only methods with a self arguments are supported: %s#%s' % (n.name, m.name))
                        self.definitions[-1][2].append(m.name)
                        self._definition_index[n.name][m.name] = m
                        self.type_env.top[n.name][m.name] = ['Function'] + ([None] * (len(m.args.args) - 1)) + [None]
                    else:
                        raise PseudoPythonNotTranslatableError('only methods are supported in classes: %s' % type(m).__name__)
            elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if n.targets[0].id[0].islower():
                    self.main.append(n)
                elif any(letter.isalpha() and letter.islower() for letter in n.targets[0].id[1:]):
                    raise PseudoPythonTypeCheckError('you make pseudo-python very pseudo-confused: please use only snake_case or SCREAMING_SNAKE_CASE for variables %s' % n.targets[0].id)
                elif self.main:
                    raise PseudoPythonNotTranslatableError('%s: constants must be initialized before all other top level code' % n.targets[0].id)
                elif self.type_env.top[n.targets[0].id]:
                    raise PseudoPythonNotTranslatableError("you can't override a constant in pseudo-python %s" % n.targets[0].id)
                else:
                    self.current_constant = n.targets[0].id
                    init = self._translate_node(n.value)
                    self.constants.append({
                        'type': 'constant',
                        'constant': n.targets[0].id,
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
            if id not in self.type_env.top.values:
                raise PseudoPythonTypeCheckError('%s is not defined' % id)
            id_type = self.type_env.top[id]
            if isinstance(id_type, dict): # class
                id_type = id
            return {'type': 'typename', 'name': id, 'pseudo_type': id_type}
        else:
            id_type = self.type_env[id]
            if id_type is None:
                raise PseudoPythonTypeCheckError('%s is not defined' % id)

            # if isinstance(id_type, list):
            # id_type = tuple(['Function'] + id_type)

            return {'type': 'local', 'name': id, 'pseudo_type': id_type}

    def _translate_call(self, func, args, keywords, starargs, kwargs):
        self.assert_translatable('call', keywords=([], keywords), starargs=(None, starargs), kwargs=(None, kwargs))
        arg_nodes = self._translate_node(args)

        if isinstance(func, ast.Name) and func.id in BUILTIN_FUNCTIONS:
            return self._translate_builtin_call('global', func.id, arg_nodes)

        func_node = self._translate_node(func)

        print(func_node)
        if func_node['type'] == 'attr':
            if func_node['object']['pseudo_type'] == 'library': # math.log
                return self._translate_builtin_call(func_node['object']['name'], func_node['attr'], arg_nodes)
            elif self.current_class and self.current_class != 'functions' and isinstance(func.value, ast.Name) and func.value.id == 'self':
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
        if init is None and params:
            raise PseudoPythonTypeCheckError('constructor of %s didn\'t expect %d arguments' % (name, len(params)))

        if init:
            self._translate_function(self._definition_index[name]['__init__'], name, {'pseudo_type': name}, '__init__', [p['pseudo_type'] for p in params])
            init[-1] = name

        for label, m in self._definition_index[name].items():
            if len(self.type_env.top[name][label]) == 2:
                self._translate_function(m, name, {'pseudo_type': name}, label, [])


    def _translate_real_method_call(self, node_type, z, receiver, message, params):
        c = self.type_env.top[z]
        param_types = [param['pseudo_type'] for param in params]
        if message in c and len(c[message]) == 2 or len(c[message]) > 2 and c[message][1]:
            q = self._type_check(z, message, param_types)[-1]
        else:
            self._definition_index[z][message] = self._translate_function(self._definition_index[z][message], z, receiver, message, param_types)
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
            vararg=(None, node.args.vararg), kwonlyargs=([], node.args.kwonlyargs),
            kw_defaults=([], node.args.kw_defaults), defaults=([], node.args.defaults),
            decorator_list=([], node.decorator_list))

        node_args = node.args.args if z == 'functions' else node.args.args[1:]

        if len(node.args.args) != len(args):
            raise PseudoPythonTypeCheckError('%s expecting %d args' % (node.name, len(node.args.args)))

        # 0-arg functions are inferred only in the beginning

        if args and self.type_env.top[z][name][1]:
            raise PseudoPythonTypeCheckError("please move recursion in a next branch in %s" % node.name)

        env = {a.arg: type for a, type in zip(node_args, args)}
        if receiver:
            env['self'] = receiver['pseudo_type']
        self.type_env, old_type_env = self.type_env.top.child_env(env), self.type_env
        self.type_env.top[z][name][1:-1] = args

        outer_current_class, self.current_class = self.current_class, z
        outer_function_name, self.function_name = self.function_name, name

        children = []
        self.is_last = False
        for j, child in enumerate(node.body):
            if j == len(node.body) - 1:
                self.is_last = True
            children.append(self._translate_node(child))
            print(self.type_env.values)
            print(args);input()
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
            if name != '__init__':
                q['is_public'] = name[0] != '_'
        return q

    def _translate_expr(self, value):
        return self._translate_node(value)

    def _translate_return(self, value):
        value_node = self._translate_node(value)
        whiplash = self.type_env.top[self.current_class][self.function_name]
        if whiplash[-1] and whiplash[-1] != value_node['pseudo_type']:
            raise PseudoPythonTypeCheckError("didn't expect %s return type for %s" % (value_node['pseudo_type'], self.function_name))
        elif whiplash[-1] is None:
            whiplash[-1] = value_node['pseudo_type']

        return {
            'type': 'explicit_return' if not self.is_last else 'implicit_return',
            'value': value_node,
            'pseudo_type': value_node['pseudo_type']
        }

    def _translate_binop(self, op, left, right):
        return {'type': 'binary', 'left': self._translate_node(left),
                'right': self._translate_node(right), 'op': OPS[op.__class__]}

    def _translate_attribute(self, value, attr, ctx):
        value_node = self._translate_node(value)
        if not isinstance(value_node['pseudo_type'], str):
            raise PseudoPythonTypeCheckError("you can't access attr of %s, only of normal objects or modules" % (serialize_type(value_node['pseudo_type'])))

        if value_node['type'] == 'library':
            return {
                'type': 'library_function',
                'library': value_node['name'],
                'function': attr,
                'pseudo_python': None
            }

        else:
            attr_type = self._attrs.get(value_node['pseudo_type'])
            if attr_type is None:
                raise PseudoPythonTypeCheckError("pseudo-python can't infer the type of %s.%s" % (value_node['pseudo_type'], attr))

            return {
                'type': 'attr',
                'object': value_node,
                'attr': attr,
                'pseudo_type': attr_type
            }

    def _translate_assign(self, targets, value):
        value_node = self._translate_node(value)
        if isinstance(targets[0], ast.Name):
            name = targets[0].id
            e = self.type_env[name]
            if e:
                a = self._compatible_types(e, value_node['pseudo_type'], "can't change the type of variable %s in " % (name, self.function_name))
            else:
                a = value_node['pseudo_type']
            self.type_env[name] = a
            return {
                'type': 'local_assignment',
                'local': name,
                'value': value_node,
                'pseudo_python': 'Void',
                'value_type': value_node['pseudo_type']
            }
        elif isinstance(targets[0], ast.Attribute):
            z = self._translate_node(targets[0].value)
            if z['pseudo_type'] == 'library':
                raise PseudoPythonTypeCheckError("pseudo-python can't redefine a module function %s" % z['name'] + ':' + targets[0].attr)

            is_public = not isinstance(targets[0].value, ast.Name) or targets[0].value.id != 'self'

            if targets[0].attr in self._attr_index[z['pseudo_type']]:
                a = self._compatible_types(self._attr_index[z['pseudo_type']][targets[0].attr][0]['pseudo_type'],
                                           value_node['pseudo_type'], "can't change attr type of " % z['pseudo_type'] + '.' + targets[0].attr)
                self._attr_index[z['pseudo_type']][targets[0].attr][0]['pseudo_type'] = a
                if is_public:
                    self._attr_index[z['pseudo_type']][targets[0].attr][0]['is_public'] = True
            else:
                a = value_node['pseudo_type']
                self._attr_index[z['pseudo_type']][targets[0].attr] = [{
                    'type': 'class_attr',
                    'name':  targets[0].attr,
                    'pseudo_type': a,
                    'is_public': is_public,
                }, False]

                self._attrs[z['pseudo_type']].append(targets[0].attr)


            return {
                'type': 'attr_assignment',
                'attr': {
                    'type': 'attr',
                    'object': z,
                    'attr': targets[0].attr,
                    'pseudo_type': a
                 },
                'value': value_node,
                'pseudo_type': 'Void'
            }
            #return self._translate_builtin_call(z['name'], targets[0].attr, [value_node])


    def _translate_list(self, elts, ctx):
        if not elts:
            return {'type': 'list', 'elements': [], 'pseudo_type': ['List', None]}

        element_nodes = [self._translate_node(elts[0])]
        element_type = element_nodes[0]['pseudo_type']
        for j in enumerate(elts[1:]):
            element_nodes.append(self._translate_node(elts[j + 1]))
            element_type = self._compatible_types(element_type, element_node[-1]['pseudo_type'], "can't use different types in a list")

        return {
            'type': 'list',
            'pseudo_type': ['List', element_type],
            'elements': element_nodes
        }

    def _translate_dict(self, keys, values):
        if not keys:
            return {'type': 'dictionary', 'pairs': [], 'pseudo_type': ['Dictionary', None, None]}

        pairs = [{'type': 'pair', 'key': self._translate_node(keys[0]), 'value': self._translate_node(values[0])}]
        key_type, value_type = pairs[0]['key']['pseudo_type'], pairs[0]['value']['pseudo_type']
        for a, b in zip(keys[1:], values[1:]):
            pairs.append({'type': 'pair', 'key': self._translate_node(a), 'value': self._translate_node(b)})
            key_type, value_type = self._compatible_types(key_type, pairs[-1]['key']['pseudo_type'], "can't use different types for keys of a dictionary"),\
                                   self._compatible_types(value_type, pairs[-1]['value']['pseudo_type'], "can't use different types for values of a dictionary")

        return {
            'type': 'dictionary',
            'pseudo_type': ['Dictionary', key_type, value_type],
            'pairs': pairs
        }

    def _translate_subscript(self, value, slice, ctx):
        value_node = self._translate_node(value)
        value_general_type = self.general_type(value_node['pseudo_type'])
        if value_general_type not in ['String', 'List', 'Dictionary']:
            raise PseudoPythonTypeCheckError('pseudo-python can use [] only on str, list or dict: %s' % value_node['pseudo_type'])

        if isinstance(slice, ast.Index):
            z = self._translate_node(slice.value)
            if value_general_type in ['String', 'List'] and z['pseudo_type'] != 'Int':
                raise PseudoPythonTypeCheckError('a non int index for %s %s' % (value_general_type, z['pseudo_type']))

            if value_general_type == 'Dictionary' and z['pseudo_type'] != value_node['pseudo_type'][1]:
                raise PseudoPythonTypeCheckError('a non %s index for %s %s' % (value_node['pseudo_type'][1], value_general_type, z['pseudo_type']))

            if value_general_type == 'String':
                pseudo_type = 'String'
            elif value_general_type == 'List':
                pseudo_type = value_node['pseudo_type'][1]
            else:
                pseudo_type = value_node['pseudo_type'][2]

            return {
                'type': 'index',
                'sequence': value_node,
                'index': z,
                'pseudo_type': pseudo_type
            }

        else:
            z = self._translate_node(slice)

        pass

    def assert_translatable(self, node, **pairs):
        for label, (expected, actual) in pairs.items():
            if actual != expected:
                raise PseudoPythonNotTranslatableError("%s in %s is not a part of pseudo-translatable python" % (label, node))

    def _translate_pure_functions(self):
        for f in self.definitions:
            print(self.type_env.values)
            if f[0] == 'function' and len(self.type_env['functions'][f[1]]) == 2:
                self._definition_index['functions'][f[1]] = self._translate_function(self._definition_index['functions'][f[1]], 'functions', None, f[1], [])

    def _type_check(self, z, message, types):
        g = self.type_env.top.values.get(z, {}).get(message)
        if not g:
            raise PseudoPythonTypeCheckError("%s is not defined" % message)

        if len(g) - 1 != len(types):
            raise PseudoPythonTypeCheckError("%s expected %d args" % (message, len(g)))

        for j, (a, b) in enumerate(zip(g[:-1], types)):
            general = self._compatible_types(b, a, "can't convert %s#%s %dth arg" % (z, message, j))

        return g

    def _compatible_types(self, from_, to, err):
        if isinstance(from_, str):
            if not isinstance(to, str):
                raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (from_, to))

            elif from_ == to:
                return to

            elif from_ in self._hierarchy:
                if to not in self._hierarchy or from_ not in self._hierarchy[to][1]:
                    raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (from_, to))
                return to

            elif from_ == 'Int' and to == 'Float':
                return 'Float'

            else:
                raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (from_, to))
        else:
            if not isinstance(to, tuple) or len(from_) != len(to) or from_[0] != to[0]:
                raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (from_, to))

            for f, t in zip(from_, to):
                self._compatible_types(f, t, err)

            return to


    def general_type(self, t):
        if isinstance(t, list):
            return t[0]
        else:
            return t
