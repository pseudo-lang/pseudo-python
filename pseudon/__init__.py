import pseudon.parser
import pseudon.emitter

def translate(source):
    return pseudon.emitter.emit(pseudon.parser.parse(source))
