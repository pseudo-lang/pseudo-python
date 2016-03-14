# int Int
# float Float
# boolean Boolean
# str String
# [2] List<Int>
# {2: 2.0} Dict<Int, Float>
# [] List
# {} Dict

from pseudo_python.errors import PseudoPythonTypeCheckError
from pseudo_python.helpers import serialize_type

V = '_' # we don't really typecheck or care for a lot of the arg types, so just use this
_ = ()

# we use lists instead of tuples, because it's easier this way
# for different methods in the same type env to reference and update the same signature
# that helps us with inherited methods: each one updates the type signature for the whole hierarchy


def builtin_type_check(namespace, function, receiver, args):
    fs = TYPED_API[namespace]
    if fs == 'library':
        fs = TYPED_API['_%s' % namespace]
    # print(namespace, function, receiver, args, TYPED_API[namespace])
    # input(0)
    if function not in fs:
        raise  PseudoPythonTypeCheckError('wrong usage of %s' % str(function))
    x = fs[function]
    
    a = namespace + '#' + function if receiver else namespace + ':' + function
    if namespace == 'List' or namespace == 'Set' or namespace == 'Array':
        generics = {'@t': receiver['pseudo_type'][1]}
    elif namespace == 'Dictionary':
        generics = {'@k': receiver['pseudo_type'][1], '@v': receiver['pseudo_type'][2]}
    else:
        generics = {}
    
    s = []
    if x[0][0] == '*':
        e = x[0][1:]
        for arg in args:
            s.append(simplify(e, generics))
            arg_check(s[-1], arg, a)
    else:
        if len(x) - 1 != len(args):   
            raise PseudoPythonTypeCheckError("%s expects %d args not %d" % (a, len(x) - 1, args))
        for e, arg in zip(x[:-1], args):
            s.append(simplify(e, generics))
            arg_check(s[-1], arg, a)
    s.append(simplify(x[-1], generics))
    return s

def arg_check(expected_type, args, a):
    if expected_type != args['pseudo_type'] and expected_type != 'Any' and not(expected_type == 'Number' and (args['pseudo_type'] == 'Int' or args['pseudo_type'] == 'Float')):
        raise PseudoPythonTypeCheckError('%s expected %s not %s' % (a, serialize_type(expected_type), serialize_type(args['pseudo_type'])))

def simplify(kind, generics):
    if not generics:
        return kind
    elif isinstance(kind, str):
        if kind[0] == '@' and kind in generics:
            return generics[kind]
        else:
            return kind
    else:
        return [simplify(child, generics) for child in kind]

# refactoring here in future

def add(l, r):
    if l == 'Float' and r in ['Float', 'Int']  or r == 'Float' and l in ['Float', 'Int']:
        return [l, r, 'Float']
    elif l == 'Int' and r == 'Int':
        return [l, r, 'Int']
    elif l == 'String' and r == 'String':
        return [l, r, 'String']
    elif isinstance(l, list) and l[0] == 'List' and l == r:
        return [l, r, l]
    else:
        raise PseudoPythonTypeCheckError("wrong types for +: %s and %s" % (serialize_type(l), serialize_type(r)))

def sub(l, r):
    if l == 'Float' and r in ['Float', 'Int'] or r == 'Float' and l in ['Float', 'Int']:
        return [l, r, 'Float']
    elif l == 'Int' and r == 'Int':
        return [l, r, 'Int']
    else:
        raise PseudoPythonTypeCheckError("wrong types for -: %s and %s" % (serialize_type(l), serialize_type(r)))

def mul(l, r):
    if l == 'Float' and r in ['Float', 'Int'] or r == 'Float' and l in ['Float', 'Int']:
        return [l, r, 'Float']
    elif l == 'Int' and r == 'Int':
        return [l, r, 'Int']
    elif l == 'Int' and (isinstance(r, list) and r[0] == 'List' or r == 'String'): 
        return [l, r, r]
    elif r == 'Int' and (isinstance(l, list) and l[0] == 'List' or l == 'String'):
        return [l, r, l]
    else:
        raise PseudoPythonTypeCheckError("wrong types for *: %s and %s" % (serialize_type(l), serialize_type(r)))

