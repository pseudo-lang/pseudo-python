import pseudon.parser
import pseudon.ast_translator


def translate(source):
    return pseudon.ast_translator.ASTTranslator(pseudon.parser.parse(source)).translate()
