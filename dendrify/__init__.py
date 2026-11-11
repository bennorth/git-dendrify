# git-dendrify --- transform git histories
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

import time
import sys
from dataclasses import dataclass
import click
import pygit2 as git
from enum import Enum


CommitType = Enum('CommitType', 'SectionStart SectionEnd Normal')


def repo_has_branch(repo, branch_name):
    m_existing_branch = repo.lookup_branch(branch_name)
    return (m_existing_branch is not None)


def create_signature(repo):
    return git.Signature(repo.config['user.name'],
                         repo.config['user.email'],
                         time=int(time.time()))


def create_base(repo, branch_name):
    """
    Create a branch in the repo with the given name, referring to a
    parentless commit with an empty tree.  Return the resulting Branch
    object.
    """
    if repo_has_branch(repo, branch_name):
        raise ValueError('branch "{}" already exists'.format(branch_name))

    tb = repo.TreeBuilder()
    empty_tree_oid = tb.write()

    sig = create_signature(repo)
    base_commit_oid = repo.create_commit(None,
                                         sig, sig,
                                         "Base commit for dendrify",
                                         empty_tree_oid,
                                         [])

    base_commit = repo[base_commit_oid]
    base_branch = repo.create_branch(branch_name, base_commit)

    return base_branch


@dataclass(frozen=True)
class ReportedCommit:
    """
    A commit just created on the destination branch, as passed to a reporter.
    """
    oid: git.Oid
    message: str
    kind: CommitType
    # Depth of the section which the commit opens, closes, or is within;
    # zero for a commit not within any section:
    depth: int

    @property
    def closes_section(self):
        return self.kind == CommitType.SectionEnd

    @property
    def short_sha1(self):
        return str(self.oid)[:12]

    @property
    def subject(self):
        return self.message.split('\n', 1)[0][:80]


class ReportToStdout:
    """
    Print each commit's short SHA1 (in green) and subject (in bold bright
    blue if the commit closes a section), showing the section structure
    with box-drawing characters, for example:

        20a2879eb675   Work item 2
        5d2568f585c2 ┌ Start work 3
        f72a8da48bd1 │ Work item 4
        cd4cc75fd075 │ ┌ Start work 5
        2a6fdca98049 │ │ Work item 6
        326b8905f082 │ └ Finish work 7
        d14597d3046d └ Finish work 8
        30810da21402   Work item 9

    By default (``color=None``), colour is only included if stdout is a
    terminal, as decided by ``click.echo()``.  Pass ``color=True`` or
    ``color=False`` to always or never include it.

    If stdout's encoding cannot represent the box-drawing characters,
    the structure is drawn with "/", "|" and "\\" instead.
    """
    BOX_DRAWING = {'start': '┌ ', 'within': '│ ', 'end': '└ '}
    ASCII = {'start': '/ ', 'within': '| ', 'end': '\\ '}

    def __init__(self, color=None):
        self.color = color
        self._drawing = None  # Chosen on first use, to suit stdout

    def __call__(self, commit):
        if self._drawing is None:
            self._drawing = self.drawing_for(sys.stdout)
        click.echo(self.format(commit), color=self.color)

    @classmethod
    def drawing_for(cls, stream):
        encoding = getattr(stream, 'encoding', None)
        if encoding is None:
            # For example, io.StringIO, which accepts any text.
            return cls.BOX_DRAWING
        try:
            ''.join(cls.BOX_DRAWING.values()).encode(encoding)
            return cls.BOX_DRAWING
        except (UnicodeEncodeError, LookupError):
            return cls.ASCII

    def structure(self, commit):
        drawing = self._drawing or self.BOX_DRAWING
        depth = commit.depth
        if commit.kind == CommitType.Normal:
            return drawing['within'] * depth if depth > 0 else '  '
        marker = drawing['start' if commit.kind == CommitType.SectionStart else 'end']
        return drawing['within'] * (depth - 1) + marker

    def format(self, commit):
        sha1 = click.style(commit.short_sha1, fg='green')
        subject = (click.style(commit.subject, fg='bright_blue', bold=True)
                   if commit.closes_section
                   else commit.subject)
        return '{sha1} {structure}{subject}'.format(sha1=sha1,
                                                    structure=self.structure(commit),
                                                    subject=subject)


class DoNotReport:
    def __call__(self, commit):
        pass


