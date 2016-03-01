# int Int
# float Float
# boolean Boolean
# str String
# [2] List<Int>
# {2: 2.0} Dict<Int, Float>
# [] List
# {} Dict

from pseudon_python.errors import PseudonPythonTypeCheckError

V = '_' # we don't really typecheck or care for a lot of the arg types, so just use this
_ = ()

def serialize_type(l):
    if isinstance(l, str):
        return l
    else:
        return '%s[%s]' % (l[0], '\n'.join(map(serialize_type, l[1])))

def add(l, r):
    if l == 'Float' or r == 'Float':
        return (l, r, 'Float')
    elif l == 'Int' and r == 'Int':
        return (l, r, 'Int')
    elif l == 'String' and r == 'String':
        return (l, r, 'String')
    elif isinstance(l, tuple) and l[0] == 'List' and l == r:
        return (l, r, l)
    else:
        raise PseudonPythonTypeCheckError("wrong types for +: %s and %s" % (serialize_type(l), serialize_type(r)))


# for template types as list, dict @t is the type of list arg and @k, @v of dict args
TYPED_API = {
    # methods
    'global': {
        'exit':  ('Int', 'Void'),
        'wat':   ('Int',),
        'to_string': ('Any', 'String')
    },

    'io': {
        'display': ('*Any', 'Void')
    },

    '+': add,
    
    'List': {
        'push':   ('@t', 'Void'),
        'pop':    ('@t',),
    },
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

    # 'Enumerable#map':    [('Function<@t, @a>',), 'List<@a>'],
    # 'Enumerable#filter': [('Function<@t, Boolean>',), 'List<@t>'],
    # 'Enumerable#reduce': [('Function<@u, @t, @u>', '@u'), '@u'],
    # 'Enumerable#any':    [('Function<@t, Boolean>',), 'Boolean'],
    
    # 'Dict#keys':       [_, 'List<@k>'],
    # 'Dict#values':     [_, 'List<@v>'],
}
