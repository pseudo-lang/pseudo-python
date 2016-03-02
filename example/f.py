import re

e = {2}
f = (2,)
g = (8.2, 'a', [4])
h = re.compile(r'(x?)')
print(h.match('la').group(0))

# def f(h):
#     return h[2]

# def g(a):
# 	return [b[0] for b in a if True]

# f({2: 2})
# g(['Hello'])
