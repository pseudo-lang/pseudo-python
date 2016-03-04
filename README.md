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

Error handling: support for hierarchies of custom exceptions, weak support for builtin exceptions, only catching and raising an Exception

## pseudo-python compiler

pseudo-python checks if your program is using a valid pseudo-translatable subset of Python, type checks it according to pseudo type rules and generates a `<filename>.pseudo.yaml` output file containing pseudo-ast code

you can directly run `pseudo-python <filename.py> <lang>` e.g.

```bash
pseudo-python <filename.py> ruby
pseudo-python <filename.py> cpp
``` 
etc for all the supported pseudo languages (javascript, c++, c#, go, ruby and python)

a lot of work has been put into making pseudo-python error messages as clear and helpful as possible: they show the offending snippet of code and 
often they offer suggestions, list possible fixes or right/wrong ways to write something

## type inference

the rules are relatively simple: currently pseudo-python infers everything
from the usage of functions/classes, so you need to call/initialize all
of your functions/classes (except for no-arg functions)

often you don't really need to do that for **all** of them, you just need
to do it in a way that can create call graphs covering all of them 
(e.g. often you'll have `a` calling `b` calling `x` and you only need to 
have an `a` invocation in your source)

variables can't change their types, the equivalents for builtin types are
```python
list :  List[@element_type] # generic
dict:   Dictionary[@key_type @value_type] # generic
set:    Set[@element_type] # generic
tuple:  Array[@element_type] # for homogeneous tuples
        Tuple[@element0_type, @element1_type..] # for heterogeneous tuples
int:    Int
float:  Float
int/float: Number
str:    String
bool:   Boolean
```

There are several limitations which will probably be fixed in v0.3

If you initialize a variable/do first call to a function with a collection literal, it should have at least one element(that limitation will be until v0.3)

All attributes used in a class should be initialized in its `__init__`

Other pseudo-tips:

* Homogeneous tuples are converted to `pseudo` fixed length arrays and heterogeneous to `pseudo` tuples. in the future `pseudo-python` would analyze better `lists`/`tuple` usage to classify them better in `list`/`array`/`tuple` categories (which can optimize the resulting code in `go`/`c++`/`c#`)

* attributes that aren't called from other classes are translated as `private`, the other ones as `public`. The rule for methods is different:
`_name` ones are only translated as `private`. That can be added as
config option in the future

* multiple returns values are supported, but they are converted to `array`/`tuple`

* single inheritance is supported, `pseudo-python` supports polymorphism
but methods in children should accept the same types as their equivalents in the hierarchy (except `__init__`)

The easiest way to play with the type system is to just try several programs: `pseudo-python` errors should be enough to guide you, if not, 
you can always open an issue

## pseudo-python progress

- [x] type inference
  - [x] checks if return type is consistent
  - [x] infers collection element types
  - [x] infers class attributes and their types
