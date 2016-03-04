from pseudo_python.helpers import serialize_type

class PseudoError(Exception):
    def __init__(self, message, suggestions=None, right=None, wrong=None):
        super(PseudoError, self).__init__(message)

        self.suggestions = suggestions
        self.right = right
        self.wrong = wrong

class PseudoPythonNotTranslatableError(PseudoError):
    pass

class PseudoPythonTypeCheckError(PseudoError):
    pass

def cant_infer_error(name):
    return PseudoPythonTypeCheckError("pseudo-python can't infer the types for %s" % name)

def beautiful_error(exception):
    def f(function):
        def decorated(data, location=None, code=None, used_type=None, **options):
            return exception('%s%s%s:\n%s\n%s^' % (
                ('wrong type %s\n' % serialize_type(used_type) if used_type else ''),
                data,
                (' on line %d column %d' % location) if location else '',
                code or '',
                (tab_aware(location[1], code) if location else '')),
                **options)
        return decorated
    return f

@beautiful_error(PseudoPythonTypeCheckError)
def type_check_error(data, location=None, code=None, used_type=None, **options):
    pass

@beautiful_error(PseudoPythonNotTranslatableError)
def translation_error(data, location=None, code=None, used_type=None, **options):
    pass

def tab_aware(location, code):
    '''
    if tabs in beginning of code, add tabs for them, otherwise spaces
    '''
    return ''.join(' ' if c != '\t' else '\t' for c in code[:location])
