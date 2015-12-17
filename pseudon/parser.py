import ast


def parse(source):
    x = ast.parse(source)
    return x
