
import re
import rebuild.parser
import rebuild.analyser


"""
Inspired by the simpler regex language SLR https://simple-regex.com/

- Helps you write maintainable regex patterns, that are readable, regardless of how good you are at regex
- ReBuild creates optimised regex patterns by analysing the input patterns
- It uses non-capturing groups as often as possible to enhance performance
- Fully string based: Can be used with many different tools
- Lets you use your beloved autocomplete for generating regex patterns
- Helps you discover new ways of writing regex patterns, that involve more code reuse 

---

either(...) is a good example of the optimisation power:

either("abc", "123", "def")
>>> "(?:abc|123|def)"

either("[a-z]", "[0-9"], "def")
>>> "(?:[a-z0-9]|def)"
ReBuild detects the two char sets and combines them

either("[a-z]", "[0-9]")
>>> "[a-z0-9]"
It detects that an OR is not necessary, and optimises it away

either("a", "b", "c")
>>> "[abc]"
ReBuild transforms the OR of individual characters into a single character set
"""


# Find all the characters in the [...] character sets
# The problem is that [abc\]], []] and [abc\\] are all valid
# and that [abc\]de] should result in abc\]de
# and that [abc\\]de] should result in abc\\

# \\\\ = Double back slash
# \\] = Escaped ] character
# . = Any other character
_CHAR_SET_PATTERN = r"\[((?:\\\\|\\]|.)+?)\]"
# TODO: Use improved pattern: \[((?:\\\\|\\]|[^\\\n])+?)\]


INTERMEDIATE_OPTIMISATION = True


def must_begin() -> str:
    return "^"


def must_end() -> str:
    return "$"


def force_full(pattern: str) -> str:
    regex = must_begin() + pattern + must_end()

    # Empty full match
    if pattern == "":
        return regex

    return _optimise_intermediate(regex)


def non_capture(pattern: str) -> str:
    if pattern == "":
        return "(?:)"

    pattern = _optimise_intermediate(pattern)
    return f"(?:{pattern})"


def optionally(pattern: str, check_for_empty_first=False) -> str:
    if pattern == "":
        return ""

    regex = non_capture(pattern) + "?"
    if check_for_empty_first:
        regex += "?"

    return _optimise_intermediate(regex)


def one_or_more(pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    regex = non_capture(pattern) + "+"

    if not greedy:
        regex += "?"

    return _optimise_intermediate(regex)


def at_least_n_times(n: int, pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    regex = f"{non_capture(pattern)}" + "{" + str(n) + ",}"

    if not greedy:
        regex += "?"

    return _optimise_intermediate(regex)


def exactly_n_times(n: int, pattern: str) -> str:
    if pattern == "":
        return ""

    regex = f"{non_capture(pattern)}" + "{" + str(n) + "}"

    return _optimise_intermediate(regex)


def at_least_n_but_not_more_than_m_times(n: int, m: int, pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    regex = f"{non_capture(pattern)}" + "{" + str(n) + "," + str(m) + "}"
    if not greedy:
        regex += "?"

    _optimise_intermediate(regex)


def at_most_n_times(n: int, pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    regex = f"{non_capture(pattern)}" + "{," + str(n) + "}"

    if not greedy:
        regex += "?"

    return _optimise_intermediate(regex)


def zero_or_more(pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    regex = non_capture(pattern) + "*"

    if not greedy:
        regex += "?"

    return _optimise_intermediate(regex)


def either(*groups) -> str:
    # Filter out empty strings
    groups = list(filter(None, groups))

    if len(groups) == 0:
        return ""

    regex = non_capture("|".join(non_capture(group) for group in groups))
    return _optimise_intermediate(regex)


def lookahead(pattern: str) -> str:
    if pattern == "":
        return ""

    regex = f"(?={pattern})"
    return _optimise_intermediate(regex)


def negative_lookahead(pattern: str) -> str:
    if pattern == "":
        return ""

    regex = f"(?!{pattern})"
    return _optimise_intermediate(regex)


def lookbehind(pattern: str) -> str:
    if pattern == "":
        return ""

    regex = f"(?<={pattern})"
    return _optimise_intermediate(regex)


def negative_lookbehind(pattern: str) -> str:
    if pattern == "":
        return ""

    regex = f"(?<!{pattern})"
    return _optimise_intermediate(regex)


def _literally_char(character):
    if re.match(r"[.\[\]*+?]", character):
        return "\\" + character

    return character


# If it is not Python flavoured Regex, then this should be updated to check for more characters
def literally(pattern: str) -> str:
    literal = re.escape(pattern)
    literal = re.sub("\"", "\\\"", literal)
    # literal = "".join([_literally_char(char) for char in pattern])
    return literal


def capture(pattern: str, name: str = None) -> str:
    if name is None:
        regex = f"({pattern})"
    else:
        regex = f"(?P<{name}>{pattern})"

    return _optimise_intermediate(regex)


def match_previous(num: int = None, name: str = None) -> str:
    if num is not None:
        regex = f"\\{num}"
    elif name is not None:
        regex = f"(?P={name})"
    else:
        return ""

    return _optimise_intermediate(regex)


def one_of(possible_characters: str) -> str:
    if possible_characters == "":
        return ""

    regex = f"[{possible_characters}]"
    return _optimise_intermediate(regex)


def mode(pattern: str,
         unicode=False,
         ascii=False,
         ignore_case=False,
         verbose=False,
         multiline=False,
         locale_dependant=False,
         dotall=False) -> str:

    modifiers = ""
    if unicode:     modifiers += "u"
    if ascii:       modifiers += "a"
    if ignore_case: modifiers += "i"
    if verbose:     modifiers += "x"
    if multiline:   modifiers += "m"
    if locale_dependant: modifiers += "L"
    if dotall:      modifiers += "s"

    # Must have at least one modifier active!
    assert len(modifiers) > 0

    regex = f"(?{modifiers}:{pattern})"

    return _optimise_intermediate(regex)


def match_everything_but(pattern: str) -> str:
    return _optimise_intermediate(force_full(negative_lookahead(pattern) + r".*"))


def digit() -> str:
    return r"\d"


def letter() -> str:
    return r"[a-zA-Z]"


def whitespace() -> str:
    return r"\s"


def word_char() -> str:
    return r"\w"


def anything() -> str:
    return r"."


def if_group_exists_then_else(name: str, then: str, elsewise: str) -> str:
    regex = f"(?({name}){non_capture(then)}|{non_capture(elsewise)})"

    return _optimise_intermediate(regex)


# Aliased functions

def capture_as(name: str, pattern: str) -> str:
    """Same as capture(pattern, name)"""
    return capture(pattern, name)


def if_followed_by(pattern: str) -> str:
    return lookahead(pattern)


def if_not_followed_by(pattern: str) -> str:
    return negative_lookahead(pattern)


def if_preceded_by(pattern: str) -> str:
    return lookbehind(pattern)


def if_not_preceded_by(pattern: str) -> str:
    return negative_lookbehind(pattern)


def _optimise_intermediate(regex: str):
    if not INTERMEDIATE_OPTIMISATION:
        return regex

    tree = rebuild.parser.regex_to_tree(regex)
    optimised = tree.optimised()
    return optimised.regex(as_atom=False)


def optimise(regex: str, is_root=True):
    tree = rebuild.parser.regex_to_tree(regex)
    optimised = tree.optimised()

    if type(tree) is rebuild.analyser.Alternation and is_root:
        return tree.regex(is_root=True)

    return optimised.regex(as_atom=(not is_root))
