
from lark import Lark


rules = r"""
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
    lookahead: "(?=" main ")"
    lookbehind: "(?<=" main ")"
    negative_lookahead: "(?!" main ")"
    negative_lookbehind: "(?<!" main ")"
    non_capturing_group: "(?:" main ")"
    capturing_group: "(" main ")"
    named_capturing_group: "(?P<" /\w+/ ">" main ")"
"""


start = "main"

regex_parser = Lark(rules, start=start, parser="lalr")

tree = regex_parser.parse(r"(?P<name>[\da-zA-Z._%+]+)")
print(tree.pretty())
