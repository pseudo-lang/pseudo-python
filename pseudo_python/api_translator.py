from pseudo_python.builtin_typed_api import builtin_type_check

class Standard:
    pass

class StandardCall(Standard):
    def __init__(self, namespace, function, expander=None):
        self.namespace = namespace
        self.function  = function
        self.expander = expander

    def expand(self, args):
        if not self.expander:
            q = builtin_type_check(self.namespace, self.function, None, args)
            return {'type': 'standard_call', 'namespace': self.namespace, 'function': self.function, 'args': args, 'pseudo_type': q[-1]}
        else:
            return self.expander(self.namespace, self.function, args)

class StandardMethodCall(Standard):
    def __init__(self, type, message, expander=None):
        self.type = type
        self.message = message
        self.expander = expander

    def expand(self, args):
        if not self.expander:
            q = builtin_type_check(self.type, self.message, args[0], args[1:])
            return {'type': 'standard_method_call', 'receiver': args[0], 'message': self.message, 'args': args[1:], 'pseudo_type': q[-1]}
        else:
            return self.expander(self.type, self.message, args)

class StandardRegex(Standard):
    def expand(self, args):
        if args[0]['type'] == 'String':
            return {'type': 'regex', 'value': args[0]['value'], 'pseudo_type': 'Regexp'}
        else:
            return {'type': 'standard_call', 'namespace': 'regexp', 'function': 'compile', 'args': [args[0]], 'pseudo_type': 'Regexp'}

def len_expander(type, message, args):
    receiver_type = args[0]['pseudo_type']
    if isinstance(receiver_type, tuple):
        a = receiver_type[0]
    else:
        a = receiver_type
    q = builtin_type_check(a, message, args[0], args[1:])
    return {'type': 'standard_method_call', 'receiver': args[0], 'message': message, 'args': [], 'pseudo_type': q[-1]}
    

FUNCTION_API = {
    'global': {
        'input':    StandardCall('io', 'read'),
        'print':    StandardCall('io', 'display'),
        'str':      StandardCall('global', 'to_string'),
        'len':      StandardMethodCall('List', 'length', len_expander)
    },

    'math': {
        'log':      {
            1:      StandardCall('math', 'ln'),
            2:      StandardCall('math', 'log')
        },

        'sin':      StandardCall('math', 'sin'),
        'cos':      StandardCall('math', 'cos')

    },

    're': {
        'match':    StandardMethodCall('Regexp', 'match'),
        'sub':      StandardMethodCall('Regexp', 'replace'),
        'compile':  StandardRegex()
    }
}

METHOD_API = {
    'List': {
        'append':   StandardMethodCall('List', 'push'),
        'pop':      StandardMethodCall('List', 'pop'),
        'insert':   {
            1:      StandardMethodCall('List', 'insert'),
            2:      StandardMethodCall('List', 'insert_at')
        },
        'remove':   StandardMethodCall('List', 'remove')
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