def div(l, r):
    if l == 'Float' and r in ['Float', 'Int'] or r == 'Float' and l in ['Float', 'Int']:
        return [l, r, 'Float']
    elif l == 'Int' and r == 'Int':
        return [l, r, 'Int']
    else:
        raise PseudoPythonTypeCheckError("wrong types for /: %s and %s" % (serialize_type(l), serialize_type(r)))

def pow_(l, r):
    if l == 'Float' and r in ['Float', 'Int'] or r == 'Float' and l in ['Float', 'Int']:
        return [l, r, 'Float']
    elif l == 'Int' and r == 'Int':
        return [l, r, 'Int']
    else:
        raise PseudoPythonTypeCheckError("wrong types for **: %s and %s" % (serialize_type(l), serialize_type(r)))

def mod(l, r):
    if l == 'Int' and r == 'Int':
        return [l, r, 'Int']
    elif l == 'String' and (r == 'String' or r == ['Array', 'String']):
        return [l, ['Array', 'String'], 'String']
    else:
        raise PseudoPythonTypeCheckError("wrong types for %: %s and %s" % (serialize_type(l), serialize_type(r)))

def and_(l, r):
    if l == 'Boolean' and r == 'Boolean':
        return 'Boolean'
    else:
        raise PseudoPythonTypeCheckError("wrong types for and: %s and %s" % (serialize_type(l), serialize_type(r)))

def or_(l, r):
    if l == 'Boolean' and r == 'Boolean':
        return 'Boolean'
    else:
        raise PseudoPythonTypeCheckError("wrong types for or: %s and %s" % (serialize_type(l), serialize_type(r)))        

def binary_and(l, r):
    if l == r == 'Int' or l == r == 'Set':
        return l
    else:
        raise PseudoPythonTypeCheckError("wrong types for &: %s and %s" % (serialize_type(l), serialize_type(r)))

def binary_or(l, r):
    if l == r == 'Int' or l == r == 'Set':
        return l
    else:
        raise PseudoPythonTypeCheckError("wrong types for |: %s and %s" % (serialize_type(l), serialize_type(r)))

def xor_(l, r):
    if l == r == 'Int' or l == r == 'Set':
        return l
    else:
        raise PseudoPythonTypeCheckError("wrong types for ^: %s and %s" % (serialize_type(l), serialize_type(r)))


