class PseudonError(Exception):
    pass

class PseudonPythonNotTranslatableError(PseudonError):
    pass

class PseudonPythonTypeCheckError(PseudonError):
    pass
