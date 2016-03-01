#pseudon-python

a python to pseudon translator

Pseudon is a dynamic language intertranspiler: it can translate a subset of each supported language to a any of the others.

This python to pseudon translator would add automatic support for
  * python to javascript
  * python to c++
  * python to c#
  * python to go
  * python to ruby
  * python to any other pseudon-supported language

[pseudon compiler](https://github.com/alehander42/pseudon)

## supported subset

pseudon supports a very clear and somehow limited subset of a language:

  * basic types: integer, float, string, boolean, nil
  * lists
  * dicts
  * standard library methods for the basic types
  * functions with normal parameters (no default/keyword/vararg parameters)
  * classes (only as a constructor + a collection of instance methods, no fancy metaprogramming etc supported)
  * iteration (for-in loops / while)
  * conditionals (if / else if / else)
  * standard math/logical operations
  * basic exception-based error handling
  * standard io: print/input, file read/write, basic http requests
  * error handling and custom exceptions (basic support for builtin exceptions)

## why

Supporting full-blown Python to Ruby auto translation is hard.
However often we need to

  * translate/support some algorithms in different languages
  * translate/support some text/data processing tool in different languages
  * generate code for the same task/algorithm in different languages

Often that code is(or can be) expressed in very similar way, with
similar constructs and basic types and data structures. On that level
a lot of dynamic languages are very similar and the only real difference
is syntax and methods api. That's a feasible task for automatic translation
and actually the existance of `pseudon` is to fullfill a need of another
existing project.

You can almost think of it in a "~json-for-algorithms" way: we express
our code with standard basic types, collections and simple classes and we can translate to a common format(pseudon code) and using it as a middle ground between each supported language
  
## pseudon-python progress

- [ ] type inference
  - [ ] infers from function usage
  - [ ] checks if return type is consistent
  - [ ] infers collection element types
  - [ ] infers class attributes and their types

- [ ] supported pseudon-translayable syntax
  - [ ] functions
  - [ ] classes
