
import re
from ordered_set import OrderedSet


class RegexNode:
    def optimised(self) -> "RegexNode":
        return self

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return ""

    def __str__(self):
        return str(self.as_json())

    def __eq__(self, other):
        if self is other:
            return True

        if type(self) is not type(other):
            return False

        own_fields = tuple([(k, v) for k, v in self.__dict__.items() if not k.startswith("_")])
        other_fields = tuple([(k, v) for k, v in other.__dict__.items() if not k.startswith("_")])

        return own_fields == other_fields

    def __hash__(self):
        return hash(tuple([(k, v) for k, v in self.__dict__.items() if not k.startswith("_")]))

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

    def regex(self, as_atom=False, in_sequence=True) -> str:
        pattern = "".join(item.regex() for item in self.items)
        if as_atom:
            return "(?:" + pattern + ")"
        return pattern


# TODO: Add optimisations (Look at the either() in previous version in rebuild.py)
# TODO: Handle negative char sets [^...]
# TODO: Factor out common part in sequences
class Alternation (RegexNode):
    def __init__(self, options):
        self.options = options

    def optimised(self) -> "RegexNode":
        optimised = [item.optimised() for item in self.options]

        simplified_options = []

        # Flatten nested alternations (?:a|(?:b|c)) --> (?:a|b|c)
        for item in optimised:
            if type(item) is Alternation:
                simplified_options.extend(item.options)
                continue

            simplified_options.append(item)

        optimised = simplified_options
        simplified_options = []

        # Merge items together, that come directly after one another
        # (?:a|b|c|hello) --> (?:[abc]|hello)
        # (?:[0-9]|[a-z]|hello) --> (?:[0-9a-z]|hello)
        current_char_set = CharSet([])

        for item in optimised:
            succeeded = current_char_set.merge_with(item)

            if succeeded:
                continue

            if len(current_char_set.options) > 0:
                simplified_options.append(current_char_set.optimised())
                current_char_set = CharSet([])

            succeeded = current_char_set.merge_with(item)
            if not succeeded:
                simplified_options.append(item)

        if len(current_char_set.options) > 0:
            simplified_options.append(current_char_set.optimised())

        optimised = simplified_options
        optimised = [item.optimised() for item in optimised]

        # Alternations are not required for single items
        # (?:[a-z]) --> [a-z]
        # (?:hello) --> hello
        if len(optimised) == 1:
            return optimised[0]

        return Alternation(optimised)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        pattern = "|".join(option.regex() for option in self.options)

        if not in_sequence:
            return pattern
        return f"(?:{pattern})"


class SingleChar (RegexNode):
    def __init__(self, char):
        self.char = char

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return self.char


