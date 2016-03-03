#pseudo-python

a python to pseudo translator

Pseudo is a dynamic language intertranspiler: it can translate a subset of each supported language to a any of the others.

This Python to `Pseudo` translator would add automatic support for
  * Python to JavaScript
  * Python to C++
  * Python to C#
  * Python to Go
  * Python to Ruby
  * Python to any other pseudo-supported language

[pseudo compiler](https://github.com/alehander42/pseudo)

## supported subset

`Pseudo` supports a very clear and somehow limited subset of a language:
  
  * basic types and collections and standard library methods for them
  
  * integer, float, string, boolean, nil
  * lists
  * dicts
  * sets
  * tuples(fixed length heterogeneous lists)
  * fixed size arrays
  * regular expressions

  * functions with normal parameters (no default/keyword/vararg parameters)
  * classes 
    * single inheritance
    * polymorphism
    * no dynamic instance variables
    * basically a constructor + a collection of instance methods, no fancy metaprogramming etc supported

  * exception-based error handling with support for custom exceptions
  
  * io: print/input, file read/write, system and subprocess commands

  * iteration (for-in-range / for-each / for-in-zip / while)
  * conditionals (if / else if / else)
  * standard math/logical operations

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
and actually the existance of `Pseudo` is to fullfill a need of another
existing project.

You can almost think of it in a "~json-for-algorithms" way: we express
our code with standard basic types, collections and simple classes and we can translate to a common format(pseudo code) and using it as a middle ground between each supported language

Error handling: weak support for builtin exceptions, only catching
and raising an Exception

## pseudo-python progress

- [x] type inference
  - [x] checks if return type is consistent
  - [x] infers collection element types
  - [x] infers class attributes and their types

- [x] supported pseudo-translayable syntax
  - [x] functions
  - [x] classes
  - [x] a lot of stuff
