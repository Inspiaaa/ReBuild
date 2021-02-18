
import re


# Inspired by the simpler regex language SLR https://simple-regex.com/

# It generates optimised Regex patterns by analysing the input patterns
# Uses non capturing groups as often as possible to enhance performance


_CHAR_SET_PATTERN = r"^\[((?:\\\\|\\]|.)+?)\]$"


def _is_char_set(pattern):
    return bool(re.match(r"^\[((?:\\\\|\\]|.)+?)\]$", pattern))


def _only_in_char_set(char, pattern):
    if char not in pattern:
        return False

    # Find all the characters in the [...] character sets
    # The problem is that [abc\]] or []] or [abc\\] are all valid
    # and that [abc\]de] should result in abc\]de
    # and that [abc\\]de] should result in abc\\

    # \\\\ = Double back slash
    # \\] = Escaped ] character
    # . = Any other character
    matches = re.findall(r"\[((?:\\\\|\\]|.)+?)\]", pattern)

    for match in matches:
        if char not in match:
            return False

    return True


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

    if not is_single_group:
        return False

    if not pattern.startswith("(") and pattern.endswith(")"):
        return False

    return True


def _group(pattern):
    """Logically groups a pattern, like you would with (...), but only when strictly necessary"""

    if _is_char_set(pattern):
        return pattern

    if _is_only_in_group(pattern):
        return pattern

    # E.g. "\s", "\.", "\w"
    if re.match(r"^\\.$", pattern):
        return pattern

    if len(pattern) <= 1:
        return pattern

    if _is_char_set(pattern):
        return pattern

    # TODO: Add case for capture, e.g. (abc(de)) by counting non escaped brackets

    return non_capture(pattern)


def must_begin():
    return "^"


def must_end():
    return "$"


def force_full(pattern):
    return must_begin() + pattern + must_end()


def non_capture(pattern):
    return f"(?:{pattern})"


def optional(pattern, check_for_empty_first=False):
    if check_for_empty_first:
        return _group(pattern) + "??"

    return _group(pattern) + "?"


def one_or_more(pattern, greedy=True):
    if not greedy:
        return _group(pattern) + "+?"

    return _group(pattern) + "+"


def at_least_n_times(n, pattern, greedy=True):
    if not greedy:
        return f"{_group(pattern)}" + "{" + str(n) + ",}?"

    return f"{_group(pattern)}" + "{" + str(n) + ",}"


def exactly_n_times(n, pattern):
    if n == 0:
        return ""
    if n == 1:
        return pattern
    return f"{_group(pattern)}" + "{" + str(n) + "}"


def at_least_n_but_not_more_than_m_times(n, m, pattern, greedy=True):
    if not greedy:
        return f"{_group(pattern)}" + "{" + str(n) + "," + str(m) + "}?"

    return f"{_group(pattern)}" + "{" + str(n) + "," + str(m) + "}"


def zero_or_more(pattern, greedy=True):
    if not greedy:
        return _group(pattern) + "*?"
    return _group(pattern) + "*"


# TODO: Optimise for groups of only characters => [abc] instead of (?:a|b|) (also for \s, ...)
def any_of(*groups):
    groups = [
        _group(group) if "|" in group and not _is_only_in_group(group)
        else group
        for group in groups]

    pattern = "|".join(groups)
    return non_capture(pattern)


def lookahead(pattern):
    return f"(?={pattern})"


def negative_lookahead(pattern):
    return f"(?!{pattern})"


def lookbehind(pattern):
    return f"(?<={pattern})"


def _literally_char(character):
    if re.match(r"[.\[\]*+?]", character):
        return "\\" + character

    return character


# If it is not Python flavoured Regex, then this should be updated to check for more characters
def literally(pattern):
    literal = re.escape(pattern)
    # literal = "".join([_literally_char(char) for char in pattern])
    return literal


def negative_lookbehind(pattern):
    return f"(?<!{pattern})"


def capture(pattern, name=None):
    if name is None:
        return f"({pattern})"

    return f"(?P<{name}>{pattern})"


def match_previous(num=None, name=None):
    if num is not None:
        return f"\\{num}"

    if name is not None:
        return f"(?P={name})"


def comment(note):
    return f"(#{note})"


def mode(pattern,
         unicode=False,
         ascii=False,
         ignore_case=False,
         verbose=False,
         multiline=False,
         locale_dependant=False,
         dotall=False):

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


def match_everything_but(pattern):
    return force_full(negative_lookahead(pattern) + r".*")


def digit():
    return r"\d"


def letter():
    return r"[a-zA-Z]"


def space():
    return r"\s"


def anything():
    return r"."


# Aliased functions

def capture_as(name, pattern):
    """Same as capture(pattern, name)"""
    return capture(pattern, name)


def until(pattern):
    return negative_lookahead(pattern)
