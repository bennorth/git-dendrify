"""git-dendrify

Usage:
  git-dendrify (-h | --help)
  git-dendrify --version
  git-dendrify dendrify <new-branch> <base-commit> <linear-commit>
  git-dendrify linearize <new-branch> <base-commit> <dendrified-commit>
"""

import os
import pygit2 as git
import dendrify
import docopt
from dendrify._version import __version__

def dendrifier_for_path(dirname, _ceiling_dir_for_testing=''):
    try:
        repo = git.discover_repository(dirname, False, _ceiling_dir_for_testing)
    except KeyError:
        raise ValueError('could not find git repo starting from {}'.format(dirname))
    return dendrify.Dendrifier(repo, report=dendrify.ReportToStdout())

def main():
    args = docopt.docopt(__doc__, version='git-dendrify {}'.format(__version__))
    dendrifier = dendrifier_for_path(os.getcwd())
    if args['dendrify']:
        dendrifier.dendrify(args['<new-branch>'],
                            args['<base-commit>'],
                            args['<linear-commit>'])
    elif args['linearize']:
        dendrifier.linearize(args['<new-branch>'],
                             args['<base-commit>'],
                             args['<dendrified-commit>'])
    else:
        raise ValueError('unknown action')
