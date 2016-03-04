def serialize_type(l):
    if isinstance(l, str):
        return l
    elif isinstance(l, list):
        return '%s[%s]' % (l[0], ', '.join(map(serialize_type, l[1:])))
    else:
        return str(l)
