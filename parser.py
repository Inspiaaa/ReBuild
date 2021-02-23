
from lark import Lark


regex_grammar = r"""
    ?main: or
        | sequence
    
    or: sequence ("|" sequence)* "|" sequence
    
    ?sequence: (one_or_more | zero_or_more | repeat | optional | atom)+
    
    one_or_more: atom "+" "?"?
    zero_or_more: atom "*" "?"?
    repeat: atom "{" /\d+/ (";" /\d+/)? "}" "?"?
    
    optional: atom "?"
    
    ?atom: char_set
        | single_char
        | group
    
    single_char: /\w/
               | /\\./
               | /\\x../
               | /\s/
               | /./
               | PLUS
               | MINUS
    
    PLUS: "+"
    MINUS: "-"
    
    char_set: "[" (range | single_char)+ "]"
    
    // TODO: Add support for regex ranges for hex, e.g. \x01-\x05
    range: /[a-z]-[a-z]/
         | /[A-Z]-[A-Z]/
         | /[0-9]-[0-9]/
    
    ?group: if_else_group
         | lookahead
         | lookbehind
         | negative_lookahead
         | negative_lookbehind
         | non_capturing_group
         | named_capturing_group
         | capturing_group
    
    if_else_group: "(?(" /\w+/ ")" sequence "|" sequence ")"
    
    lookaround: lookahead
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
"""


class RegexNode:
    def optimised(self) -> "RegexNode":
        pass

    def regex(self, as_atom=False) -> str:
        pass

    def __bool__(self):
        return True


class Group (RegexNode):
    pass


class Atom (RegexNode):
    pass


class EmptyNode (RegexNode):
    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        return ""

    def __bool__(self):
        return False


class Sequence (RegexNode):
    def __init__(self, items):
        self.items = items

    def optimised(self) -> "RegexNode":
        non_empty = filter(None, self.items)
        return Sequence([item.optimised() for item in non_empty])

    def regex(self, as_atom=False) -> str:
        return "".join(item.regex() for item in self.items)


class Alternation (RegexNode):
    def __init__(self, options):
        self.options = options

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, is_root=False, as_atom=False) -> str:
        pattern = "|".join(option.regex() for option in self.options)

        if is_root:
            return pattern
        return "(?:{pattern})"


class SingleChar (Atom):
    def __init__(self, char):
        self.char = char

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        return self.char


class OneOrMore (RegexNode):
    def __init__(self, to_repeat):
        self.to_repeat = to_repeat

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        pattern = self.to_repeat.regex(as_astom=True)

        if as_atom:
            return f"(?:{pattern}+)"

        return pattern


start = "main"

regex_parser = Lark(regex_grammar, start=start, parser="lalr")

tree = regex_parser.parse(r"(?P<name>[\da-zA-Z._%+]+)(?:abc)")
print(tree.pretty())
