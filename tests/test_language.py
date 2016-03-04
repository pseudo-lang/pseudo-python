class TestLanguage(type):
    def __new__(cls, name, bases, namespace, **kwargs):

        def generate_test(name, cases):
            def test(self):
                for input, exp in cases.items():
                    if isinstance(exp, list):
                        exp = {'type': 'module', 'dependencies': [], 'constants': [], 'definitions': [], 'main': exp}
                    else:
                        exp = {'type': 'module', 'dependencies': [], 'constants': exp.get('constants', []), 'definitions': exp.get('definitions', []), 'main': exp['main']}

                    self.assertEqual(self.translate(input), exp)
            return test

        for name, cases in namespace['suite'].items():
            test_name = 'test_%s' % name
            namespace[test_name] = generate_test(name, cases)

        return super().__new__(cls, name, bases, namespace)
