
import re


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

            if type(value) is str:
                return "\"" + value + "\""

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
                return name + ": " + subtree

            return {name: subtree}

        subtree = {}

        for field in fields:
            value = getattr(self, field)
            value_json = json_for(value)

            if value_json is None:
                # EmptyNode
                subtree[prettify_varname(field) + ": ---"] = None

            elif type(value_json) is str:
                subtree[prettify_varname(field) + ": " + value_json] = None
            else:
                subtree[prettify_varname(field)] = value_json

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
    def __init__(self, pattern, is_lazy):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""
        regex = self.pattern.regex(as_atom=True) + "+"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class ZeroOrMore (RegexNode):
    def __init__(self, pattern, is_lazy=False):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""
        regex = self.pattern.regex(as_atom=True) + "*"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class Optional (RegexNode):
    def __init__(self, pattern, is_lazy=False):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        if type(self.pattern) is EmptyNode:
            return ""
        regex = self.pattern.regex(as_atom=True) + "?"

        if self.is_lazy:
            regex += "?"

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


class ModeGroup (RegexNode):
    def __init__(self, modifiers, pattern):
        self.modifiers = modifiers
        self.pattern = pattern

    def regex(self, as_atom=False) -> str:
        return f"(?{self.modifiers}:{self.pattern.regex()})"


class Lookaround (RegexNode):
    def __init__(self, pattern, symbol="="):
        self.pattern = pattern
        self._symbol = symbol

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return self

    def regex(self, as_atom=False) -> str:
        return f"(?{self._symbol}{self.pattern.regex()})"


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


class AnchorStart (RegexNode):
    def regex(self, as_atom=False) -> str:
        return "^"


class AnchorEnd (RegexNode):
    def regex(self, as_atom=False) -> str:
        return "$"


class CharSet (RegexNode):
    def __init__(self, options):
        self.options = options

    def regex(self, as_atom=False) -> str:
        return f"[{''.join([option.regex() for option in self.options])}]"


class Range (RegexNode):
    def __init__(self, from_char, to_char):
        self.from_char = from_char
        self.to_char = to_char

    def optimised(self) -> "RegexNode":
        if self.from_char == self.to_char:
            return SingleChar(self.from_char)
        return self

    def regex(self, as_atom=False) -> str:
        return self.from_char + "-" + self.to_char


class RepeatExactlyN (RegexNode):
    def __init__(self, pattern, n, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True) + "{" + str(self.n) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex


class RepeatAtLeastN (RegexNode):
    def __init__(self, pattern, n, is_lazy):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True) + "{" + str(self.n) + ",}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex


class RepeatAtMostN (RegexNode):
    def __init__(self, pattern, n, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True) + "{," + str(self.n) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex


class RepeatBetweenNM (RegexNode):
    def __init__(self, pattern, n, m, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.m = m
        self.is_lazy = is_lazy

    def regex(self, as_atom=False) -> str:
        regex = self.pattern.regex(as_atom=True) + "{" + str(self.n) + "," + str(self.m) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex
