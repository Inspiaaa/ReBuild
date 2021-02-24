
from rebuild.builder import _group, _is_only_in_group, _ungroup
from rebuild.builder import _only_in_char_set, _is_single_char, _get_char_set_content, _is_only_char_set
from rebuild.builder import *


def test_get_char_set_content():
    # Test simple character sets
    assert _get_char_set_content("[abc]") == "abc"
    assert _get_char_set_content("[a-z0-9]") == "a-z0-9"

    # Test potentially difficult sets
    assert _get_char_set_content("[]]") == "]"
    assert _get_char_set_content(r"[abc\]]") == r"abc\]"
    assert _get_char_set_content(r"[[abc]") == r"[abc"
    assert _get_char_set_content(r"[abc\\]") == r"abc\\"

    # Test cases where it should not match
    assert _get_char_set_content("[abc]+") is None
    assert _get_char_set_content(r"[abc\]") is None
    assert _get_char_set_content(r"[abc][def]") is None


# _is_only_char_set is based on _get_char_set_content and therefore needn't be tested


def test_only_in_char_set():
    assert _only_in_char_set("|", "[ab|c]") is True
    assert _only_in_char_set("|", "[abc][de|f]") is True

    assert _only_in_char_set("|", "[abc]|") is False
    assert _only_in_char_set("|", r"\[ab|c\]") is False
    assert _only_in_char_set("|", "[|][abc]|") is False


def test_is_only_in_group():
    assert _is_only_in_group("(abc)") is True
    assert _is_only_in_group("(abc(def))") is True
    assert _is_only_in_group(r"(abc\\)") is True

    # Sequences
    assert _is_only_in_group("abc") is False
    assert _is_only_in_group(r"\(abc\)") is False
    assert _is_only_in_group("(abc)(def)") is False

    # Illegal / Incomplete captures
    assert _is_only_in_group("((((abc") is False
    assert _is_only_in_group(r"(abc\)") is False


def test_is_single_char():
    assert _is_single_char("a") is True
    assert _is_single_char(r"\s") is True

    assert _is_single_char("ab") is False
    assert _is_single_char("") is False


def test_group():
    assert _group("abc") == "(?:abc)"

    assert _group("[abc]") == "[abc]"
    assert _group("(abc)") == "(abc)"

    assert _group(r"\.") == r"\."
    assert _group("a") == "a"

    assert _group("(abc)(123)") == "(?:(abc)(123))"
    assert _group("[a-z][0-9]") == "(?:[a-z][0-9])"


def test_ungroup():
    assert _ungroup("(?:abc)") == "abc"

    assert _ungroup("(?:abc)(?:123)") == "(?:abc)(?:123)"

    # Don't affect capturing groups or groups with special meanings
    assert _ungroup("(abc)") == "(abc)"
    assert _ungroup("(?=abc)") == "(?=abc)"
