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
            return {'type': 'standard_call', 'namespace': self.namespace, 'function': self.function, 'args': args, 'pseudon_type': q[-1]}
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
            return {'type': 'standard_method_call', 'receiver': args[0], 'message': self.message, 'args': args[1:], 'pseudon_type': q[-1]}
        else:
            return self.expander(self.type, self.message, args)


def len_expander(type, message, args):
    receiver_type = args[0]['pseudon_type']
    if isinstance(receiver_type, tuple):
        a = receiver_type[0]
    else:
        a = receiver_type
    q = builtin_type_check(a, message, args[0], args[1:])
    return {'type': 'standard_method_call', 'receiver': args[0], 'message': message, 'args': [], 'pseudon_type': q[-1]}
    

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
    }
}