class OneOrMore (RegexNode):
    def __init__(self, pattern, is_lazy=False):
        self.is_lazy = is_lazy
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()
        return OneOrMore(optimised, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
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

        optimised = self.pattern.optimised()
        return ZeroOrMore(optimised, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
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

        optimised = self.pattern.optimised()
        return Optional(optimised, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        if type(self.pattern) is EmptyNode:
            return ""

        regex = self.pattern.regex(as_atom=True) + "?"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return f"(?:{regex})"

        return regex


class CapturingGroup (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        return CapturingGroup(self.pattern.optimised())

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return f"({self.pattern.regex(in_sequence=False)})"


class NonCapturingGroup (RegexNode):
    def __init__(self, pattern):
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        return self.pattern.optimised()

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return f"(?:{self.pattern.regex(in_sequence=False)})"


class NamedCapturingGroup (RegexNode):
    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        return NamedCapturingGroup(self.name, self.pattern.optimised())

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return f"(?P<{self.name}>{self.pattern.regex(in_sequence=False)})"


class ModeGroup (RegexNode):
    def __init__(self, modifiers, pattern):
        self.modifiers = modifiers
        self.pattern = pattern

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        if len(self.modifiers) == 0:
            return self.pattern.optimised()

        return ModeGroup(self.modifiers, self.pattern.optimised())

    def regex(self, as_atom=False, in_sequence=True) -> str:
        if type(self.pattern) is EmptyNode:
            return ""

        if len(self.modifiers) == 0:
            return self.pattern.regex(as_atom=as_atom)

        return f"(?{self.modifiers}:{self.pattern.regex(in_sequence=False)})"


class IfElseGroup (RegexNode):
    def __init__(self, name, then, elsewise):
        self.name = name
        self.then = then
        self.elsewise = elsewise

    def optimised(self) -> "RegexNode":
        if type(self.then) is EmptyNode and type(self.elsewise) is EmptyNode:
            return EmptyNode()
        return IfElseGroup(self.name, self.then.optimised(), self.elsewise.optimised())

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return f"(?({self.name}){self.then.regex()}|{self.elsewise.regex()})"


class Lookaround (RegexNode):
    def __init__(self, pattern, symbol="="):
        self.pattern = pattern
        self._symbol = symbol

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()
        return Lookaround(self.pattern.optimised(), self._symbol)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return f"(?{self._symbol}{self.pattern.regex(in_sequence=False)})"


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
    def regex(self, as_atom=False, in_sequence=True) -> str:
        return "^"


class AnchorEnd (RegexNode):
    def regex(self, as_atom=False, in_sequence=True) -> str:
        return "$"


# TODO: Add optimisation (Look at one_of of previous rebuild.py version)
class CharSet (RegexNode):
    def __init__(self, options, is_inverted=False):
        self.is_inverted = is_inverted
        self.options = options

    def optimised(self) -> "RegexNode":
        if len(self.options) == 0:
            return EmptyNode()

        unique_options = list(OrderedSet(self.options))

        if len(unique_options) == 1 and type(unique_options[0]) is SingleChar:
            return unique_options[0]

        # TODO: Remove single chars that are already included in a range

        return CharSet(unique_options, self.is_inverted)

    def merge_with(self, node):
        if type(node) is CharSet:
            if len(self.options) == 0:
                self.is_inverted = node.is_inverted

            if self.is_inverted and node.is_inverted:
                self_unique = OrderedSet(self.options)
                other_unique = OrderedSet(node.options)

                # [^abc] + [^bc] --> [^a]
                merged_options = self_unique.symmetric_difference(other_unique)
                self.options = list(merged_options)
                return True

            if not self.is_inverted and not node.is_inverted:
                self.options.extend(node.options)
                return True

            return False

        if not self.is_inverted and type(node) is SingleChar:
            self.options.append(node)
            return True

        return False

    def regex(self, as_atom=False, in_sequence=True) -> str:
        pattern = ''.join([option.regex() for option in self.options])

        if self.is_inverted:
            pattern = "^" + pattern

        if len(pattern) == 0:
            return ""

        return f"[{pattern}]"


# TODO: Add optimisation
class Range (RegexNode):
    def __init__(self, from_char, to_char):
        self.from_char = from_char
        self.to_char = to_char

    def optimised(self) -> "RegexNode":
        if self.from_char == self.to_char:
            return SingleChar(self.from_char)
        return self

    def regex(self, as_atom=False, in_sequence=True) -> str:
        return self.from_char + "-" + self.to_char


class RepeatExactlyN (RegexNode):
    def __init__(self, pattern, n, is_lazy=False):
        self.pattern = pattern
        self.n = n
        self.is_lazy = is_lazy

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        if self.n == 0:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == 1:
            return optimised

        return RepeatExactlyN(optimised, self.n, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{" + str(self.n) + "}"

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

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == 0:
            return ZeroOrMore(optimised)

        if self.n == 1:
            return OneOrMore(optimised)

        return RepeatAtLeastN(optimised, self.n, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{" + str(self.n) + ",}"

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

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        if self.n == 0:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == 1:
            return optimised

        return RepeatAtMostN(optimised, self.n, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{," + str(self.n) + "}"

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

    def optimised(self) -> "RegexNode":
        if type(self.pattern) is EmptyNode:
            return EmptyNode()

        optimised = self.pattern.optimised()

        if self.n == self.m:
            return RepeatExactlyN(optimised, self.n, is_lazy=self.is_lazy)

        if self.m == 0:
            return EmptyNode()

        if self.m == 1:
            return Optional(optimised, is_lazy=self.n==0)

        return RepeatBetweenNM(optimised, self.n, self.m, self.is_lazy)

    def regex(self, as_atom=False, in_sequence=True) -> str:
        regex = self.pattern.regex(as_atom=True)

        if regex == "":
            return ""

        regex += "{" + str(self.n) + "," + str(self.m) + "}"

        if self.is_lazy:
            regex += "?"

        if as_atom:
            return "(?:" + regex + ")"
        return regex
