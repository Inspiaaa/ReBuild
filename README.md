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