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

"""Command-line interface for git-dendrify"""

import os
from contextlib import contextmanager
import click
import pygit2 as git
import dendrify
from dendrify._version import __version__


def dendrifier_for_path(dirname, _ceiling_dir_for_testing='', report_to_stdout=False,
                        color=None):
    repo = git.discover_repository(dirname, False, _ceiling_dir_for_testing)
    if repo is None:
        raise ValueError('could not find git repo starting from {}'.format(dirname))
    kwargs = ({'report': dendrify.ReportToStdout(color=color)}
              if report_to_stdout else {})
    return dendrify.Dendrifier(repo, **kwargs)


_color_f_when = {'auto': None, 'always': True, 'never': False}


def _dendrifier_for_cwd(quiet, color):
    return dendrifier_for_path(os.getcwd(), report_to_stdout=(not quiet),
                               color=_color_f_when[color])


@contextmanager
def _errors_reported_cleanly():
    """
    Report errors arising from the user's input (bad branch names,
    histories of the wrong shape, etc.) as plain messages rather than
    tracebacks.
    """
    try:
        yield
    except ValueError as e:
        raise click.ClickException(str(e))
    except KeyError as e:
        # pygit2 raises KeyError for a revision which cannot be resolved.
        raise click.ClickException('not found: {}'.format(e.args[0]))


_quiet_option = click.option('-q', '--quiet', is_flag=True,
                             help='Do not print commits as they are made.')

_color_option = click.option('--color', type=click.Choice(list(_color_f_when)),
                             default='auto', show_default=True,
                             help='When to colour the printed commits:'
                                  ' "auto" means only if output is a terminal.')


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(__version__, prog_name='git-dendrify',
                      message='%(prog)s %(version)s')
def main():
    """Transform git history between linear and structured forms."""


@main.command('dendrify')
@_quiet_option
@_color_option
@click.argument('new_branch', metavar='NEW-BRANCH')
@click.argument('base_commit', metavar='BASE-COMMIT')
@click.argument('linear_branch', metavar='LINEAR-BRANCH')
def dendrify_command(quiet, color, new_branch, base_commit, linear_branch):
    """Convert a linear history into a structured one.

    Create NEW-BRANCH, which must not already exist, holding a structured
    version of the commits from BASE-COMMIT (exclusive) to the tip of the
    existing branch LINEAR-BRANCH.
    """
    with _errors_reported_cleanly():
        _dendrifier_for_cwd(quiet, color).dendrify(new_branch, base_commit, linear_branch)


@main.command('linearize')
@_quiet_option
@_color_option
@click.argument('new_branch', metavar='NEW-BRANCH')
@click.argument('base_commit', metavar='BASE-COMMIT')
@click.argument('dendrified_branch', metavar='DENDRIFIED-BRANCH')
def linearize_command(quiet, color, new_branch, base_commit, dendrified_branch):
    """Convert a structured history into a linear one.

    Create NEW-BRANCH, which must not already exist, holding a linear
    version of the commits from BASE-COMMIT (exclusive) to the tip of the
    existing branch DENDRIFIED-BRANCH.
    """
    with _errors_reported_cleanly():
        _dendrifier_for_cwd(quiet, color).linearize(new_branch, base_commit,
                                                    dendrified_branch)
