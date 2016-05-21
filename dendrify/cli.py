"""git-dendrify

Usage:
  git-dendrify (-h | --help)
  git-dendrify --version
  git-dendrify dendrify <new-branch> <base-commit> <linear-commit>
  git-dendrify linearize <new-branch> <base-commit> <dendrified-commit>
"""

import pygit2 as git
import dendrify
import docopt
from dendrify._version import __version__

def dendrifier_for_path(dirname, _ceiling_dir_for_testing=''):
    try:
        repo = git.discover_repository(dirname, False, _ceiling_dir_for_testing)
    except KeyError:
        raise ValueError('could not find git repo starting from {}'.format(dirname))
    return dendrify.Dendrifier(repo)

def main():
    args = docopt.docopt(__doc__, version='git-dendrify {}'.format(__version__))
