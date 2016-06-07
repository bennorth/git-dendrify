"""git-dendrify

Usage:
  git-dendrify (-h | --help)
  git-dendrify --version
  git-dendrify dendrify [options] <new-branch> <base-commit> <linear-commit>
  git-dendrify linearize [options] <new-branch> <base-commit> <dendrified-commit>

Options:
  -h --help    Show this help info
  --version    Display version info and exit
  -q --quiet   Do not print commits as they are made
"""

import os
import pygit2 as git
import dendrify
import docopt
from dendrify._version import __version__

def dendrifier_for_path(dirname, _ceiling_dir_for_testing='', report_to_stdout=False):
    try:
        repo = git.discover_repository(dirname, False, _ceiling_dir_for_testing)
    except KeyError:
        raise ValueError('could not find git repo starting from {}'.format(dirname))
    kwargs = {'report': dendrify.ReportToStdout()} if report_to_stdout else {}
    return dendrify.Dendrifier(repo, **kwargs)

def main(_argv=None):
    args = docopt.docopt(__doc__, argv=_argv, version='git-dendrify {}'.format(__version__))
    dendrifier = dendrifier_for_path(os.getcwd(),
                                     report_to_stdout=(not args['--quiet']))
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
