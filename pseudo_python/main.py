#!/usr/bin/env python3
import os
import sys
import pseudo_python
import pseudo_python.errors
import pseudo
import pseudo.errors
from colorama import init
from termcolor import colored

USAGE = '''
pseudo-python <input-filename.py> [<output-filename> / <language>]

where if you omit <language>, pseudo-python will generate a 
<input-filename.pseudo.yaml> file with serialized ast 

if <output-filename> is provided, <language> will be extracted from 
the extension

it can be:
  py / python 
  rb / ruby
  js / javascript
  cs / csharp
  go

examples:
pseudo-python a.py # generates a.pseudo.yaml
pseudo-python z.py o.rb # generates a ruby translation in o.rb
'''

def main():
    if len(sys.argv) == 1:
        print(USAGE)
        return

    filename = sys.argv[1]
    with open(filename, 'r') as f:
        source = f.read()
    base, _ = os.path.splitext(filename)
    try:
        if len(sys.argv) == 2:
            clj = pseudo_python.translate_to_yaml(source)
            with open('%s.pseudo.yaml' % base, 'w') as f:
                f.write(clj)
            print(colored('OK\nsaved pseudo ast as %s.pseudo.yaml' % base, 'green'))
        else:
            arg = sys.argv[2]
            if '.' in arg:
                base, language = os.path.splitext(arg)
                language = language[1:]
            else:
                language = arg
            if language not in pseudo.SUPPORTED_FORMATS:
                print(colored('%s is not supported' % language, 'red'))
                exit(1)
            if '%s.%s' % (base, pseudo.FILE_EXTENSIONS[language]) == filename:
                print(colored('this would overwrite the input file, please choose another name', 'red'))                
                exit(1)
            node = pseudo_python.translate(source)
            output = pseudo.generate(node, language)
            with open('%s.%s' % (base, pseudo.FILE_EXTENSIONS[language]), 'w') as f:
                f.write(output)     
            print(colored('OK\nsaved as %s.%s' % (base, pseudo.FILE_EXTENSIONS[language]), 'green'))
    except pseudo_python.errors.PseudoError as e:
        print(colored(e, 'red'))
        if e.suggestions:
            print(colored(e.suggestions, 'green'))
        if e.right:
            print(colored('\nright:\n%s' % e.right, 'green'))
        if e.wrong:
            print(colored('\nwrong:\n%s' % e.wrong, 'red'))
        exit(1)
    except pseudo.errors.PseudoError as e:
        print(colored('Pseudo error:\n%s' % e, 'red'))
        exit(1)

if __name__ == '__main__':
    main()
