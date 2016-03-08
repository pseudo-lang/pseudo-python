f = 'apolonia.txt'
with open(f, 'r') as handler:
    source = handler.read()

print(source.split('\n'))
