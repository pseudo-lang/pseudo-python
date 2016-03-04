import ast
import pseudo_python.env
from pseudo_python.builtin_typed_api import TYPED_API
from pseudo_python.errors import PseudoPythonNotTranslatableError, PseudoPythonTypeCheckError, cant_infer_error, translation_error, type_check_error
from pseudo_python.api_translator import Standard, StandardCall, StandardMethodCall, FUNCTION_API, METHOD_API, OPERATOR_API
from pseudo_python.helpers import serialize_type, prepare_table

BUILTIN_TYPES = {
    'int':      'Int',
    'float':    'Float',
    'object':   'Object',
    'str':      'String',
    'list':     'List',
    'dict':     'Dictionary',
    'set':      'Set',
    'tuple':    'Tuple',
    'SRE_Pattern': 'Regexp',
    'SRE_Match': 'RegexpMatch'
}

PSEUDON_BUILTIN_TYPES = {v: k for k, v in BUILTIN_TYPES.items()}

BUILTIN_FUNCTIONS = {'print', 'input', 'str', 'int'}

ITERABLE_TYPES = {'String', 'List', 'Dictionary', 'Set', 'Array'}

TESTABLE_TYPE = 'Boolean'

INDEXABLE_TYPES = {'String', 'List', 'Dictionary', 'Array', 'Tuple'}

COMPARABLE_TYPES = {'Int', 'Float', 'String'}

TYPES_WITH_LENGTH = {'String', 'List', 'Dictionary', 'Array', 'Tuple', 'Set'}

NUMBER_TYPES = {'Int', 'Float'}

PSEUDO_OPS = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Div: '/',
    ast.Mult: '*',
    ast.And: 'and',
    ast.Pow: '**',

    ast.Eq: '==',
    ast.Lt: '<',
    ast.Gt: '>',
    ast.Mod: '%'
}



