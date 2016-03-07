import test_language
import unittest
import textwrap
from pseudo_python import translate

class TestPython(unittest.TestCase, metaclass=test_language.TestLanguage):
    # several shortcuts for common nodes
    def local(name, pseudo_type):
        return {'type': 'local', 'pseudo_type': pseudo_type, 'name': name}

    def literal(value):
        pseudo_node = {int: 'int', float: 'float', bool: 'boolean', str: 'string'}[type(value)]
        return {'type': pseudo_node, 'pseudo_type': pseudo_node.title(), 'value': value}

    def call(function, args, pseudo_type):
        return {'type': 'call', 'function': function, 'args': args, 'pseudo_type': pseudo_type}

    def t(s):
        return textwrap.dedent(s)

    def translate(self, source):
        return translate(source)

    maxDiff = None
    # why a dict? well all our test inputs for a node type
    # are unique strings, and it makes for a good dsl

    suite = dict(
        # int     = {
        #     '42':       [literal(42)]
        # },

        # float   = {
        #     '42.42':    [literal(42.42)]
        # },

        # bool    = {
        #     'True':     [literal(True)],
        #     'False':    [literal(False)]
        # },

        # str     = {
        #     '""':       [literal('')],
        #     "'lalaя'":  [literal('lalaя')]
        # },

        # none    = {
        #     'None':     [{'type': 'null', 'pseudo_type': 'Void'}]
        # },

        # assignments = {
        #     'l = 2': [{
        #         'type': 'assignment', 
        #         'target': local('l', 'Int'), 
        #         'value': literal(2),
        #         'pseudo_type': 'Void'
        #     }],
        #     # 'self.a = 4': {
        #     #     'type': 'assignment',
        #     #     'target': {'type': 'instance_variable', 'name': 'a', 'pseudo_type': 'Int'},
        #     #     'value': literal(4),
        #     #     'pseudo_type': 'Void'
        #     # },
        #     t('''
        #     l = [42]
        #     l[0] = 42
        #     '''): [{
        #         'type': 'assignment',
        #         'target': local('l', ['List', 'Int']),
        #         'value': {'type': 'list', 'elements': [literal(42)], 'pseudo_type': ['List', 'Int']},
        #         'pseudo_type': 'Void'
        #     }, {
        #         'type': 'assignment',
        #         'target': {'type': 'index', 'sequence': local('l', ['List', 'Int']), 'index': literal(0), 'pseudo_type': 'Int'},
        #         'value': literal(42),
        #         'pseudo_type': 'Void'
        #     }]
        # },
        # extensive tests in v0.3/v0.4 when ast spec stabilizes
        function = {
            t('''
            def x(a):
                return 42

            x(0)
            '''): {
                'definitions': [{
                    'type': 'function_definition',
                    'name': 'x',
                    'params': ['a'],
                    'block': [{
                        'type': 'implicit_return',
                        'value': literal(42),
                        'pseudo_type': 'Int'
                    }],
                    'pseudo_type': ['Function', 'Int', 'Int'],
                    'return_type': 'Int'
                }], 
                'main': [
                    call(local('x', ['Function', 'Int', 'Int']), [literal(0)], 'Int')
                ]
            }
        }
    )            


