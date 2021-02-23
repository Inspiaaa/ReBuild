
from lark import Lark, Transformer


regex_grammar = r"""
    ?main: alternation
         | sequence
    
    alternation: alternation_matches_empty? sequence ("|" sequence)* "|" sequence
    alternation_matches_empty: "|"
    
    ?sequence: (quantified | atom)+
    
    ?quantified: one_or_more
               | zero_or_more
               | repeat
               | optional
    
    one_or_more: atom "+" "?"?
    zero_or_more: atom "*" "?"?
    repeat: atom "{" /\d+/ "}" "?"?
          | atom "{" /\d+/? ";" /\d+/ "}"
    
    optional: atom "?"
    
    ?atom: char_set
         | backreference
         | group
         | lookaround
         | single_char
    
    // TODO: Split this into two rules:
    // one for normal characters
    // and one for char sets
    single_char: /\w/
               | /\\[^\d]/
               | /\s/
               | HEX_CHARACTER
               | UNICODE_CHARACTER
               | PLUS
               | MINUS
               | ASTERISK
               | /[^\n]/
    
    UNICODE_CHARACTER: /\\u\d{4}/
    HEX_CHARACTER: /\\x[a-fA-F0-9]{2}/
    PLUS: "+"
    MINUS: "-"
    ASTERISK: "*"
    DIGIT: /\d/
    
    char_set: "[" (range | single_char)+ "]"

    range: /[a-z]-[a-z]/
         | /[A-Z]-[A-Z]/
         | /[0-9]-[0-9]/
         | /\\u\d{4}-\\u\d{4}/
         | /\\x[a-fA-F0-9]{2}-\\x[a-fA-F0-9]{2}/
    
    ?group: if_else_group
          | non_capturing_group
          | named_capturing_group
          | mode
          | capturing_group
    
    if_else_group: "(?(" /\w+/ ")" sequence "|" sequence ")"
    
    ?lookaround: lookahead
               | lookbehind
               | negative_lookahead
               | negative_lookbehind
    
    lookahead: "(?=" main ")"
    lookbehind: "(?<=" main ")"
    negative_lookahead: "(?!" main ")"
    negative_lookbehind: "(?<!" main ")"
    
    // Non-capturing groups are of no meaning
    ?non_capturing_group: "(?:" main ")"
    capturing_group: "(" main ")"
    named_capturing_group: "(?P<" /\w+/ ">" main ")"
    
    mode: "(?" /[aiLmsux]+/ ":" main ")"
    
    ?backreference: named_backreference
                  | numbered_backreference
    
    numbered_backreference: "\\" /\d+/
    named_backreference: "(P=" /\w+/ ")"
"""


class RegexNode:
    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        return ""

    def __bool__(self):
        return True

    def as_json(self):
        return {}

    def pretty_print(self):
        tree = self.as_json()
        _print_pretty_tree(tree)


def _print_pretty_tree(tree, depth=0):
    indentation = "|   " * depth

    if type(tree) is list:
        for item in tree:
            _print_pretty_tree(item, depth)
        return

    if type(tree) is dict:
        for name, subtree in tree.items():
            print(indentation + name)
            _print_pretty_tree(subtree, depth+1)
        return

    print(indentation + tree)


class Group (RegexNode):
    pass


class Atom (RegexNode):
    pass


class EmptyNode (RegexNode):
    def as_json(self):
        return "Empty"

    def __bool__(self):
        return False


class Sequence (RegexNode):
    def __init__(self, items):
        self.items = items

    def optimised(self) -> "RegexNode":
        optimised = [item.optimised() for item in self.items]
        non_empty = list(filter(None, optimised))

        if len(non_empty) == 0:
            return EmptyNode()

        if len(non_empty) == 1:
            return non_empty[0]

        return Sequence(non_empty)

    def regex(self, as_atom=False) -> str:
        return "".join(item.regex() for item in self.items)

    def as_json(self):
        return {"Sequence": [item.as_json() for item in self.items]}


class Alternation (RegexNode):
    def __init__(self, options):
        self.options = options

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, is_root=False, as_atom=False) -> str:
        pattern = "|".join(option.regex() for option in self.options)

        if is_root:
            return pattern
        return f"(?:{pattern})"

    def as_json(self):
        return {"Alternation": [option.as_json() for option in self.options]}


class SingleChar (Atom):
    def __init__(self, char):
        self.char = char

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        return self.char

    def as_json(self):
        return "Single Char: " + self.char


class OneOrMore (RegexNode):
    def __init__(self, to_repeat):
        self.to_repeat = to_repeat

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        pattern = self.to_repeat.regex(as_atom=True) + "+"

        if as_atom:
            return f"(?:{pattern})"

        return pattern

    def as_json(self):
        return {"One or more": self.to_repeat.as_json()}


class ParseTreeTransformer (Transformer):
    alternation = Alternation
    sequence = Sequence
    single_char = lambda self, items: SingleChar(items[0])
    one_or_more = lambda self, items: OneOrMore(items[0])


start = "main"

regex_parser = Lark(regex_grammar, start=start, parser="lalr")

tree = regex_parser.parse(r"\1(P=23)[]\u1234abc+\x20-\x59 \u1234-\u12345]")
print(tree.pretty())
