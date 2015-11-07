from ast import *

# TODO: support w,s = 4, 2

TEMPLATES = {
    Num:            '{n}',
    Name:           '{id}',
    Assign:         ('(= {target} {value})', lambda f: {'target': f['targets'][0]}),
    Module:         ('(Cell \n{body})\n', "\n", 1),
    FunctionDef:    ('(def {name} ({args})\n  {body})', lambda f: {'args': f['args'].args}),
    arg:            '{arg}',
    Return:         '(return {value})',
    ClassDef:       ('(class {name} {base} {body})', lambda f: {'base': f['bases'][0] if f['bases'] else ''})
}