# for template types as list, dict @t is the type of list arg and @k, @v of dict args
TYPED_API = {
    # methods
    'global': {
        'exit':  ['Int', 'Void'],
        'to_string': ['Any', 'String']
    },

    'io': {
        'display':     ['*Any', 'Void'],
        'read':        ['String'],
        'read_file':   ['String', 'String'],
        'write_file':  ['String', 'String', 'Void']
    },

    'system': {
        'args':         [['List', 'String']]
    },

    'regexp': {
        'compile':      ['String', 'Regexp'],
        'escape':       ['String', 'String']
    },

    'math': {
        'tan':          ['Number', 'Float'],
        'sin':          ['Number', 'Float'],
        'cos':          ['Number', 'Float'],
        'ln':           ['Number', 'Float'],
        'log':          ['Number', 'Number', 'Float']
    },

    'operators': {
        '+': add,
        '-': sub,
        '*': mul,
        '/': div,
        '**': pow_,
        '%': mod,

        '&':   binary_and,
        '|':   binary_or,
        '^':   xor_
    },
    
    'List': {
        'push':       ['@t', 'Void'],
        'pop':        ['@t'],
        'insert':     ['@t', 'Void'],
        'insert_at':  ['@t', 'Int', 'Void'],
        'concat':     [['List', '@t'], ['List', '@t']],
        'repeat':     ['Int', ['List', '@t']],
        'push_many':  [['List', '@t'], 'Void'],
        'remove':     ['@t', 'Void'],
        'length':     ['Int'],
        'join':       [['List', 'String'], 'String'],
        'map':        [['Function', '@t', '@y'], ['List', '@y']],
        'filter':     [['Function', '@t', 'Boolean'], ['List', '@t']]
    },

    'Dictionary': {
        'keys':       ['List', '@k'],
        'values':     ['List', '@v'],
        'length':     ['Int']
    },
    'String': {
        'find':       ['String', 'Int'],
        'to_int':     ['Int'],
        'split':      ['String', ['List', 'String']],
        'c_format':   [['Array', 'String'], 'String'],
        'upper':      ['String'],
        'lower':      ['String'],
        'title':      ['String'],
        'center':     ['Int', 'String', 'String'],
        'find_from':  ['String', 'Int', 'Int'],
        'length':     ['Int'],
    },
    'Set': {
        '|':           [['Set', '@t'], ['Set', '@t']],
        'add':         ['@t', 'Void'],
        'remove':      ['@t', 'Void'],
        '&':           [['Set', '@t'], ['Set', '@t']],
        '^':           [['Set', '@t'], ['Set', '@t']],
        '-':           [['Set', '@t'], ['Set', '@t']]
    },
    'Int': {'to_int': ['Int'], 'to_float': ['Float']},
    'Float': {'to_int': ['Int'], 'to_float': ['Float']},
    'Array': {
        'length':      ['Int'],
        'index':       ['@t', 'Int'],
        'count':       ['@t', 'Int']
    },

    'Tuple': {
        'length':       ['Int']
    },

    'Regexp': {
        'match':        ['String', 'RegexpMatch'],
        'groups':       ['String', ['String']]
    },

    'RegexpMatch': {
        'group':        ['Int', 'String']
    },

    '_generic_List':    ['List', '@t'],
    '_generic_Set':     ['Set', '@t'],
    '_generic_Array':   ['Array', '@t'],
    '_generic_Tuple':   ['Tuple', '@t'],
    '_generic_Dictionary': ['Dictionary', '@k', '@v'],
    # 'List#pop':        [_, '@t'],
    # 'List#insert':     [_, 'Null'],
    # 'List#remove':     [_, 'Null'],
    # 'List#remove_at':  [_, 'Null'],
    # 'List#length':     [_, 'Int'],
    # 'List#concat_one': [_, 'List<@t>'],
    # 'List#concat':     [_, 'List<@t>'],
    # 'List#[]':         [_, '@t'],
    # 'List#[]=':        [_, 'Null'],
    # 'List#slice':      [_, 'List<@t>'],

    # 'Dict#keys':       [_, 'List<@k>'],
    # 'Dict#values':     [_, 'List<@v>'],
}

# useful for error messages

ORIGINAL_METHODS = {
    'List': {
        'push':       'append(element)',
        'pop':        'pop',
        'insert':     'insert(element)',
        'insert_at':  'insert(element, index)',
        'concat':     '+',
        'repeat':     '*',
        'push_many':  'extend(other)',
        'remove':     'remove',
        'length':     'len',
        'map':        'list comprehension / map',
        'filter':     'list comprehension / filter'
    },

    'Dictionary': {
        'keys':       'keys',
        'values':     'values',
        'length':     'len'
    },

    'Int': {
        'to_int':     'int',
        'to_float':   'float'
    },
    'Float': {
        'to_int':     'int',
        'to_float':   'float'
    },
    'String': {
        'find':       'index(substring)',
        'join':       'join(elements)',
        'split':      'split(delimiter)',
        'c_format':   '%',
        'format':     'format(*elements)',
        'upper':      'upper',
        'lower':      'lower',
        'title':      'title',
        'center':     'center',
        'find_from':  'index(substring, index)',
        'to_int':     'int'
    },
    'Set': {
        '|':           '|',
        'add':         'add(element)',
        'remove':      'remove(element)',
        '&':           '&',
        '^':           '^',
        '-':           '-'
    },

    'Array': {
        'length':      'len',
        'find':        'find(element)',
        'count':       'count(element)'
    },

    'Tuple': {
        'length':       'len'
    },

    'Regexp': {
        'match':        'match(value)',
        'groups':       'find_all(value)'
    },

    'RegexpMatch': {
        'group':        'group(z)'
    }
}