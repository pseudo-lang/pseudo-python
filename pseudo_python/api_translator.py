from pseudo_python.builtin_typed_api import builtin_type_check
from pseudo_python.errors import PseudoPythonTypeCheckError

class Standard:
    '''
    Standard classes should respond to expand and to return
    valid nodes on expand
    '''
    pass

class StandardCall(Standard):
    '''
    converts to a standard call of the given namespace and function
    '''
    def __init__(self, namespace, function, expander=None):
        self.namespace = namespace
        self.function  = function
        self.expander = expander

    def expand(self, args):
        if not self.expander:
            q = builtin_type_check(self.namespace, self.function, None, args)[-1]
            return {'type': 'standard_call', 'namespace': self.namespace, 'function': self.function, 'args': args, 'pseudo_type': q}
        else:
            return self.expander(self.namespace, self.function, args)

class StandardMethodCall(Standard):
    '''
    converts to a method call of the same class
    '''
    def __init__(self, type, message, default=None, expander=None):
        self.type = type
        self.message = message
        self.default = default
        self.expander = expander

    def expand(self, args):
        if self.default and len(args) - 1 in self.default:
            args += self.default[len(args) - 1]
        if not self.expander:
            q = builtin_type_check(self.type, self.message, args[0], args[1:])[-1]
            return {'type': 'standard_method_call', 'receiver': args[0], 'message': self.message, 'args': args[1:], 'pseudo_type': q}
        else:
            return self.expander(self.type, self.message, args)


class StandardRegex(Standard):
    '''
    converts re.compile(r'literal') to {type: regex} node
    re.compile(variable) to re.compile(variable) standard call
    '''
    def expand(self, args):
        if args[0]['type'] == 'String':
            return {'type': 'regex', 'value': args[0]['value'], 'pseudo_type': 'Regexp'}
        else:
            return {'type': 'standard_call', 'namespace': 'regexp', 'function': 'compile', 'args': [args[0]], 'pseudo_type': 'Regexp'}


class StandardSwapper(Standard):
    def __init__(self, type, message):
        self.type = type
        self.message = message

    def expand(self, args):
        if len(args) < 2:
            raise PseudoPythonTypeCheckError('%s expects more args' % self.message)
        q = builtin_type_check(self.type, self.message, args[1], [args[0]])[-1]
        return {'type': 'standard_method_call', 'receiver': args[1], 'args': [args[0]], 'message': self.message, 'pseudo_type': q}

def to_int_expander(type, message, args):
    return len_expander(type, message, args)

def len_expander(type, message, args):
    receiver_type = args[0]['pseudo_type']
    if isinstance(receiver_type, list):
        a = receiver_type[0]
    else:
        a = receiver_type
    # print(a, message, args[0], args[1:])
    # input(0)
    if message == 'length' and 'special' in args[0]: # len(sys.argv)
        return {'type': 'standard_call', 'namespace': 'system', 'function': 'arg_count', 'args': [], 'pseudo_type': 'Int'}
    else:
        q = builtin_type_check(a, message, args[0], args[1:])
        return {'type': 'standard_method_call', 'receiver': args[0], 'message': message, 'args': [], 'pseudo_type': q[-1]}


FUNCTION_API = {
    'global': {
        'input':    StandardCall('io', 'read'),
        'print':    StandardCall('io', 'display'),
        'str':      StandardCall('global', 'to_string'),
        'len':      StandardMethodCall('List', 'length', expander=len_expander),
        'int':      StandardMethodCall('String', 'to_int', expander=to_int_expander)
    },

    'math': {
        'log':      {
            1:      StandardCall('math', 'ln'),
            2:      StandardCall('math', 'log')
        },

        'sin':      StandardCall('math', 'sin'),
        'cos':      StandardCall('math', 'cos'),
        'tan':      StandardCall('math', 'tan'),
        'pow':      lambda left, right, pseudo_type: Node('binary_op',
                        op='**', left=left, right=right, pseudo_type=pseudo_type)
    },

    're': {
        'match':    StandardMethodCall('Regexp', 'match'),
        'sub':      StandardMethodCall('Regexp', 'replace'),
        'compile':  StandardRegex(),
        'escape':   StandardCall('regexp', 'escape')
    }
}

METHOD_API = {
    'String': {
        'split':      StandardMethodCall('String', 'split'),
        'join':       StandardSwapper('List', 'join'),
        'upper':      StandardMethodCall('String', 'upper'),
        'lower':      StandardMethodCall('String', 'lower'),
        'title':      StandardMethodCall('String', 'title'),
        'center':     StandardMethodCall('String', 'center', default={1: [{'type': 'string', 'value': ' ', 'pseudo_type': 'String'}]}),
        'index':      {
            1:        StandardMethodCall('String', 'find'),
            2:        StandardMethodCall('String', 'find_from')
        }
    },
    'List': {
        'append':   StandardMethodCall('List', 'push'),
        'pop':      StandardMethodCall('List', 'pop'),
        'insert':   {
            1:      StandardMethodCall('List', 'insert'),
            2:      StandardMethodCall('List', 'insert_at')
        },
        'remove':   StandardMethodCall('List', 'remove'),
        'extend':   StandardMethodCall('List', 'push_many'),
        'map':      StandardMethodCall('List', 'map'),
        'filter':   StandardMethodCall('List', 'filter')
    },

    'Dictionary': {
        'keys':     StandardMethodCall('Dictionary', 'keys'),
        'values':   StandardMethodCall('Dictionary', 'values'),
        '[]':       StandardMethodCall('Dictionary', 'getitem'),
        '[]=':      StandardMethodCall('Dictionary', 'setitem')
    },

    'Array': {
    },

    'Tuple': {
    },

    'Set': {
        '|':       StandardMethodCall('Set', 'union')
    },

    'Regexp': {
        'match':   StandardMethodCall('Regexp', 'match')
    },

    'RegexpMatch': {
        'group':    StandardMethodCall('RegexpMatch', 'group')
    }
}

OPERATOR_API = {
    'List':  {
        '+':    'concat',
        '*':    'repeat'
    },
    'Set':  {
        '|':    'union',
        '&':    'intersection',
        '^':    'symmetric_diff',
        '-':    'diff'
    },
    'String': {
        '+':    'concat',
        '*':    'repeat',
        '%':    'c_format'
    }
}

