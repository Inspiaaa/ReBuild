
from lark import Lark, Transformer, Tree, Token
from rebuild.analyser import *


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
    
    one_or_more: atom "+" is_lazy?
    zero_or_more: atom "*" is_lazy?
    optional: atom "?" is_lazy?
    
    ?repeat: repeat_exactly_n
           | repeat_at_least_n
           | repeat_at_most_n
           | repeat_between_n_m
    
    is_lazy: "?"
    
    repeat_exactly_n:   atom "{" /\d+/ "}" is_lazy?
    repeat_at_least_n:  atom "{" /\d+/ ",}" is_lazy?
    repeat_at_most_n:   atom "{," /\d+/ "}" is_lazy?
    repeat_between_n_m: atom "{" /\d+/ "," /\d+/ "}" is_lazy?
    
    ?atom: char_set
         | backreference
         | group
         | lookaround
         | single_char
         | anchor
    
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
               | /[^\n^$]/
    
    UNICODE_CHARACTER: /\\u\d{4}/
    HEX_CHARACTER: /\\x[a-fA-F0-9]{2}/
    PLUS: "+"
    MINUS: "-"
    ASTERISK: "*"
    DIGIT: /\d/
    CARET: "^"
    DOLLAR: "$"
    
    anchor: CARET | DOLLAR
    
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
    
    if_else_group: "(?(" /\w+/ ")" sequence? "|" sequence? ")"
    
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


def _get_single_child(items):
    if len(items) == 0:
        return EmptyNode()
    child = items[0]

    if type(child) is Token:
        return str(child)
    if type(child) is Tree:
        return str(child)
    return child


def _one_child(cls, look_for_lazy=False):
    if look_for_lazy:
        return lambda _, items: cls(_get_single_child(items), is_lazy=_is_lazy(items))
    return lambda _, items: cls(_get_single_child(items))


def _is_lazy(items):
    return any([type(item) is Tree and item.data == "is_lazy" for item in items])


class ParseTreeTransformer (Transformer):
    alternation = Alternation
    sequence = Sequence
    single_char = _one_child(SingleChar)
    one_or_more = _one_child(OneOrMore, look_for_lazy=True)
    zero_or_more = _one_child(ZeroOrMore, look_for_lazy=True)
    optional = _one_child(Optional, look_for_lazy=True)

    lookahead = _one_child(Lookahead)
    negative_lookahead = _one_child(NegativeLookahead)
    lookbehind = _one_child(Lookbehind)
    neagtive_lookbehind = _one_child(NegativeLookbehind)

    named_capturing_group = lambda _, items: NamedCapturingGroup(str(items[0]), _get_single_child(items[1:]))
    capturing_group = _one_child(CapturingGroup)
    non_capturing_group = _one_child(NonCapturingGroup)
    anchor = lambda _, items: AnchorStart() if items[0] == "^" else AnchorEnd()

    def mode(self, items):
        modifiers = str(items[0])
        pattern = _get_single_child(items[1:])
        return ModeGroup(modifiers, pattern)

    def range(self, items):
        from_char, to_char = items[0].split("-")
        return Range(from_char, to_char)

    char_set = CharSet

    def repeat_exactly_n(self, items):
        pattern = _get_single_child(items)
        n = int(items[1])
        is_lazy = _is_lazy(items)
        return RepeatExactlyN(pattern, n, is_lazy)

    def repeat_at_least_n(self, items):
        pattern = _get_single_child(items)
        n = int(items[1])
        is_lazy = _is_lazy(items)
        return RepeatAtLeastN(pattern, n, is_lazy)

    def repeat_at_most_n(self, items):
        pattern = _get_single_child(items)
        n = int(items[1])
        is_lazy = _is_lazy(items)
        return RepeatAtMostN(pattern, n, is_lazy)

    def repeat_between_n_m(self, items):
        pattern = _get_single_child(items)
        n = int(items[1])
        m = int(items[2])
        is_lazy = _is_lazy(items)
        return RepeatBetweenNM(pattern, n, m, is_lazy)

    def if_else_group(self, items):
        name = str(items[0])
        then = _get_single_child(items[1:])
        elsewise = _get_single_child(items[2:])
        return IfElseGroup(name, then, elsewise)


def debug_parse_tree(regex, use_lalr=True):
    if use_lalr:
        parser = regex_parser
    else:
        parser = Lark(regex_grammar, start=start, parser="earley")

    tree = parser.parse(regex)
    return tree


def regex_to_tree(regex) -> "RegexNode":
    if regex == "":
        return EmptyNode()

    # Check if the regex is valid before running it through the parser => Better error messages
    re.compile(regex)
    return regex_parser.parse(regex)


start = "main"

regex_parser = Lark(regex_grammar, start=start, parser="lalr", transformer=ParseTreeTransformer())
