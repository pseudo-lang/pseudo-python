b = 2
a = 4
b, a = a, b
print(a, b) # 2 4

def x(a):
	a[0], a[1] = a[1], a[0]
	return a

print(x([2, 4])) #[4, 2]

