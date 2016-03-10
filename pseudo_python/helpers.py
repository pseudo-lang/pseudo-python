def serialize_type(l):
    if isinstance(l, str):
        return l
    elif isinstance(l, list):
        return '%s[%s]' % (l[0], ', '.join(map(serialize_type, l[1:])))
    else:
        return str(l)

def safe_serialize_type(l):
    '''serialize only with letters, numbers and _'''

    if isinstance(l, str):
        return l
    elif isinstance(l, list):
        return '%s_%s_' % (l[0], ''.join(map(safe_serialize_type, l[1:])))
    else:
        return str(l)

def prepare_table(types, original_methods=None):
    names, args, returns = [], [], []
    max_name, max_arg, max_return = 0, 0, 0
    for name, t in types.items():
        if original_methods:
            if name in original_methods:
                name = original_methods[name]
            else:
                continue
        names.append(name)
        args.append(' '.join(serialize_type(arg) for arg in t[:-1]))
        returns.append(serialize_type(t[-1]))
        if len(name) > max_name:
            max_name = len(name)
        if len(args[-1]) > max_arg:
            max_arg = len(args[-1])
        if len(returns[-1]) > max_return:
            max_return = len(returns[-1])
    return '\n'.join(
        '  %s %s -> %s' % (name.ljust(max_name), arg_types.ljust(max_arg), return_type.ljust(max_return)) for name, arg_types, return_type in zip(names, args, returns))