class ASTTranslator:

    def __init__(self, tree, code):
        self.tree = tree
        self.in_class = False
        self.lines = [''] + code.split('\n') # easier 1based access with lineno
        self.type_env = pseudo_python.env.Env(TYPED_API, None)

    def translate(self):
        self.dependencies = []
        self.definitions = []
        self._definition_index = {'functions': {}}
        self.constants = []
        self.main = []
        self._exceptions = {'Exception'}
        self._hierarchy = {}
        self._attr_index = {}
        self._attrs = {}
        self._imports = set()
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
                    raise cant_infer_error(definition[1])

                definitions.append(self._definition_index['functions'][definition[1]])
            elif definition[0] == 'class':  #inherited
                c = {'type': 'class_definition', 'name': definition[1], 'base': definition[2],
                     'attrs': [self._attr_index[definition[1]][a][0]
                               for a
                               in self._attrs[definition[1]] if not self._attr_index[definition[1]][a][1]], 'methods': [], 'constructor': None}
                for method in definition[3]:
                    # print(definition[1], method, self._definition_index)
                    m = self._definition_index[definition[1]][method]
                    if not isinstance(m, dict):
                        raise cant_infer_error('%s#%s' % (definition[1], method))

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
            if isinstance(n, ast.Import):
                if self.definitions or self.main:
                    raise translation_error('imports can be only on top', (n.lineno, n.col_offset), self.lines[n.lineno])

                self._imports.add(n.names[0].name)
                self.type_env.top['_%s' % n.names[0].name], self.type_env.top[n.names[0].name] = self.type_env.top[n.names[0].name], 'library'

            elif isinstance(n, ast.FunctionDef):
                self.definitions.append(('function', n.name))
                self._definition_index['functions'][n.name] = n
                self.type_env.top['functions'][n.name] = ['Function'] + ([None] * len(n.args.args)) + [None]
                self.type_env.top[n.name] = self.type_env.top['functions'][n.name]
            elif isinstance(n, ast.ClassDef):
                self.assert_translatable('class', decorator_list=([], n.decorator_list))
                self._hierarchy[n.name] = (None, set())
                if n.bases:
                    if len(n.bases) == 1 and isinstance(n.bases[0], ast.Name) and n.bases[0].id in self._exceptions:
                        self.main.append({
                            'type': 'custom_exception',
                            'name': n.name,
                            'base': None if n.bases[0].id == 'Exception' else n.bases[0].id
                        })
                        self._exceptions.add(n.name)
                        self.type_env[n.name] = 'ExceptionType'
                        continue
                    elif len(n.bases) != 1 or not isinstance(n.bases[0], ast.Name) or n.bases[0].id not in self._definition_index:
                        raise translation_error(
                            'only single inheritance from an already defined class is supported',
                            (n.bases[0].lineno, n.bases[0].col_offset),
                            self.lines[n.lineno])

                    base = n.bases[0].id
                    self.type_env.top[n.name] = {l: t for l, t in self.type_env.top[base].items()}
                    self._attr_index[n.name] = {l: [t[0], True] for l, t in self._attr_index[base].items()}
                    self._hierarchy[n.name] = (base, set())
                    self._hierarchy[base][1].add(n.name)
                else:
                    base = None
                    self._attr_index[n.name] = {}
                    self.type_env[n.name] = {}

                self.definitions.append(('class', n.name, base, []))

                self._definition_index[n.name] = {}
                self._attrs[n.name] = []

                for y, m in enumerate(n.body):
                    if isinstance(m, ast.FunctionDef):
                        if not m.args.args or m.args.args[0].arg != 'self':
                            raise translation_error(
                                'only methods with a self arguments are supported(class %s)' % n.name,
                                (m.lineno, m.col_offset + 4 + len(m.name) + 1),
                                self.lines[m.lineno],
                                'example: def method_name(self, x):')

                        self.definitions[-1][3].append(m.name)
                        self._definition_index[n.name][m.name] = m
                        self.type_env.top[n.name][m.name] = ['Function'] + ([None] * (len(m.args.args) - 1)) + [None]
                    else:
                        raise translation_error('only methods are supported in classes',
                            (m.lineno, m.col_offset),
                            self.lines[m.lineno])

            elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if n.targets[0].id[0].islower():
                    self.main.append(n)
                elif any(letter.isalpha() and letter.islower() for letter in n.targets[0].id[1:]):
                    raise type_check_error(
                        'you make pseudo-python very pseudo-confused: please use only snake_case or SCREAMING_SNAKE_CASE for variables',
                        (n.targets[0].lineno, n.targets[0].col_offset),
                        self.lines[n.targets[0].lineno],
                        suggestions='example:\ns = 2 # local\nK = 2 # constant')
                elif self.main:
                    raise translation_error(
                        'constants must be initialized before all other top level code',
                        (n.targets[0].lineno, n.targets[0].col_offset),
                        self.lines[n.targets[0].lineno],
                        right='K = 2\ndef ..',
                        wrong='def ..\nK = 2')

                elif self.type_env.top[n.targets[0].id]:
                    raise translation_error(
                        "you can't override a constant in pseudo-python",
                        (n.targets[0].lineno, n.targets[0].col_offset),
                        self.lines[n.targets[0].lineno])

                else:
                    self.current_constant = n.targets[0].id
                    init = self._translate_node(n.value)
                    self.constants.append({
                        'type': 'constant',
                        'constant': n.targets[0].id,
                        'init': init,
                        'pseudo_type': init['pseudo_type']
                    })
                    self.type_env.top[n.targets[0].id] = init['pseudo_type']
                    self.current_constant = None
            else:
                self.current_constant = None
                self.main.append(n)

    def _translate_node(self, node, in_call=False):
        if isinstance(node, ast.AST):
            if self.current_constant and type(node) not in [ast.Num, ast.Str, ast.List]:
                raise translation_error(
                    'You can initialize constants only with literals',
                    (node[0].lineno, node[0].col_offset),
                    self.lines[node[0].lineno],
                    right='K = [2, 4]',
                    wrong='K = [2, x]')

            fields = {field: getattr(node, field) for field in node._fields}
            fields['location'] = node.lineno, node.col_offset
            if isinstance(node, ast.Attribute):
                fields['in_call'] = in_call
            return getattr(self, '_translate_%s' % type(node).__name__.lower())(**fields)
        elif isinstance(node, list):
            return [self._translate_node(n) for n in node]
        elif isinstance(node, dict):
            return {k: self._translate_node(v) for k, v in node.items()}
        else:
            return node

    def _translate_num(self, n, location):
        type = 'int' if isinstance(n, int) else 'float'
        return {'type': type, 'value': n, 'pseudo_type': type.title()}

    def _translate_name(self, id, ctx, location):
        if id[0].isupper():
            if id not in self.type_env.top.values:
                raise type_check_error(
                    'name %s is not defined' % id,
                    location,
                    self.lines[location[0]])
            id_type = self.type_env.top[id]
            if isinstance(id_type, dict): # class
                id_type = id
            return {'type': 'typename', 'name': id, 'pseudo_type': id_type}
        else:
            id_type = self.type_env[id]
            if id_type is None:
                raise type_check_error(
                    '%s is not defined' % id,
                    location,
                    self.lines[location[0]])

            # if isinstance(id_type, list):
            # id_type = tuple(['Function'] + id_type)
            if id == 'self':
                return {'type': 'this', 'pseudo_type': id_type}
            else:
                return {'type': 'local', 'name': id, 'pseudo_type': id_type}

    def _translate_call(self, func, args, keywords, starargs, kwargs, location):
        self.assert_translatable('call', keywords=([], keywords), starargs=(None, starargs), kwargs=(None, kwargs))
        arg_nodes = self._translate_node(args)

        if isinstance(func, ast.Name) and func.id in BUILTIN_FUNCTIONS:
            return self._translate_builtin_call('global', func.id, arg_nodes, location)

        func_node = self._translate_node(func, in_call=True)

        print('CALL CALL ', func_node, arg_nodes[:1])
        if func_node['type'] == 'attr':
            if func_node['object']['pseudo_type'] == 'library': # math.log
                return self._translate_builtin_call(func_node['object']['name'], func_node['attr'], arg_nodes, location)
            elif self.current_class and self.current_class != 'functions' and isinstance(func.value, ast.Name) and func.value.id == 'self':
                node_type = 'this_method_call'
            elif self.current_class and self.current_class != 'functions' and func_node['object']['pseudo_type'] == 'instance_variable':
                node_type = 'this_method_call'
            elif self._general_type(func_node['object']['pseudo_type']) in PSEUDON_BUILTIN_TYPES: # [2].append
                return self._translate_builtin_method_call(self._general_type(func_node['object']['pseudo_type']), func_node['object'], func_node['attr'], arg_nodes, location)
            else:
                node_type = 'method_call'

            return self._translate_real_method_call(node_type, self._general_type(func_node['object']['pseudo_type']), func_node['object'], func_node['attr'], arg_nodes, location)

        else:
            if (func_node['type'] == 'local' or func_node['type'] == 'this') and func_node['pseudo_type'][-1] is None:
                return self._translate_real_method_call('call', 'functions', None, 'self' if func_node['type'] == 'this' else func_node['name'], arg_nodes, location)
            elif func_node['type'] == 'typename':
                return self._translate_init(func_node['name'], arg_nodes, location)
            elif func_node['type'] == 'library_function':
                return self._translate_builtin_call(func_node['library'], func_node['function'], arg_nodes, location)
            else:
                if self._general_type(func_node['pseudo_type']) != 'Function':
                    raise translation_error(
                        'only Function[..] type is callable',
                        location,
                        self.lines[location[0]],
                        wrong_type=func_node['pseudo_type'])

                self._real_type_check(func_node['pseudo_type'], [arg_node['pseudo_type'] for arg_node in arg_nodes], (func_node['name'] if 'name' in func_node else func_node['type']))
                z = func_node['pseudo_type'][-1]

                return {'type': 'call', 'function': func_node, 'args': arg_nodes, 'pseudo_type': z}

    def _translate_init(self, name, params, location):

        # check or save with the params
        # translate this function and then the pure functions in class
        class_types = self.type_env.top.values.get(name, None)
        if class_types is None:
            raise type_check_error(
                '%s is undefined' % name,
                location,
                self.lines[location[0]])
        init = class_types.get('__init__')
        if init is None and params:
            raise type_check_error(
                'constructor of %s didn\'t expect %d arguments' % (name, len(params)),
                location,
                self.lines[location[0]])

        if init:
            self._definition_index[name]['__init__'] = self._translate_function(self._definition_index[name]['__init__'], name, {'pseudo_type': name}, '__init__', [p['pseudo_type'] for p in params])
            init[-1] = name

        for label, m in self._definition_index[name].items():
            if len(self.type_env.top[name][label]) == 2 and label != '__init__':
                self._definition_index[name][label] = self._translate_function(m, name, {'pseudo_type': name}, label, [])

        return {
            'type': 'new_instance',
            'class': {'type': 'typename', 'name': name},
            'params': params,
            'pseudo_type': name
        }

    def _translate_real_method_call(self, node_type, z, receiver, message, params):
        print(node_type, z, receiver, message)
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

    def _translate_builtin_call(self, namespace, function, args, location):
        if namespace != 'global' and namespace not in self._imports:
            raise type_check_error(
                'module %s not imported: impossible to use %s' % (namespace, function),
                location, self.lines[location[0]],
                suggestions='a tip: pseudo-python currently supports only import, no import as or from..import')
        if not namespace in FUNCTION_API:
            raise translation_error(
                "pseudo-python doesn't support %s" % namespace,
                location, self.lines[location[0]],
                suggestions='pseudo-python supports methods from\n  %s' % ' '.join(
                  k for k in FUNCTION_API if k != 'global'))
        api = FUNCTION_API[namespace].get(function)
        if not api:
            raise translation_error(
                'pseudo-python doesn\'t support %s %s' % (namespace, function),
                location, self.lines[location[0]],
                suggestions='pseudo-python supports those %s functions\n  %s' % (
                    namespace, '\n'.join(
                        '  %s %s -> %s' % (
                            name,
                            ' '.join(serialize_type(arg) for arg in t[:-1]),
                            serialize_type(t[-1]))
                        for name, t in TYPED_API['_%s' % namespace].items()).strip()))



        if not isinstance(api, dict):
            return api.expand(args)
        else:
            for count,(a, b)  in api.items():
                if len(args) == count:
                    return b.expand(args)
            raise translation_error(
                'pseudo-python doesn\'t support %s%s with %d args' % (namespace, function, len(args)),
                location, self.lines[location[0]])

    def _translate_builtin_method_call(self, class_type, base, message, args):
        if class_type not in METHOD_API:
            raise translation_error(
                "pseudo-python doesn't support %s" % class_type,
                location,self.lines[location[0]],
                suggestions='pseudo-python support those builtin classes:\n%s' % ' '.join(
                    PSEUDON_BUILTIN_TYPES[k] for k in METHOD_API.keys()))

        api = METHOD_API.get(class_type, {}).get(message)
        if not api:
            raise translation_error(
                "pseudo-python doesn\'t support %s#%s"  % (serialize_type(class_type), message),
                location, self.lines[location[0]],
                suggestions='pseudo-python supports those %s methods:\n%s' % (
                    PSEUDON_BUILTIN_TYPES[class_type],
                    prepare_table(TYPED_API[class_type]).strip()))

        if isinstance(api, Standard):
            return api.expand([base] + args)
        else:
            for count,(a, b)  in api.items():
                if len(args) == count:
                    return b.expand([base] + args)
            raise translation_error(
                'pseudo-python doesn\'t support %s%s with %d args' % (serialize_type(class_type), message, len(args)),
                location, self.lines[location[0]])

    def _translate_function(self, node, z, receiver, name, args):
        self.assert_translatable('functiondef',
            vararg=(None, node.args.vararg), kwonlyargs=([], node.args.kwonlyargs),
            kw_defaults=([], node.args.kw_defaults), defaults=([], node.args.defaults),
            decorator_list=([], node.decorator_list))

        node_args = node.args.args if z == 'functions' else node.args.args[1:]

        if len(node_args) != len(args):
            raise translation_error('%s expecting %d args' % (node.name, len(node_args)),
                location, self.lines[location[0]])

        # 0-arg functions are inferred only in the beginning

        if args and self.type_env.top[z][name][1]:
            raise type_check_error(
                'please move recursion in a next branch in %s' % node.name,
                location, self.lines[location[0]],
                suggestions='pseudo-python will detect non-recursive branches after the first one in v0.3',
                right='def lala(e):\n    if e == 0:\n        return 0\n   else:\n        return lala(e - 2)',
                wrong='def lala(e):\n    if e > 0:\n        return lala(e - 2)\n..')


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
            # print(args);input()
        self.function_name = outer_function_name
        self.current_class = outer_current_class

        self.type_env = old_type_env


        if z == 'functions':
            node_name = 'function_definition'
        elif name == '__init__':
            node_name = 'constructor'
        else:
            node_name = 'method_definition'

        q = {
            'type':   node_name,
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

    def _translate_expr(self, value, location):
        return self._translate_node(value)

    def _translate_return(self, value, location):
        value_node = self._translate_node(value)
        whiplash = self.type_env.top[self.current_class][self.function_name]
        if whiplash[-1] and whiplash[-1] != value_node['pseudo_type']:
            raise type_check_error(
                "expected %s return type for %s" % (serialize_type(whiplash[-1]), self.function_name), location, self.lines[location[0]], wrong_type=value_node['pseudo_type'])
        elif whiplash[-1] is None:
            whiplash[-1] = value_node['pseudo_type']

        return {
            'type': 'explicit_return' if not self.is_last else 'implicit_return',
            'value': value_node,
            'pseudo_type': value_node['pseudo_type']
        }

    def _translate_binop(self, op, left, right, location):
        op = PSEUDO_OPS[type(op)]
        left_node, right_node = self._translate_node(left), self._translate_node(right)
        binop_type = TYPED_API['operators'][op](left_node['pseudo_type'], right_node['pseudo_type'])[-1]
        if binop_type == 'Float' or binop_type == 'Int':
            return {
                'type': 'binary_op',
                'op': op,
                'left': left_node,
                'right': right_node,
                'pseudo_type': binop_type
            }
        else:
            if left_node['pseudo_type'] == 'String' and op == '%' and right_node['pseudo_type'] == 'String':
                right_node = {
                    'type': 'array',
                    'pseudo_type': ['Array', 'String'],
                    'elements': [right_node]
                }

            return {
                'type': 'standard_method_call',
                'receiver': left_node,
                'message': OPERATOR_API[self._general_type(left_node['pseudo_type'])][op],
                'args': [right_node],
                'pseudo_type': binop_type
            }

    def _translate_compare(self, left, ops, comparators, location):
        op = PSEUDO_OPS[type(ops[0])]
        right_node = self._translate_node(comparators[0])
        left_node = self._translate_node(left)

        self._confirm_comparable(left_node['pseudo_type'], right_node['pseudo_type'], location)

        result = {
            'type': 'binary_op',
            'op':   op,
            'left': left_node,
            'right': right_node,
            'pseudo_type': 'Boolean'
        }
        if len(comparators) == 1:
            return result
        else:
            result = [result]
            for r in comparators[1:]:
                left_node, right_node = right_node, self._translate_node(r)
                self._confirm_comparable(left_node['pseudo_type'], right_node['pseudo_type'], location)
                result = {
                    'type': 'binary_op',
                    'op': 'and',
                    'left': left_node,
                    'right': result,
                    'pseudo_type': 'Boolean'
                }
            return result

    def _confirm_comparable(self, l, r):
        if isinstance(l, list) or isinstance(r, list) or\
           l != r or l not in COMPARABLE_TYPES:
            raise type_check_error(
                '%s not comparable with %s' % (serialize_type(l), serialize_type(r)),
                location, self.lines[location[0]],
                suggestions='comparable types in pseudo-python: %s' % ' '.join(COMPARABLE_TYPES))

    def _translate_attribute(self, value, attr, ctx, location, in_call=False):
        value_node = self._translate_node(value)
        if not isinstance(value_node['pseudo_type'], str) and not in_call:
            raise type_check_error(
                "you can't access attr of %s, only of normal objects or modules" % serialize_type(value_node['pseudo_type']),
                (value.lineno, value.col_offset), self.lines[value.lineno],
                suggestions='[2].s is invalid',
                right='h = H()\nh.y',
                wrong='h = (2, H())\nh.hm')

        if value_node['pseudo_type'] == 'library':
            return {
                'type': 'library_function',
                'library': value_node['name'],
                'function': attr,
                'pseudo_type': 'library'
            }

        else:
            value_general_type = self._general_type(value_node['pseudo_type'])
            attr_type = self._attr_index.get(value_general_type, {}).get(attr)

            if attr_type is None:
                m = METHOD_API.get(value_general_type, {}).get(attr)
                if m:
                    attr_type = m #'builtin_method[%s]' % serialize_type(m)
                else:
                    m = self.type_env.top.values.get(value_general_type, {}).get(attr)
                    if m:
                        attr_type = m #'user_method[%s]' % serialize_type(m)

                if not m:
                    value_type = value_node['pseudo_type']
                    value_general_type = self._general_type(value_type)
                    show_type = serialize_type(TYPED_API.get('_generic_%s' % value_general_type, value_type))
                    raise translation_error(
                        "pseudo-python can\'t infer the type of %s#%s"  % (serialize_type(value_type), attr),
                        location, self.lines[location[0]],
                        suggestions='pseudo-python knows about those %s methods:\n%s' % (
                            show_type,
                            prepare_table(self.type_env.top[value_general_type])))

            else:
                attr_type = attr_type[0]['pseudo_type']

            if value_node['type'] == 'this':
                return {
                    'type': 'instance_variable',
                    'name': attr,
                    'pseudo_type': attr_type
                }
            else:
                return {
                    'type': 'attr',
                    'object': value_node,
                    'attr': attr,
                    'pseudo_type': attr_type
                }

    def _translate_assign(self, targets, value, location):
        if isinstance(value, ast.AST):
            value_node = self._translate_node(value)
        else:
            value_node = value
        if isinstance(targets[0], ast.Name):
            name = targets[0].id
            e = self.type_env[name]
            if e:
                a = self._compatible_types(e, value_node['pseudo_type'], "can't change the type of variable %s in %s " % (name, self.function_name))
            else:
                a = value_node['pseudo_type']
            self.type_env[name] = a
            return {
                'type': 'local_assignment',
                'local': name,
                'value': value_node,
                'pseudo_type': 'Void',
                'value_type': value_node['pseudo_type']
            }
        elif isinstance(targets[0], ast.Attribute):
            z = self._translate_node(targets[0].value)
            if z['pseudo_type'] == 'library':
                raise PseudoPythonTypeCheckError("pseudo-python can't redefine a module function %s" % z['name'] + ':' + targets[0].attr)

            is_public = not isinstance(targets[0].value, ast.Name) or targets[0].value.id != 'self'

            if targets[0].attr in self._attr_index[z['pseudo_type']]:
                a = self._compatible_types(self._attr_index[z['pseudo_type']][targets[0].attr][0]['pseudo_type'],
                                           value_node['pseudo_type'], "can't change attr type of %s" % serialize_type(z['pseudo_type']) + '.' + targets[0].attr)
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

            if z['type'] == 'this':
                return {
                    'type': 'instance_assignment',
                    'name': targets[0].attr,
                    'value': value_node,
                    'pseudo_type': 'Void',
                    'value_type': value_node['pseudo_type']
                }
            elif z['type'] == 'index':
                return {
                    'type': 'index_assignment',
                    'sequence': z['sequence'],
                    'value': value_node,
                    'pseudo_type': 'Void',
                    'value_type': value_node['pseudo_type']
                }
            return {
                'type': 'attr_assignment',
                'attr': {
                    'type': 'attr',
                    'object': z,
                    'attr': targets[0].attr,
                    'pseudo_type': a
                 },
                'value': value_node,
                'pseudo_type': 'Void',
                'value_type': value_node['pseudo_type']
            }

    def _translate_augassign(self, target, op, value, location):
        return self._translate_assign([target], ast.BinOp(target, op, value))

    def _translate_if(self, test, orelse, body, location, base=True):
        test_node = self._testable(self._translate_node(test))
        block = [self._translate_node(child) for child in body]
        if isinstance(orelse, ast.If):
            otherwise = self._translate_if(orelse.test, orelse.orelse, orelse.body, False)
        elif orelse:
            otherwise = {
                'type': 'else_statement',
                'block': [self._translate_node(node) for node in orelse],
                'pseudo_type': 'Void'
            }
        else:
            otherwise = None

        return {
            'type': 'if_statement' if base else 'elseif_statement',
            'test': test_node,
            'block': block,
            'pseudo_type': 'Void',
            'otherwise': otherwise
        }

    def _translate_while(self, body, test, orelse, location):
        self.assert_translatable('while', orelse=([], orelse))
        test_node = self._testable(self._translate_node(test))
        return {
            'type': 'while_statement',
            'test': test_node,
            'block': [self._translate_node(node) for node in body],
            'pseudo_type': 'Void'
        }

    def _testable(self, test_node):
        t = self._general_type(test_node['pseudo_type'])
        if t != TESTABLE_TYPE:
            if t in TYPES_WITH_LENGTH:
                return {
                    'type': 'comparison',
                    'pseudo_type': 'Boolean',
                    'op': '>',
                    'left': {
                        'type': 'standard_method_call',
                        'pseudo_type': 'Int',
                        'receiver': test_node,
                        'message': 'length',
                        'args': []
                    },
                    'right': {'type': 'int', 'pseudo_type': 'Int', 'value': 0}
                }
            elif t in NUMBER_TYPES:
                return {
                    'type': 'comparison',
                    'pseudo_type': 'Boolean',
                    'op': '>',
                    'left': test_node,
                    'right': {'type': 'int', 'pseudo_type': 'Int', 'value': 0}
                }
            elif t == 'RegexpMatch':
                return {
                    'type': 'standard_method_call',
                    'pseudo_type': 'Boolean',
                    'receiver': test_node,
                    'message': 'has_match',
                    'args': []
                }
            else:
                raise PseudoPythonTypeCheckError('pseudo-python expects a bool or RegexpMatch test not %s' % serialize_type(test_node['pseudo_type']))
        else:
            return test_node

    def _translate_list(self, elts, ctx, location):
        if not elts:
            return {'type': 'list', 'elements': [], 'pseudo_type': ['List', None]}

        element_nodes, element_type = self._translate_elements(elts, 'list')

        return {
            'type': 'list',
            'pseudo_type': ['List', element_type],
            'elements': element_nodes
        }

    def _translate_dict(self, keys, values, location):
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

    def _translate_set(self, elts, location):
        element_nodes, element_type = self._translate_elements(elts, 'set')

        return {
            'type': 'set',
            'pseudo_type': ['Set', element_type],
            'elements': element_nodes
        }

    def _translate_tuple(self, elts, ctx, location):
        element_nodes, accidentaly_homogeneous, element_type = self._translate_elements(elts, 'tuple', homogeneous=False)

        return {
            'type': 'tuple',
            'pseudo_type': ['Array', element_type, len(elts)] if accidentaly_homogeneous else ['Tuple'] + element_type,
            'elements': element_nodes
        }

    def _translate_elements(self, elements, kind, homogeneous=True):
        element_nodes = [self._translate_node(elements[0])]
        element_type = element_nodes[0]['pseudo_type']
        if not homogeneous:
            element_types = [element_type]
        accidentaly_homogeneous = True
        for j, element in enumerate(elements[1:]):
            element_nodes.append(self._translate_node(element))
            print(self._hierarchy)
            if homogeneous:
                element_type = self._compatible_types(element_nodes[-1]['pseudo_type'], element_type, "can't use different types in a %s" % kind)
            else:
                element_types.append(element_nodes[-1]['pseudo_type'])
                if accidentaly_homogeneous:
                    element_type = self._compatible_types(element_type, element_nodes[-1]['pseudo_type'], '', silent=True)
                    accidentaly_homogeneous = element_type is not False

        return (element_nodes, element_type) if homogeneous else (element_nodes, accidentaly_homogeneous, element_type if accidentaly_homogeneous else element_types)

    def _translate_subscript(self, value, slice, ctx, location):
        value_node = self._translate_node(value)
        value_general_type = self._general_type(value_node['pseudo_type'])
        if value_general_type not in INDEXABLE_TYPES:
            raise PseudoPythonTypeCheckError('pseudo-python can use [] only on String, List, Dictionary or Tuple : %s' % value_node['pseudo_type'])

        if isinstance(slice, ast.Index):
            z = self._translate_node(slice.value)
            if value_general_type in ['String', 'List', 'Tuple'] and z['pseudo_type'] != 'Int':
                raise PseudoPythonTypeCheckError('a non int index for %s %s' % (value_general_type, z['pseudo_type']))

            if value_general_type == 'Dictionary' and z['pseudo_type'] != value_node['pseudo_type'][1]:
                raise PseudoPythonTypeCheckError('a non %s index for %s %s' % (value_node['pseudo_type'][1], value_general_type, z['pseudo_type']))

            if value_general_type == 'String':
                pseudo_type = 'String'
            elif value_general_type == 'List' or value_general_type == 'Array':
                pseudo_type = value_node['pseudo_type'][1]
            elif value_general_type == 'Tuple':
                if z['type'] != 'int':
                    raise PseudoPythonTypeCheckError('pseudo-python can support only literal int indices of a heterogenous tuple ' +
                                                     'because otherwise the index type is not predictable %s %s ' % (serialize_type(value_node['pseudo_type']), z['type']))

                elif z['value'] > len(value_node['pseudo_type']) - 2:
                    raise PseudoPythonTypeCheckError('%s has only %d elements' % serialize_type(value_node['pseudo_type']), len(value_node['pseudo_type']))

                pseudo_type = value_node['pseudo_type'][z['value'] + 1]

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

    def _translate_str(self, s, location):
        return {'type': 'string', 'value': s.replace('\n', '\\n'), 'pseudo_type': 'String'}

    def _translate_try(self, orelse, finalbody, body, handlers, location):
        self.assert_translatable('try', else_=([], orelse), finally_=([], finalbody))

        return {
            'type': 'try_statement',
            'pseudo_type': 'Void',
            'block': [self._translate_node(node) for node in body],
            'handlers': [self._translate_handler(handler) for handler in handlers]
        }

    def _translate_raise(self, exc, cause, location):
        self.assert_translatable('raise', cause=(None, cause))
        if not isinstance(exc.func, ast.Name) or exc.func.id not in self._exceptions:
            raise PseudoPythonTypeCheckError('pseudo-python can raise only Exception or custom exceptions: %s ' % ast.dump(exc.func))

        return {
            'type': 'throw_statement',
            'pseudo_type': 'Void',
            'exception': exc.func.id,
            'value': self._translate_node(exc.args[0])
        }


    def _translate_with(self, items, body, location):
        if len(items) != 1 or not isinstance(items[0].context_expr, ast.Call) or not isinstance(items[0].context_expr.func, ast.Name) or items[0].context_expr.func.id != 'open':
            print(not isinstance(items[0].context_expr, ast.Call))
            raise PseudoPythonTypeCheckError('pseudo-python supports with only for opening files')
        elif not isinstance(items[0].optional_vars, ast.Name):
           raise PseudoPythonTypeCheckError('pseudo-python needs exactly one name var for with statements' )
        optional_vars = items[0].optional_vars
        items = [items[0].context_expr]

        if len(body) == 1 and len(items[0].args) > 1:
            arg_node = self._translate_node(items[0].args[0])
            if arg_node['pseudo_type'] == 'String' and isinstance(body[0], ast.Assign) and len(body[0].targets) == 1 and\
               isinstance(items[0].args[1], ast.Str) and 'r' in items[0].args[1].s and\
               isinstance(body[0].value, ast.Call) and isinstance(body[0].value.func, ast.Attribute) and isinstance(body[0].value.func.value, ast.Name) and body[0].value.func.value.id == optional_vars.id and body[0].value.func.attr == 'read' and not body[0].value.args:
                return self._translate_assign(targets=body[0].targets, value= {
                    'type': 'standard_call',
                    'namespace': 'io',
                    'function': 'read_file',
                    'args': [arg_node],
                    'pseudo_type': 'String'
                })
            elif arg_node['pseudo_type'] == 'String' and isinstance(body[0], ast.Call) and isinstance(body[0].func, ast.Attribute) and isinstance(body[0].func.value, ast.Name) and body[0].func.value.id == optional_vars.id and body[0].func.attr == 'write':
                z == self._translate_node(body[0].func.args[0], in_call=True)
                return {
                    'type': 'standard_call',
                    'namespace': 'io',
                    'function': 'write_file',
                    'args': [arg_node, z],
                    'pseudo_type': 'Void'
                }

        raise PseudoPythonTypeCheckError('the supported format for with requires exactly one line in body which is [<name> =] <handler>.read/write(..)')


    def _translate_handler(self, handler):
        if not isinstance(handler.type, ast.Name) or handler.type.id not in self._exceptions:
            raise PseudoPythonTypeCheckError('%s' % str(ast.dump(handler.type)))
        h = self.type_env[handler.name]
        if h and h != 'Exception':
            raise PseudoPythonTypeCheckError("can't change the type of exception %s to %s" % (handler.name, serialize_type(h)))
        self.type_env[handler.name] = 'Exception'
        return {
            'type': 'exception_handler',
            'pseudo_type': 'Void',
            'exception': handler.type.id,
            'is_builtin': handler.type.id == 'Exception',
            'instance': handler.name,
            'block': [self._translate_node(z) for z in handler.body]
        }

    def _translate_nameconstant(self, value, location):
        if value == True or value == False:
            return {'type': 'boolean', 'value': value, 'pseudo_type': 'Boolean'}
        elif value is None:
            return {'type': 'null', 'pseudo_type': 'Void'}

    def _translate_listcomp(self, generators, elt, location):
        if isinstance(generators[0].target, ast.Name):
            sketchup, env = self._translate_iter(generators[0].target, generators[0].iter)

        self.type_env = self.type_env.child_env(env)

        old_function_name, self.function_name = self.function_name, 'list comprehension'

        sketchup['type'] = 'standard_iterable_call' + sketchup['type']

        if not generators[0].ifs:
            sketchup['function'] = 'map'
        else:
            test_node = self._testable(self._translate_node(generators[0].ifs[0]))
            sketchup['function'] = 'filter_map'
            sketchup['test'] = [test_node]

        elt_node = self._translate_node(elt)

        self.function_name = old_function_name
        sketchup['block'] = [elt_node]
        sketchup['pseudo_type'] = ['List', elt_node['pseudo_type']]
        return sketchup

    def _translate_iter(self,target, k):
        # fix short names when not 5 am
        if isinstance(k, ast.Call) and isinstance(k.func, ast.Name):
            if k.func.id == 'enumerate':
                if len(k.args) != 1 or not isinstance(target, ast.Tuple) or len(target.elts) != 2:
                    raise PseudoPythonTypeCheckError('enumerate expected one arg not %d and two indices' % len(k.args))
                return self._translate_enumerate(target.elts, k.args[0])
            elif k.func.id == 'range':
                if not isinstance(target, ast.Tuple) or len(target.elts) != 2:
                    raise PseudoPythonTypeCheckError('range expected two indices')

                if not k.args or len(k.args) > 3:
                    raise PseudoPythonTypeCheckError('range expected 1 to 3 args not %d' % len(k.args))
                return self._translate_range(target.elts, k.args)
            elif k.func.id == 'zip':
                if len(k.args) < 2 or not isinstance(target, ast.Tuple) or len(k.args) != len(target.elts):
                    raise PseudoPythonTypeCheckError('zip expected 2 or more args and the same number of indices not %d' % len(k.args))
                return self._translate_zip(target.elts, k.args)

        sequence_node = self._translate_node(k)
        self._confirm_iterable(sequence_node['pseudo_type'])

        if isinstance(target, ast.Tuple):
            raise PseudoPythonNotTranslatableError("pseudo doesn't support tuples yet")

        elif not isinstance(target, ast.Name):
            raise PseudoPythonNotTranslatableError("pseudo doesn't support %s as an iterator" % sequence_node['type'])

        target_pseudo_type = self._element_type(sequence_node['pseudo_type'])
        return {
            'type': '',
            'sequences': {'type': 'for_sequence', 'sequence': sequence_node},
            'iterators': {
                'type': 'for_iterator',
                'iterator': {
                    'type':       'local',
                    'pseudo_type': target_pseudo_type,
                    'name':        target.id
                }
            }
        }, {target.id: target_pseudo_type}


    def _translate_enumerate(self, targets, sequence):
        sequence_node = self._translate_node(sequence)
        self._confirm_iterable(sequence_node['pseudo_type'])

        if not isinstance(targets[0], ast.Name) or not isinstance(targets[1], ast.Name):
            raise PseudoPythonTypeCheckError('expected a name for an index not %s' % type(targets[0]).__name__)

        if self._general_type(sequence_node['pseudo_type']) == 'Dictionary':
            q = 'items'
            k = 'key'
            v = 'value'
        else:
            q = 'index'
            k = 'index'
            v = 'iterator'
        iterator_type = self._element_type(sequence_node['pseudo_type'])
        return {
            'type': '',
            'sequences': {'type': 'for_sequence_with_' + q, 'sequence': sequence_node},
            'iterators': {'type': 'for_iterator_with_' + q,
                k: {
                    'type': 'local',
                    'pseudo_type': 'Int',
                    'name': targets[0].id
                },
                v: {
                    'type': 'local',
                    'pseudo_type': iterator_type,
                    'name': targets[1].id
                }}
            }, {targets[0].id: 'Int', targets[1].id: iterator_type}

    def _translate_range(self, targets, range):
        if len(range) == 1:
            start, end, step = {'type': 'int', 'value': 0, 'pseudo_type': 'Int'}, self._translate_node(range[0]), {'type': 'int', 'value': 1, 'pseudo_type': 'Int'}
        elif len(range) == 2:
            start, end, step = self._translate_node(range[0]), self._translate_node(range[1]), {'type': 'int', 'value': 1, 'pseudo_type': 'Int'}
        else:
            start, end, step = tuple(map(self._translate_node, range[:3]))

        for label, r in [('start', start), ('end', end), ('step', step)]:
            if r['pseudo_type'] != 'Int':
                raise PseudoPythonTypeCheckError('expected int for range %s index' % label)

        if not isinstance(targets[0], ast.Name):
            raise PseudoPythonTypeCheckError('index is not a name %s' % type(targets[0]).__name__)

        return {
            'type': '_range',
            'start': start,
            'end': end,
            'step': step,
            'index': {
                'type': 'local',
                'pseudo_type': 'Int',
                'name': targets[0].id
            }
        }, {targets[0].id: 'Int'}

    def _translate_zip(self, targets, sequences):
        sequence_nodes = []
        sketchup = {'type': '', 'iterators': {'type': 'for_iterator_zip', 'iterators': []}}
        env = {}
        for s, z in zip(sequences, targets):
            sequence_nodes.append(self._translate_node(s))
            self._confirm_iterable(sequence_nodes[-1]['pseudo_type'])
            if not isinstance(z, ast.Name):
                raise PseudoPythonTypeCheckError('index is not a name %s' % type(z).__name__)
            z_type = self._element_type(sequence_nodes[-1]['pseudo_type'])
            sketchup['iterators']['iterators'].append({
                'type': 'local',
                'pseudo_type': z_type,
                'name': z.id
            })
            env[z.id] = z_type

        sketchup['sequences'] = {'type': 'for_sequence_zip', 'sequences': sequence_nodes}
        return sketchup, env


    def _confirm_iterable(self, sequence_type):
        sequence_general_type = self._general_type(sequence_type)
        if sequence_general_type not in ITERABLE_TYPES:
            raise PseudoPythonTypeCheckError('expected an iterable type, not %s' % serialize_type(sequence_type))

    def _element_type(self, sequence_type):
        if isinstance(sequence_type, list):
            if sequence_type[0] == 'Dictionary':
                return sequence_type[2]
            elif sequence_type[0] == 'List':
                return sequence_type[1]
        elif sequence_type == 'String':
            return 'String'

    def assert_translatable(self, node, **pairs):
        for label, (expected, actual) in pairs.items():
            if actual != expected:
                raise PseudoPythonNotTranslatableError("%s in %s is not a part of pseudo-translatable python" % (label if label[-1] != '_' else label[:-1], node))

    def _translate_pure_functions(self):
        for f in self.definitions:
            print(self.type_env.values)
            if f[0] == 'function' and len(self.type_env['functions'][f[1]]) == 2:
                self._definition_index['functions'][f[1]] = self._translate_function(self._definition_index['functions'][f[1]], 'functions', None, f[1], [])

    def _translate_for(self, iter, target, body, orelse, location):
        self.assert_translatable('for', orelse=([], orelse))
        sketchup, env = self._translate_iter(target, iter)
        for label, value in env.items():
            if self.type_env[label]:
                raise PseudoPythonTypeCheckError("pseudo-python forbirds %s shadowing a variable in for" % label)
            self.type_env[label] = value
        self.in_for = True
        sketchup['block'] = [self._translate_node(z) for z in body]
        sketchup['type'] = 'for' + sketchup['type'] + '_statement'
        sketchup['pseudo_type'] = 'Void'
        return sketchup

    def _type_check(self, z, message, types):
        g = self.type_env.top.values.get(z, {}).get(message)
        if not g:
            raise PseudoPythonTypeCheckError("%s is not defined" % message)

        return self._real_type_check(g, types, '%s#%s' % (z, message))

    def _real_type_check(self, g, types, name):
        if len(g) - 2 != len(types):
            raise PseudoPythonTypeCheckError("%s expected %d args" % (message, len(g) - 2))

        for j, (a, b) in enumerate(zip(g[1:-1], types)):
            general = self._compatible_types(b, a, "can't convert %s %dth arg" % (name, j))

        return g

    def _compatible_types(self, from_, to, err, silent=False):
        if isinstance(from_, str):
            if not isinstance(to, str):
                if silent:
                    return False
                else:
                    raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (serialize_type(from_), serialize_type(to)))

            elif from_ == to:
                return to

            elif from_ in self._hierarchy:
                if to in self._hierarchy:
                    if to in self._hierarchy[from_][1]:
                        return from_

                    base = to
                    while base:
                        if from_ in self._hierarchy[base][1]:
                            return base
                        base = self._hierarchy[base][0]

                if silent:
                    return False
                else:
                    raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (serialize_type(from_), serialize_type(to)))

            elif from_ == 'Int' and to == 'Float':
                return 'Float'

            elif silent:
                return False
            else:
                raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (serialize_type(from_), serialize_type(to)))
        else:
            if not isinstance(to, list) or len(from_) != len(to) or from_[0] != to[0]:
                if silent:
                    return False
                else:
                    raise PseudoPythonTypeCheckError(err + ' from %s to %s' % (serialize_type(from_), serialize_type(to)))

            for f, t in zip(from_[1:-1], to[1:-1]):
                self._compatible_types(f, t, err)

            return to


    def _general_type(self, t):
        if isinstance(t, list):
            return t[0]
        else:
            return t


