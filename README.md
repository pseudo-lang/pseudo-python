[![Build Status](https://travis-ci.org/alehander42/pseudo-python.svg?branch=master)](https://travis-ci.org/alehander42/pseudo-python)
[![MIT License](http://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

#pseudo-python

A Python to JavaScript / Ruby / C++ / Go / C# / PHP translator

[Pseudo](https://github.com/alehander42/pseudo) is a framework for high level code generation: it is used by this compiler to translate a subset of Python to all Pseudo-supported languages

## Supported subset

Pseudo supports a very clear and somehow limited subset of a language:
  
  * basic types and collections and standard library methods for them
  
  * integer, float, string, boolean
  * lists
  * dicts
  * sets
  * tuples/structs(fixed length heterogeneous lists)
  * fixed size arrays
  * regular expressions

  * functions with normal parameters (no default/keyword/vararg parameters)
  * classes 
    * single inheritance
    * polymorphism
    * no dynamic instance variables
    * basically a constructor + a collection of instance methods, no fancy metaprogramming etc supported

  * exception-based error handling with support for custom exceptions
  (target languages support return-based error handling too)
  
  * io: print/input, file read/write, system and subprocess commands

  * iteration (for-in-range / for-each / iterating over several collections / while)
  * conditionals (if / else if / else)
  * standard math/logical operations

## pseudo-python compiler

pseudo-python checks if your program is using a valid pseudo-translatable subset of Python, type checks it according to pseudo type rules and generates a `<filename>.pseudo.yaml` output file containing pseudo-ast code

[TODO]
You can directly run `pseudo-python <filename.py> <lang>` e.g.

```bash
pseudo-python <filename.py> ruby
pseudo-python <filename.py> cpp
``` 
etc for all the supported pseudo languages (javascript, c++, c#, go, ruby and python)

## Error messages

A lot of work has been put into making pseudo-python error messages as clear and helpful as possible: they show the offending snippet of code and 
often they offer suggestions, list possible fixes or right/wrong ways to write something

![Screenshot of error messages](http://i.imgur.com/8W7QNgZ.png)

## Type inference

The rules are relatively simple: currently pseudo-python infers everything
from the usage of functions/classes, so has sufficient information when the program is calling/initializing all
of its functions/classes (except for no-arg functions)

Often you don't really need to do that for **all** of them, you just need to do it in a way that can create call graphs covering all of them  (e.g. often you'll have `a` calling `b` calling `x` and you only need to have an `a` invocation in your source)

You can also add type annotations. We are trying to respect existing Python3 type annotation conventions and currently pseudo-python recognizes `int`, `float`, `str`, `bool`, `List[<type>]`, 
`Dict[<key-type>, <value-type>]`, `Tuple[<type>..]`, `Set[<type>]` and `Callable[[<type>..], <type>]`

Beware, you can't just annotate one param, if you provide type annotations for a function/method, pseudo-python expects type hints for all params and a return type

Variables can't change their types, the equivalents for builtin types are
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

* Homogeneous tuples are converted to `pseudo` fixed length arrays and heterogeneous to `pseudo` tuples. [Pseudo](https://github.com/alehander42/pseudo) analyzes the tuples usage in the code and sometimes it translates them to classes/structs with meaningful names if the target language is `C#` `C++` or `Go` 

* Attributes that aren't called from other classes are translated as `private`, the other ones as `public`. The rule for methods is different:
`_name` ones are only translated as `private`. That can be added as
config option in the future

* Multiple returns values are supported, but they are converted to `array`/`tuple`

* Single inheritance is supported, `pseudo-python` supports polymorphism
but methods in children should accept the same types as their equivalents in the hierarchy (except `__init__`)

The easiest way to play with the type system is to just try several programs: `pseudo-python` errors should be enough to guide you, if not, 
you can always open an issue

