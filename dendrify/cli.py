# git-dendrify --- transform git histories (CLI)
# Copyright (C) 2016 Ben North
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    repo = git.discover_repository(dirname, False, _ceiling_dir_for_testing)
    if repo is None:
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
        raise RuntimeError('unknown action'
                           ' (docopt should have handled this situation)')  # pragma nocover
