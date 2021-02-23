
from lark import Lark, Transformer
import re


# TODO: Rename this file to analyser and maybe rebuild to builder and put both in a rebuild folder


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
    
    lookahead: "(?=" main? ")"
    lookbehind: "(?<=" main? ")"
    negative_lookahead: "(?!" main? ")"
    negative_lookbehind: "(?<!" main? ")"
    
    // Non-capturing groups are of no meaning
    ?non_capturing_group: "(?:" main? ")"
    capturing_group: "(" main? ")"
    named_capturing_group: "(?P<" /\w+/ ">" main? ")"
    
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
        # Automatically generate a tree structure for this object

        def json_for(value):
            """Creates a json like structure for the given object """
            if isinstance(value, RegexNode):
                if type(value) is EmptyNode:
                    return None
                return value.as_json()
            if type(value) in (list, tuple):
                return [json_for(item) for item in value]
            return str(value)

        def prettify_varname(name):
            return name.replace("_", " ").title()

        def prettify_classname(name):
            return re.sub(r"(?<=[a-z])([A-Z])", r" \1", name)

        # Find all properties / fields of the object
        fields = [field for field in vars(self) if not field.startswith("_")]

        name = prettify_classname(self.__class__.__name__)

        # E.g. for EmptyNode
        if len(fields) == 0:
            return name

        # If there is only one field, then ignore the name of the field
        if len(fields) == 1:
            value = getattr(self, fields[0])
            subtree = json_for(value)

            if type(subtree) is str:
                return name + ": \"" + subtree + "\""

            return {name: subtree}

        subtree = {}

        for field in fields:
            value = getattr(self, field)
            value_json = json_for(value)

            if value_json is None:
                # EmptyNode
                subtree[prettify_varname(field) + ": ---"] = None

            elif type(value_json) is str:
                subtree[prettify_varname(field) + ": \"" + value_json + "\""] = None
            else:
                subtree[prettify_varname(field)] = value_json

        print(subtree)
        return {name: subtree}

    def pretty_print(self):
        tree = self.as_json()
        _print_pretty_tree(tree)


def _ipretty_tree(tree, depth=0):
    indentation = "|   " * depth

    if type(tree) is list:
        for item in tree:
            yield from _ipretty_tree(item, depth)
        return

    if type(tree) is dict:
        for name, subtree in tree.items():
            yield indentation + name
            if (type(subtree) is str and len(subtree) == 0) or subtree is None:
                continue
            yield from _ipretty_tree(subtree, depth + 1)
        return

    yield indentation + str(tree)


def _print_pretty_tree(tree, depth=0):
    indentation = "|   " * depth

    if type(tree) is list:
        for item in tree:
            _print_pretty_tree(item, depth)
        return

    if type(tree) is dict:
        for name, subtree in tree.items():
            print(indentation + name)
            if (type(subtree) is str and len(subtree) == 0) or subtree is None:
                continue
            _print_pretty_tree(subtree, depth+1)
        return

    print(indentation + str(tree))


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
        pattern = "".join(item.regex() for item in self.items)
        if as_atom:
            return "(?:" + pattern + ")"
        return pattern


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


class SingleChar (Atom):
    def __init__(self, char):
        self.char = char

    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False) -> str:
        return self.char


class OneOrMore (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""
        regex = self.pattern.regex(as_atom=True) + "+"

        if as_atom:
            return f"(?:{regex})"

        return regex


class ZeroOrMore (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""
        regex = self.pattern.regex(as_atom=True) + "*"

        if as_atom:
            return f"(?:{regex})"

        return regex


class Optional (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""
        regex = self.pattern.regex(as_atom=True) + "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class CapturingGroup (Group):
    def __init__(self, pattern):
        self.pattern = pattern

    def regex(self, as_atom=False) -> str:
        return f"({self.pattern.regex()})"


class NamedCapturingGroup (Group):
    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def regex(self, as_atom=False) -> str:
        return f"(?P<{self.name}>{self.pattern.regex()})"


class Lookaround (RegexNode):
    def __init__(self, pattern, symbol="="):
        self.pattern = pattern
        self._symbol = symbol

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        return f"(?{self._symbol}{self.pattern})"


class Lookahead (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "=")


class NegativeLookahead (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "!")


class Lookbehind (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "<=")


class NegativeLookbehind (Lookaround):
    def __init__(self, pattern):
        super().__init__(pattern, "<!")


def _get_single_child(items):
    if len(items) == 0:
        return EmptyNode()
    return items[0]


def _one_child(cls, **kwargs):
    return lambda _, items: cls(_get_single_child(items), **kwargs)


class ParseTreeTransformer (Transformer):
    alternation = Alternation
    sequence = Sequence
    single_char = _one_child(SingleChar)
    one_or_more = _one_child(OneOrMore)
    zero_or_more = _one_child(ZeroOrMore)
    optional = _one_child(Optional)

    lookahead = _one_child(Lookahead)
    negative_lookahead = _one_child(NegativeLookahead)
    lookbehind = _one_child(Lookbehind)
    neagtive_lookbehind = _one_child(NegativeLookbehind)

    named_capturing_group = lambda _, items: NamedCapturingGroup(items[0], _get_single_child(items[1:]))
    capturing_group = _one_child(CapturingGroup)


start = "main"

regex_parser = Lark(regex_grammar, start=start, parser="lalr")

tree = regex_parser.parse(r"(?P<Hello>)abc(?=123)")
print(tree.pretty())

tree = ParseTreeTransformer().transform(tree)
tree.pretty_print()
