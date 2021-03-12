# ReBuild

> Some people, when confronted with a problem, think "I know, I'll use regular expressions." Now they have two problems.
> 
> *-- Jamie Zawinski*

With ReBuild you can write performant regex patterns in a readable and maintainable way by using functions. It is inspired by the Simple Regex Language ([SRL - Simple Regex Language](https://simple-regex.com/)).

![](images/EmailRegex.png)

### Why Rebuild?

- Helps you write **maintainable** regex patterns, that are **readable**, regardless of how good you are at regex

- ReBuild creates highly **optimised** regex patterns by **analysing** the input patterns

- It uses non-capturing groups as often as possible to **enhance performance**

- Fully **string based**: It's **versatile** and can be used with many different tools

- Lets you use your beloved **autocomplete** for generating regex patterns

- Helps you discover new ways of writing regex patterns, that involve **more code reuse**

### Optimisation

ReBuild does a lot of processing ahead of time (AOT) to generate performant and simple regex patterns. Many of its functions can optimise specific cases, which means that many functions provide zero-cost abstraction.

A good example to illustrate the optimisation power is the `either` function, which represents a regex OR function, e.g. `a|b|c`.

```python
# Matches the string abc, 123, or xyz
either("abc", "123", "xyz")
>>> '(?:abc|123|xyz)'


# Matches any letter from a to z, any digit or the string "xyz"
either("[a-z]", "[0-9]", "xyz")
>>> '(?:[a-z0-9]|xyz)'
# ReBuild detects the two character sets and combines them

# Matches any letter from a to z or any digit
either("[a-z]", "[0-9]")
>>> '[a-z0-9]'
# It detects that a OR is no longer necessary after 
# combining the character sets, and optimises it away


# Matches the character "a", "b" or "c"
either("a", "b", "c")
>>> '[abc]'
# ReBuild transforms the OR of individual characters into a single character set
```

### How it works

For every function (like `either`, `one_of`, ...) ReBuild does the following steps:

1. Generate a non-optimised regex pattern (`rebuild.builder`)

2. Parse this pattern and convert it to a tree structure (`rebuild.parser`)

3. Analyse and optimise the tree (`rebuild.analyser`)

4. Convert the tree back to a string regex pattern

As you can see from the aforementioned steps, ReBuild consists of 3 modules: `builder`, `parser` and `analyser`

- `rebuild.builder` provides the regex building functions like `either`, `one_of`, ... which first create a non-optimised pattern, but then run them through an intermediate optimisation process
  
  ```python
  print(either("a", "b", one_of("0-9"))
  # Before optimising (intermediate optimisations disabled for this example)
  >>> '(?:(?:a)|(?:b)|(?:[0-9]))'
  ```

- `rebuild.parser` parses string regex patterns with the amazing parsing library for Python [Lark](https://github.com/lark-parser/lark).
  
  First, it converts the regex pattern into a concrete syntax tree (CST)
  
  ```python
  # CST of '(?:(?:a)|(?:b)|(?:[0-9]))'
  
  alternation
    single_char    a
    single_char    b
    char_set
      range    0-9
  ```
  
  Then this tree is converted into the another tree, now consisting of `RegexNode`s, which are defined in the `rebuild.analyser` module. Amongst other things, these nodes contain more information about the pattern (AST).
  
  ```python
  Alternation
  |   Single Char: "a"
  |   Single Char: "b"
  |   Char Set
  |   |   Is Inverted: False
  |   |   Options
  |   |   |   Range
  |   |   |   |   From Char: "0"
  |   |   |   |   To Char: "9"
  ```

- `rebuild.analyser` defines the nodes of this tree, which each have rules for optimisations and methods for converting back to a string regex pattern.
  
  ```python
  # After optimisation
  
  Char Set
  |   Is Inverted: False
  |   Options
  |   |   Single Char: "a"
  |   |   Single Char: "b"
  |   |   Range
  |   |   |   From Char: "0"
  |   |   |   To Char: "9"
  ```
  
  Converted back to a string:
  
  ```python
  '[ab0-9]'
  ```

As you can see, ReBuild re-optimises the input string for every function, maximising readability and ease of use. 

Should you be worried about the performance penalty of re-optimising for every single function? 

No. ReBuild uses Lark's most optimised mode, a tree-less LALR(1) parser. Lark is the [fastest](https://github.com/lark-parser/lark#performance-comparison) parsing library available for Python. And after all, you should only generate the regex pattern once, store it in a constant and only use the constant for the rest of your program.

But if you want to only optimise once, you can do the following:

```python
import rebuild.builder

rebuild.builder.INTERMEDIATE_OPTIMISATION = False


from rebuild.builder import *

print(either("a", "b", "c"))
# (?:(?:a)|(?:b)|(?:c))

print(optimise(either("a", "b", "c")))
# [abc]
```