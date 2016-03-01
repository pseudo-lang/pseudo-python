class SexpNode:
    pass

class ListNode(SexpNode):
    def __init__(self, elements):
        self.elements = elements

    def __repr__(self):
        s = ' 'join([repr(element) for element in self.elements])
        return 'List[{0}]'.format(s)

class StringNode(SexpNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'String[{0}]'.format(self.value)

class IntNode(SexpNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Int[{0}]'.format(self.value)

class IdentifierNode(SexpNode):
    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return 'Identifier[{0}]'.format(self.label)

class SexpParser:
    def parse(self, code):
        sexp = [ListNode([])]
        token = ''
        in_str = False
        for c in code:
            if c == '(' and not in_str:
                sexp.append(ListNode([]))
            elif c == ')' and not in_str:
                if token:
                    sexp[-1].elements.append(self.categorize_token(token))
                    token = ''
                temp = sexp.pop()
                sexp[-1].elements.append(temp)
            elif c in (' ', '\n', '\t') and not in_str:
                sexp[-1].elements.append(self.categorize_token(token))
                token = ''
            elif c == '\"':
                in_str = not in_str
            else:
                token += c
        return sexp[0] 


    def categorize_token(self, token):
        if token[0] == '"':
            return StringNode(token[1:-1])
        elif token.isnumeric():
            return IntNode(token)
        else:
            return IdentifierNode(token)

print(repr(SexpParser.parse('(ls 2)')))

# List[Identifier[ls] Int[2]]

