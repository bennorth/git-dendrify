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


class ReportToStdout:
    def __call__(self, msg):
        sys.stdout.write(msg)
        sys.stdout.write('\n')


class DoNotReport:
    def __call__(self, msg):
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
        base_oid = self.repo.revparse_single(base_revision).oid
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
        tip = self.repo.revparse_single(base_revision).oid
        for id in self.linear_ancestry(base_revision, linear_branch_name):
            commit = self.repo[id]
            def commit_to_dest(msg, parent_ids):
                new_oid = self.repo.create_commit(None,
                                                  commit.author, commit.committer,
                                                  msg, commit.tree_id, parent_ids)
                report_txt = ('{sha1}{indent} * {subject}'
                              .format(indent='  ' * len(section_start_ids),
                                      sha1=str(new_oid)[:12],
                                      subject=msg.split('\n', 1)[0][:80]))
                self.report(report_txt)
                return new_oid
            if commit.message.startswith('<s>'):
                section_start_ids.append(tip)
                tip = commit_to_dest(commit.message[3:], [tip])
            elif commit.message.startswith('</s>'):
                if not section_start_ids:
                    raise ValueError('unexpected section-end at {}'
                                     ' (no section in progress)'
                                     .format(id))
                start_id = section_start_ids.pop(-1)
                msg = commit.message[4:]
                tip = commit_to_dest(msg, [start_id, tip])
            else:
                tip = commit_to_dest(commit.message, [tip])

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
        base_oid = self.repo.revparse_single(base_revision).oid
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

        tip = self.repo.revparse_single(base_revision).oid
        for tp, id in self.flattened_ancestry(base_revision, dendrified_branch_name):
            commit = self.repo[id]
            def commit_to_dest(msg, parent_ids):
                new_oid = self.repo.create_commit(None,
                                                  commit.author, commit.committer,
                                                  msg, commit.tree_id, parent_ids)
                report_txt = ('{sha1} * {subject}'
                              .format(sha1=str(new_oid)[:12],
                                      subject=msg.split('\n', 1)[0][:80]))
                self.report(report_txt)
                return new_oid
            if tp == CommitType.SectionStart:
                tip = commit_to_dest('<s>{}'.format(commit.message), [tip])
            elif tp == CommitType.SectionEnd:
                tip = commit_to_dest('</s>{}'.format(commit.message), [tip])
            elif tp == CommitType.Normal:
                tip = commit_to_dest(commit.message, [tip])

        self.repo.create_branch(linear_branch_name, self.repo[tip])
