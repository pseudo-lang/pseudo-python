from ast import AST
import yaml


class ASTTranslator:

    def __init__(self, tree):
        self.tree = tree

    def translate(self):
        return yaml.dump({'type': 'program', 'code': []})
