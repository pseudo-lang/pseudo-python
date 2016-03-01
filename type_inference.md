## type inference

pseudon-python makes two passes

On the first pass it converts the ast produced by builtin ast module to
pseudon-ast-like data structure and it infers types , checking that it can be
well typed for pseudon

On the second pass it annotates everything the types and it converts idioms and method calls
into pseudon-api compatible method calls

Example:

```python
class A:
    def __init__(self, a):
    	self.a = 2

	def double(self):
		return self.a * 2

s = []
s.append(A(22).double())
```

after first pass

```python
class:
  name: typename(A)
  methods: [
  	constructor:
  	  args: [local(a)]
	  body: [
	    instance_assignment:
	      name: a
	      value: int(2)
	  ]
	method:
	  name: local(double)
	  args: []
  ]

local_assignment:
  name: s
  value: list([])
```

after second pass the same but with
s.push and `return_type` `type_hint` for everything
