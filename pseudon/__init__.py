import pseudon.parser
import pseudon.ast_translator


def translate(source):
    return pseudon.ast_translator(pseudon.parser.parse(source)).translate()
