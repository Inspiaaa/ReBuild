
from rebuild.builder import *

pattern = force_full(
    capture_as(
        "name",
        one_or_more(either(digit(), letter(), one_of("._%+-"))))

    + literally("@")

    + capture_as(
        "domain",
        one_or_more(r"[\d\w.-]")
        + literally(".")
        + at_least_n_times(2, letter()))
)

print(pattern)

# Generates
# ^(?P<name>[\da-zA-Z._%+-]+)@(?P<domain>[\d\w.-]+\.[a-zA-Z]{2,})$

