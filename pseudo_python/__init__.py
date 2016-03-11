import pseudo_python.parser
import pseudo_python.ast_translator

def translate(source):
	return pseudo_python.ast_translator.ASTTranslator(pseudo_python.parser.parse(source), source).translate()
