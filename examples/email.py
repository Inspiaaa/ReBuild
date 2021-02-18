
from rebuild import *

pat = force_full(
    capture_as("name", one_or_more(r"[\d\w._%+-]"))
    + literally("@")
    + capture_as("domain",
                 one_or_more(r"[\d\w.-]")
                 + literally(".")
                 + at_least_n_times(2, letter()))
)

print(pat)

# Generates
# ^(?P<name>[\d\w._%+-]+)@(?P<domain>[\d\w.-]+\.[a-zA-Z]{2,})$
