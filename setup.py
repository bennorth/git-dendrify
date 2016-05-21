import re
from setuptools import setup, find_packages

with open('dendrify/_version.py') as f_in:
    m = re.match("__version__ = '([^']*)'", f_in.read())
    _version = m.group(1)

setup(
    name = 'gitdendrify',
    version = _version,
    packages = find_packages(),
    entry_points={
        'console_scripts': ['git-dendrify = dendrify.cli:main']},
)
