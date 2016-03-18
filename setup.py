from setuptools import setup

setup(
    name='pseudo-python',
    version='0.2.28',
    description='a python3 to pseudo compiler',
    author='Alexander Ivanov',
    author_email='alehander42@gmail.com',
    url='https://github.com/alehander42/pseudo-python',
    download_url='https://github.com/alehander42/pseudo-python/archive/v0.2.tar.gz',
    keywords=['compiler', 'generation', 'c++', 'ruby', 'c#', 'javascript', 'go', 'python', 'pseudo'],
    packages=['pseudo_python'],
    license='MIT',
    install_requires=[
        'PyYAML',
        'colorama',
        'termcolor',
        'pseudo>=0.2.3'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: JavaScript',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'console_scripts': [
            'pseudo-python=pseudo_python.main:main',
        ],
    },
)
