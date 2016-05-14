import time
import pygit2 as git
from enum import Enum


CommitType = Enum('CommitType', 'Root SectionStart SectionEnd Normal')


def repo_has_branch(repo, branch_name):
    m_existing_branch = repo.lookup_branch(branch_name)
    return (m_existing_branch is not None)


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

    # TODO: Extract from config.
    sig = git.Signature('Nobody', 'nobody@example.com', time=int(time.time()))

    base_commit_oid = repo.create_commit(None,
                                         sig, sig,
                                         "Base commit for dendrify",
                                         empty_tree_oid,
                                         [])

    base_commit = repo[base_commit_oid]
    base_branch = repo.create_branch(branch_name, base_commit)

    return base_branch


class Dendrifier:
    default_base_branch_name = 'dendrify-base'

    def __init__(self, repository_path, base_branch_name=default_base_branch_name):
        self.repo = git.Repository(repository_path)
        self.base_branch_name = base_branch_name
        self._ensure_has_base()

    def _has_branch(self, branch_name):
        return repo_has_branch(self.repo, branch_name)

    def _create_base(self, branch_name):
        return create_base(self.repo, branch_name)

    def _ensure_has_base(self):
        if not self._has_branch(self.base_branch_name):
            self._create_base(self.base_branch_name)

    @property
    def base_branch(self):
        return self.repo.lookup_branch(self.base_branch_name)

    @staticmethod
    def plain_message_from_tagged(msg):
        if msg.startswith('<s>'):
            return msg[3:]
        if msg.startswith('</s>'):
            if msg.endswith('<s>'):
                return msg[4:-3]
            return msg[4:]
        return msg

    def linear_ancestry(self, base_revision, branch_name):
        """
        Return a list of commits leading from the one referred to by ``base_revision``
        (but excluding it) up to and including the commit at the tip of ``branch_name``.
        There must be a linear ancestry chain starting at ``branch_name`` leading to
        ``base_revision``.

        TODO: Allow ancestry all the way back to a root?
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
            n_parents = len(parents)
            if n_parents > 1:
                raise ValueError('ancestry of "{}" is not linear'
                                 .format(branch_name))
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
                return self.repo.create_commit(None,
                                               commit.author, commit.committer,
                                               msg, commit.tree_id, parent_ids)
            if commit.message.startswith('<s>'):
                tip = commit_to_dest(commit.message[3:], [tip])
                section_start_ids.append(tip)
            elif commit.message.startswith('</s>'):
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
                # TODO: Handle case where we want to go all the way
                # back to a root commit?
                raise RuntimeError('reached root')
            elif n_parents == 1:
                if section_start_oids and oid == section_start_oids[-1]:
                    elts.append((CommitType.SectionStart, oid))
                    section_start_oids.pop(-1)
                else:
                    elts.append((CommitType.Normal, oid))
                oid = parents[0]
            elif n_parents == 2:
                # TODO: Check the two parents are the expected way round.
                section_start_oids.append(parents[0])
                elts.append((CommitType.SectionEnd, oid))
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
                return self.repo.create_commit(None,
                                               commit.author, commit.committer,
                                               msg, commit.tree_id, parent_ids)
            if tp == CommitType.Root:
                raise RuntimeError('encountered root commit')
            elif tp == CommitType.SectionStart:
                tip = commit_to_dest('<s>{}'.format(commit.message), [tip])
            elif tp == CommitType.SectionEnd:
                tip = commit_to_dest('</s>{}'.format(commit.message), [tip])
            elif tp == CommitType.Normal:
                tip = commit_to_dest(commit.message, [tip])

        self.repo.create_branch(linear_branch_name, self.repo[tip])