class Dendrifier:
    def __init__(self, repository_path, report=DoNotReport()):
        self.repo = git.Repository(repository_path)
        self.report = report

    @staticmethod
    def plain_message_from_tagged(msg):
        if msg.startswith('<s>'):
            return msg[3:]
        if msg.startswith('</s>'):
            return msg[4:]
        return msg

    def linear_ancestry(self, base_revision, branch_name):
        """
        Return a list of commits leading from the one referred to by ``base_revision``
        (but excluding it) up to and including the commit at the tip of ``branch_name``.
        There must be a linear ancestry chain starting at ``branch_name`` leading back
        to ``base_revision``.
        """
        oids = []
        oid = self.repo.lookup_branch(branch_name).target
        base_oid = self.repo.revparse_single(base_revision).id
        while True:
            if oid == base_oid:
                break
            oids.append(oid)
            commit = self.repo[oid]
            parents = commit.parent_ids
            if len(parents) > 1:
                raise ValueError('ancestry of "{}" is not linear'
                                 .format(branch_name))
            if not parents:
                raise ValueError('"{}" is not an ancestor of "{}"'
                                 .format(base_revision, branch_name))
            oid = parents[0]
        return list(reversed(oids))

    def _verify_branch_existence(self, tag, branch_name, must_exist):
        exists = repo_has_branch(self.repo, branch_name)
        if exists != must_exist:
            raise ValueError('{} branch "{}" {}'
                             .format(tag,
                                     branch_name,
                                     'exists' if exists else 'does not exist'))

    def dendrify(self, dendrified_branch_name, base_revision, linear_branch_name):
        self._verify_branch_existence('destination', dendrified_branch_name, False)
        self._verify_branch_existence('source', linear_branch_name, True)

        section_start_ids = []
        tip = self.repo.revparse_single(base_revision).id
        for id in self.linear_ancestry(base_revision, linear_branch_name):
            commit = self.repo[id]
            def commit_to_dest(msg, parent_ids, kind, depth):
                new_oid = self.repo.create_commit(None,
                                                  commit.author, commit.committer,
                                                  msg, commit.tree_id, parent_ids)
                self.report(ReportedCommit(new_oid, msg, kind, depth))
                return new_oid
            if commit.message.startswith('<s>'):
                section_start_ids.append(tip)
                tip = commit_to_dest(commit.message[3:], [tip],
                                     CommitType.SectionStart, len(section_start_ids))
            elif commit.message.startswith('</s>'):
                if not section_start_ids:
                    raise ValueError('unexpected section-end at {}'
                                     ' (no section in progress)'
                                     .format(id))
                depth = len(section_start_ids)
                start_id = section_start_ids.pop(-1)
                msg = commit.message[4:]
                tip = commit_to_dest(msg, [start_id, tip],
                                     CommitType.SectionEnd, depth)
            else:
                tip = commit_to_dest(commit.message, [tip],
                                     CommitType.Normal, len(section_start_ids))

        self.repo.create_branch(dendrified_branch_name, self.repo[tip])

    def flattened_ancestry(self, base_revision, branch_name):
        """
        Annotated flat list of commits leading up to the current target of
        ``branch_name``, starting from but not including the commit referred to by
        ``base_revision``.  Each element of the list is a pair (type, oid).  The 'type'
        is an element of the ``CommitType`` enumeration.
        """
        elts = []
        section_start_oids = []
        oid = self.repo.lookup_branch(branch_name).target
        base_oid = self.repo.revparse_single(base_revision).id
        while True:
            if oid == base_oid: break
            commit = self.repo[oid]
            parents = commit.parent_ids
            n_parents = len(parents)
            if n_parents == 0:
                raise ValueError('"{}" is not an ancestor of "{}"'
                                 .format(base_revision, branch_name))
            elif n_parents == 1:
                parent_id = parents[0]
                if section_start_oids and parent_id == section_start_oids[-1]:
                    elts.append((CommitType.SectionStart, oid))
                    section_start_oids.pop(-1)
                else:
                    elts.append((CommitType.Normal, oid))
                oid = parents[0]
            elif n_parents == 2:
                elts.append((CommitType.SectionEnd, oid))
                # parent[0] should be the 'main' branch, into which
                # parent[1] was merged; therefore we expect no diff
                # w.r.t. parent[1]:
                diff = self.repo.diff(self.repo[oid], self.repo[parents[1]])
                if len(diff) > 0:
                    raise ValueError('expected {} to be pure merge'.format(oid))
                section_start_oids.append(parents[0])
                oid = parents[1]
            else:
                raise ValueError('unexpected number of parents')
        return list(reversed(elts))

    def linearize(self, linear_branch_name, base_revision, dendrified_branch_name):
        self._verify_branch_existence('destination', linear_branch_name, False)
        self._verify_branch_existence('source', dendrified_branch_name, True)

        tip = self.repo.revparse_single(base_revision).id
        depth = 0
        for tp, id in self.flattened_ancestry(base_revision, dendrified_branch_name):
            commit = self.repo[id]
            def commit_to_dest(msg, parent_ids):
                new_oid = self.repo.create_commit(None,
                                                  commit.author, commit.committer,
                                                  msg, commit.tree_id, parent_ids)
                self.report(ReportedCommit(new_oid, msg, tp, depth))
                return new_oid
            if tp == CommitType.SectionStart:
                depth += 1
                tip = commit_to_dest('<s>{}'.format(commit.message), [tip])
            elif tp == CommitType.SectionEnd:
                tip = commit_to_dest('</s>{}'.format(commit.message), [tip])
                depth -= 1
            elif tp == CommitType.Normal:
                tip = commit_to_dest(commit.message, [tip])

        self.repo.create_branch(linear_branch_name, self.repo[tip])
