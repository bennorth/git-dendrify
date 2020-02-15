import re
from setuptools import setup, find_packages

with open('dendrify/_version.py') as f_in:
    m = re.match("__version__ = '([^']*)'", f_in.read())
    _version = m.group(1)

with open('long-description.md', 'rt') as f_in:
    long_description_md = f_in.read()

setup(
    name='gitdendrify',
    version=_version,
    author='Ben North',
    author_email='ben@redfrontdoor.org',
    description='Transform git history between linear and structured forms',
    long_description=long_description_md,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        ],
    python_requires='>=3.5',
    url='https://github.com/bennorth/git-dendrify',
    install_requires=['pygit2>=0.27.1', 'docopt'],
    tests_require=['pytest', 'pytest-raisesregexp'],
    packages=find_packages(),
    entry_points={
        'console_scripts': ['git-dendrify = dendrify.cli:main']},
)
