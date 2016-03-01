class PseudoError(Exception):
    pass

class PseudoPythonNotTranslatableError(PseudoError):
    pass

class PseudoPythonTypeCheckError(PseudoError):
    pass
