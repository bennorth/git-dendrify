import pytest
import pygit2 as git
import time

try:
    import dendrify
except ImportError:
    import sys
    sys.path.insert(0, '..')
    import dendrify


@pytest.fixture
def empty_repo(tmpdir):
    return git.init_repository(tmpdir.strpath)


@pytest.fixture
def empty_dendrifier(empty_repo):
    return dendrify.Dendrifier(empty_repo.path)


def test_empty_repo(empty_repo):
    all_refs = empty_repo.listall_references()
    assert len(all_refs) == 0


def populate_repo(repo, commit_descriptors):
    assert not dendrify.repo_has_branch(repo, 'linear')
    linear_branch = dendrify.create_base(repo, 'linear')

    # TODO: Extract from config.
    sig = git.Signature('Nobody', 'nobody@example.com', time=int(time.time()))

    for idx, cd in enumerate(commit_descriptors):
        parent = repo[repo.lookup_branch('linear').target]
        def commit(msg, tree_oid):
            repo.create_commit('refs/heads/linear', sig, sig,
                               msg, tree_oid, [parent.oid.hex])
        if cd == '[':
            commit('<s>Start work {}'.format(idx), parent.tree.oid)
        elif cd == ']':
            commit('</s>Finish work {}'.format(idx), parent.tree.oid)
        elif cd == '.':
            blob = repo.create_blob('{}\n'.format(idx).encode('utf-8'))
            tb = repo.TreeBuilder(parent.tree)
            tb.insert('data', blob, git.GIT_FILEMODE_BLOB)
            tree_oid = tb.write()
            commit('Work item {}'.format(idx), tree_oid)
        else:
            raise ValueError('unknown commit-descriptor')

class TestTransformations:
    def test_ensure_base(self, empty_dendrifier):
        assert empty_dendrifier.base_branch is not None

    def test_base_recreation_caught(self, empty_dendrifier):
        pytest.raises_regexp(ValueError, 'branch .* already exists',
                             empty_dendrifier._create_base,
                             empty_dendrifier.base_branch_name)

    def _descr_from_commit(self, commit):
        # TODO: assert that diff to parent is empty/non-empty as reqd
        if commit.message.startswith('<s>'):
            return '['
        if commit.message.startswith('</s>'):
            return ']'
        return '.'

    def _test_ancestry_matches_descriptors(self, repo, oids, descrs):
        assert len(oids) == len(descrs)
        for oid, descr in zip(oids, descrs):
            commit = repo[oid]
            assert isinstance(commit, git.Commit)
            assert self._descr_from_commit(commit) == descr

    def test_linear_ancestry(self, empty_dendrifier):
        descrs = '[[..][..]][....]'
        populate_repo(empty_dendrifier.repo, descrs)
        ancestry = empty_dendrifier.linear_ancestry('linear')
        self._test_ancestry_matches_descriptors(empty_dendrifier.repo,
                                                ancestry[1:],
                                                descrs)
