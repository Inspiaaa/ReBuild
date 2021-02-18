
import re


# Inspired by the simpler regex language SLR https://simple-regex.com/


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


def _group(pattern):
    """Logically groups a pattern, like you would with (...), but only when strictly necessary"""

    # a|b would result in a non capture, [a|b] would not
    if "|" in pattern and not _only_in_char_set("|", pattern):
        return non_capture(pattern)

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
    groups = [_group(group) if "|" in group else group for group in groups]
    pattern = "|".join(groups)
    return non_capture(pattern)


def lookahead(pattern):
    return f"(?={pattern})"


def negative_lookahead(pattern):
    return f"(?!{pattern})"


def lookbehind(pattern):
    return f"(?<={pattern})"


#def _literally_char(character):
#    if re.match(r"[.\[\]*+?]", character):
#        return "\\" + character
#
#    return character


def literally(pattern):
    return re.escape(pattern)


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
    return r"\w"


def space():
    return r"\s"


# Check email address
pat = force_full(
    capture(one_or_more(r"[\d\w._%+-]"), name="name")
    + literally("@")
    + capture(one_or_more(r"[\d\w.-]") + literally(".") + at_least_n_times(2, letter()), name="domain")
)
print(pat)
