
import re


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
It detects that a logical or is not necessary, and optimises it away

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


def _get_char_set_content(pattern):
    match = re.match(_CHAR_SET_PATTERN, pattern)

    if match is None:
        return None

    # The match isn't an exact one
    if match.group(0) != pattern:
        return None

    content = match.group(1)

    # The edge case, that the regex can't detect: [abc\]
    if content.replace("\\\\", "").endswith("\\"):
        return None

    return content


def _is_only_char_set(pattern):
    return bool(_get_char_set_content(pattern))


def _only_in_char_set(char, pattern):
    if char not in pattern:
        return False

    matches = re.findall(_CHAR_SET_PATTERN, pattern)

    # Check for the edge cases, where the regex pattern produces a false positive
    for match in matches:
        if match.replace("\\\\", "").endswith("\\") and char in match:
            return False

    outside_char_sets = re.sub(_CHAR_SET_PATTERN, "", pattern)
    if char in outside_char_sets:
        return False

    return True


# TODO: Find a better name
def _is_only_in_group(pattern):
    # Remove all char sets (as these could potentially contain brackets)
    pattern = re.sub(_CHAR_SET_PATTERN, "", pattern)

    # Remove literal \ back slashes (that do not make brackets literal characters)
    pattern = pattern.replace(r"\\", "")

    # Find all non-literal bracket characters: ( or )
    brackets = re.findall(r"(?<!\\)\(|(?<!\\)\)", pattern)

    if len(brackets) == 0:
        return False

    is_single_group = True

    # Group depth (1 (2 (3)))
    depth = 0
    is_at_start = True
    for bracket in brackets:
        if bracket == "(":
            # This marks the start of a second group, e.g. ()()
            if depth == 0 and not is_at_start:
                is_single_group = False

            depth += 1
        elif bracket == ")":
            depth -= 1

        is_at_start = False

    # Brackets are mismatched, e.g. (((abc)
    if depth != 0:
        return False

    if not is_single_group:
        return False

    if not pattern.startswith("(") or not pattern.endswith(")"):
        return False

    return True


def _is_single_char(pattern):
    if len(pattern) == 1:
        return True

    if re.match(r"^\\.$", pattern):
        return True

    return False


def _group(pattern: str) -> str:
    """Logically groups a pattern, like you would with (...), but only when strictly necessary"""

    if len(pattern) == 0:
        return ""

    if _is_only_char_set(pattern):
        return pattern

    if _is_only_in_group(pattern):
        return pattern

    # E.g. "\s", "\.", "\w"
    if _is_single_char(pattern):
        return pattern

    return non_capture(pattern)


def _ungroup(pattern: str) -> str:
    if not pattern.startswith("(?:"):
        return pattern

    if not _is_only_in_group(pattern):
        return pattern

    pattern = re.sub(r"^\(\?:", "", pattern)
    pattern = re.sub(r"\)$", "", pattern)
    return pattern


def must_begin() -> str:
    return "^"


def must_end() -> str:
    return "$"


def force_full(pattern: str) -> str:
    return must_begin() + pattern + must_end()


def non_capture(pattern: str) -> str:
    return f"(?:{pattern})"


def optionally(pattern: str, check_for_empty_first=False) -> str:
    if pattern == "":
        return ""

    if check_for_empty_first:
        return _group(pattern) + "??"

    return _group(pattern) + "?"


