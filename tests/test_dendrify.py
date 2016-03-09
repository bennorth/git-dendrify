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
        if cd[0] == '[':
            commit('<s>Start work {}'.format(idx), parent.tree.oid)
        elif cd[0] == ']':
            commit('</s>Finish work {}'.format(idx), parent.tree.oid)
        elif cd[0] == '.':
            blob = repo.create_blob('{}\n'.format(idx).encode('utf-8'))
            tb = repo.TreeBuilder(parent.tree)
            tb.insert('data', blob, git.GIT_FILEMODE_BLOB)
            tree_oid = tb.write()
            commit('Work item {}'.format(idx), tree_oid)
        else:
            raise ValueError('unknown commit-descriptor')

        if len(cd) > 1:
            tip = repo[repo.lookup_branch('linear').target]
            repo.create_branch(cd[1:], tip)

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

    def test_plain_message(self):
        plain = dendrify.Dendrifier.plain_message_from_tagged
        assert plain('hello world') == 'hello world'
        assert plain('<s>hello world') == 'hello world'
        assert plain('</s>hello world') == 'hello world'

    def test_linear_ancestry(self, empty_dendrifier):
        descrs = '[[..][..]][....]'
        populate_repo(empty_dendrifier.repo, descrs)
        ancestry = empty_dendrifier.linear_ancestry('dendrify-base', 'linear')
        self._test_ancestry_matches_descriptors(empty_dendrifier.repo,
                                                ancestry,
                                                descrs)

    def test_populate_repo(self, empty_repo):
        populate_repo(empty_repo, ['.', '.', '.develop', '[', '[', '.', ']', ']'])
        repo = empty_repo  # Can't really go on calling it 'empty_repo'.
        # Work backwards and check:
        exp_msgs = ['</s>Finish work 7',
                    '</s>Finish work 6',
                    'Work item 5',
                    '<s>Start work 4',
                    '<s>Start work 3',
                    'Work item 2',
                    'Work item 1',
                    'Work item 0']
        tip = repo[repo.lookup_branch('linear').target]
        for exp_msg in exp_msgs:
            assert tip.message == exp_msg
            assert len(tip.parents) == 1
            tip = tip.parents[0]
        assert repo[repo.lookup_branch('develop').target].message == exp_msgs[5]

    def test_dendrify(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        populate_repo(repo, ['.', '.', '.develop',
                             '.', # 0 --- index in linear ancestry
                             '[', # 1
                             '[', # 2
                             '.', # 3
                             ']', # 4
                             ']', # 5
                             '.', # 6
                             ])
        empty_dendrifier.dendrify('dendrified', 'develop', 'linear')
        lin_commit_oids = empty_dendrifier.linear_ancestry('develop', 'linear')
        exp_links = [(6, 5), (5, 4), (5, 1), (4, 3), (4, 2),
                     (3, 2), (2, 1), (1, 0), (0, -1)]

        develop_oid = repo.lookup_branch('develop').target
        dendrified_tip_oid = repo.lookup_branch('dendrified').target

        dendrified_oid_f_msg = {}
        for c in repo.walk(dendrified_tip_oid, git.GIT_SORT_TOPOLOGICAL):
            if c.id == develop_oid: break
            dendrified_oid_f_msg[c.message] = c.id

        plain = dendrify.Dendrifier.plain_message_from_tagged
        dendrified_oid_f_lin_idx = {}
        for idx, oid in enumerate(lin_commit_oids):
            dendrified_oid = dendrified_oid_f_msg[plain(repo[oid].message)]
            dendrified_oid_f_lin_idx[idx] = dendrified_oid

        for lin_idx, dendrified_oid in dendrified_oid_f_lin_idx.items():
            exp_parent_idxs = [link[1] for link in exp_links if link[0] == lin_idx]
            exp_parent_oids = [(dendrified_oid_f_lin_idx[idx] if idx >= 0 else develop_oid)
                               for idx in exp_parent_idxs]
            got_parent_oids = repo[dendrified_oid].parent_ids
            assert set(exp_parent_oids) == set(got_parent_oids)

    def test_linearize(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        populate_repo(repo, ['.', '.', '.develop',
                             '.', '[', '[', '.', ']', ']', '.'])
        empty_dendrifier.dendrify('dendrified', 'develop', 'linear')
        lin_commit_oids = empty_dendrifier.linear_ancestry('develop', 'linear')
        empty_dendrifier.linearize('linear-1', 'develop', 'dendrified')
        lin_commit_oids_1 = empty_dendrifier.linear_ancestry('develop', 'linear-1')
        orig_msgs = [repo[oid].message for oid in lin_commit_oids]
        rtrp_msgs = [repo[oid].message for oid in lin_commit_oids_1]
        assert orig_msgs == rtrp_msgs
