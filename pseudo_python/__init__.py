import pseudo_python.parser
import pseudo_python.ast_translator
import yaml

def translate(source):
    return pseudo_python.ast_translator.ASTTranslator(pseudo_python.parser.parse(source), source).translate()

def translate_to_yaml(source):
    yaml.Dumper.ignore_aliases = lambda *args : True
    return yaml.dump(translate(source))
