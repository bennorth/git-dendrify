import re
from setuptools import setup, find_packages

with open('dendrify/_version.py') as f_in:
    m = re.match("__version__ = '([^']*)'", f_in.read())
    _version = m.group(1)

setup(
    name='gitdendrify',
    version=_version,
    author='Ben North',
    author_email='ben@redfrontdoor.org',
    url='https://github.com/bennorth/git-dendrify',
    install_requires=['pygit2>=0.27.1', 'docopt'],
    tests_require=['pytest', 'pytest-raisesregexp'],
    packages=find_packages(),
    entry_points={
        'console_scripts': ['git-dendrify = dendrify.cli:main']},
)
