import pseudon_python.parser
import pseudon_python.ast_translator


def translate(source):
    return pseudon_python.ast_translator.ASTTranslator(pseudon_python.parser.parse(source)).translate()
