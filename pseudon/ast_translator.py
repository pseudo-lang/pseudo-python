import ast
import yaml


class ASTTranslator:

    def __init__(self, tree):
        self.tree = tree

    def translate(self):
        return yaml.dump(self._translate_node(self.tree))

    def _translate_node(self, node):
        if isinstance(node, ast.AST):
            return getattr('_translate_%s' % type(node).__name__)(**node.__dict__)
        elif isinstance(node, list):
            return [self._translate_node(n) for n in node]
        elif isinstance(node, dict):
            return {k: self._translate_node(v) for k, v in node.items()}
        else:
            return node

    def _translate_module(self, body):
        return {'type': 'program', 'code': self._translate_node(body)}

    def _translate_int(self, n):
        return {'type': 'int', 'value': n}