def one_or_more(pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    if not greedy:
        return _group(pattern) + "+?"

    return _group(pattern) + "+"


def at_least_n_times(n: int, pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    if n == 0:
        return zero_or_more(pattern, greedy)
    if n == 1:
        return one_or_more(pattern, greedy)

    if not greedy:
        return f"{_group(pattern)}" + "{" + str(n) + ",}?"

    return f"{_group(pattern)}" + "{" + str(n) + ",}"


def exactly_n_times(n: int, pattern: str) -> str:
    if pattern == "":
        return ""

    if n == 0:
        return ""
    if n == 1:
        return pattern
    return f"{_group(pattern)}" + "{" + str(n) + "}"


def at_least_n_but_not_more_than_m_times(n: int, m: int, pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    if n == m:
        return exactly_n_times(n, pattern)

    if m == 0:
        return ""

    if m == 1:
        return pattern + "?" if n == 0 else ""

    if not greedy:
        return f"{_group(pattern)}" + "{" + str(n) + "," + str(m) + "}?"

    return f"{_group(pattern)}" + "{" + str(n) + "," + str(m) + "}"


def at_most_n_times(n: int, pattern: str, greedy=True) -> str:
    return at_least_n_but_not_more_than_m_times(0, n, pattern, greedy)


def zero_or_more(pattern: str, greedy=True) -> str:
    if pattern == "":
        return ""

    if not greedy:
        return _group(pattern) + "*?"
    return _group(pattern) + "*"


# TODO: Optimise nested either blocks (that do not capture!)
# (?:a|(?:b|c)) --> (?:a|b|c)
# TODO: Handle negative char sets [^...]
def either(*groups) -> str:
    # Filter out empty strings
    groups = list(filter(None, groups))

    if len(groups) == 0:
        return ""

    simplified_groups = []

    # Simplify character sets that come directly after another into one char set
    # (abc|[a-z]|[0-9]|def) --> (abc|[a-z0-9]|def)
    current_char_set = ""

    for group in groups:
        next_char_set = _get_char_set_content(group)

        if next_char_set is not None and not next_char_set.startswith("[^"):
            if next_char_set.startswith("]") and len(current_char_set) > 0:
                # If it starts with a ], which is in fact legal, escape it when it is not the first character
                # as that would break the char set
                # []] => Fine
                # [abc\]] => Add escape character

                next_char_set = "\\" + next_char_set
            current_char_set += next_char_set
            continue

        # Characters such as "a", "\s", "\w" are also legal inside char sets
        # But keep special characters outside
        if _is_single_char(group) and not re.match(r"^[$^.]|\\[AbBZ]$", group):
            current_char_set += group
            continue

        # The next item is not a character set
        # Check if the previously created char set has some content and add it as a char set
        if len(current_char_set) > 0:
            if _is_single_char(current_char_set):
                # There is only one character in the set, e.g. [a]
                # => Remove redundant char set brackets
                simplified_groups.append(current_char_set)
            else:
                simplified_groups.append("[" + current_char_set + "]")
            current_char_set = ""

        simplified_groups.append(group)

    # Add the last character set
    if len(current_char_set) > 0:
        simplified_groups.append("[" + current_char_set + "]")

    if len(simplified_groups) == 0:
        return ""

    if len(simplified_groups) == 1:
        return simplified_groups[0]

    # Put elements in groups that strictly need to be
    simplified_groups = [
        _group(group) if "|" in group and not _is_only_in_group(group)
        else group
        for group in simplified_groups]

    pattern = "|".join(simplified_groups)
    return non_capture(pattern)


def lookahead(pattern: str) -> str:
    if pattern == "":
        return ""
    return f"(?={pattern})"


def negative_lookahead(pattern: str) -> str:
    if pattern == "":
        return ""
    return f"(?!{pattern})"


def lookbehind(pattern: str) -> str:
    if pattern == "":
        return ""
    return f"(?<={pattern})"


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


def negative_lookbehind(pattern: str) -> str:
    if pattern == "":
        return ""
    return f"(?<!{pattern})"


def capture(pattern: str, name: str = None) -> str:
    if _is_only_in_group(pattern):
        # Check if it is actually a non-capturing group
        if pattern.startswith("(?:"):

            # Remove the non-capturing group, as it is going to be wrapped in a capturing group anyway
            pattern = _ungroup(pattern)

    if name is None:
        return f"({pattern})"

    return f"(?P<{name}>{pattern})"


def match_previous(num: int = None, name: str = None) -> str:
    if num is not None:
        return f"\\{num}"

    if name is not None:
        return f"(?P={name})"

    return ""


def comment(note: str) -> str:
    return f"(#{note})"


def one_of(possible_characters: str) -> str:
    if possible_characters == "":
        return ""

    return f"[{possible_characters}]"


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

    return f"(?{modifiers}:{pattern})"


def match_everything_but(pattern: str) -> str:
    return force_full(negative_lookahead(pattern) + r".*")


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
    if "|" in then and not _only_in_char_set("|", then):
        then = _group(then)

    if "|" in elsewise and not _only_in_char_set("|", elsewise):
        elsewise = _group(elsewise)

    return f"(?({name}){then}|{elsewise})"


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
