class Shape:
    def __init__(self, a):
        self.a = a

    def area(self):
        return self.a * self.a

s = Shape(0)
s.area()

# def fib(n):
#   if n < 2:
#       return 1
#   else:
#       return fib(n - 1) * fib(n - 2)

# def huh(l):
#   for j, k in enumerate(l):
#       print(j)

# f = 4
# while f == 2:
#   fib(4)
# huh([2])

# # import re

# # e = {2}
# # f = (2,)
# # g = (8.2, 'a', [4])
# # h = re.compile(r'(x?)')
# # print(h.match('la').group(0))

# # # def f(h):
# # #     return h[2]

# # # def g(a):
# # #   return [b[0] for b in a if True]

# # # f({2: 2})
# # # g(['Hello'])
