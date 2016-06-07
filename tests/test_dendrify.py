import pytest
import pygit2 as git
import time
import os
from io import StringIO
import sys
from contextlib import contextmanager

import dendrify
import dendrify.cli

@contextmanager
def temporary_cwd_within_repo(repo):
    dir = os.path.realpath(os.path.join(repo.path, '..'))
    try:
        saved_cwd = os.getcwd()
        os.chdir(dir)
        yield
    finally:
        os.chdir(saved_cwd)


@pytest.fixture
def empty_repo(tmpdir):
    return git.init_repository(tmpdir.strpath)


@pytest.fixture
def empty_dendrifier(empty_repo):
    return dendrify.Dendrifier(empty_repo.path)


def test_empty_repo(empty_repo):
    all_refs = empty_repo.listall_references()
    assert len(all_refs) == 0


def populate_repo(repo, commit_descriptors, branch_name='linear'):
    sig = dendrify.create_signature(repo)

    assert not dendrify.repo_has_branch(repo, 'test-base')
    base_commit = repo[dendrify.create_base(repo, 'test-base').target]
    repo.create_branch(branch_name, base_commit)
    ref_name = 'refs/heads/{}'.format(branch_name)

    for idx, cd in enumerate(commit_descriptors):
        parent = repo[repo.lookup_branch(branch_name).target]
        def commit(msg, tree_oid):
            repo.create_commit(ref_name, sig, sig,
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
            tip = repo[repo.lookup_branch(branch_name).target]
            repo.create_branch(cd[1:], tip)

class TestTransformations:
    def test_base_recreation_caught(self, empty_repo):
        dendrify.create_base(empty_repo, 'test-base')
        pytest.raises_regexp(ValueError, 'branch "test-base" already exists',
                             dendrify.create_base, empty_repo, 'test-base')

    def test_destination_branch_exists_caught(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        # Doesn't really matter that these branches are unrelated:
        dendrify.create_base(repo, 'test-base')
        dendrify.create_base(repo, 'dendrified')
        dendrify.create_base(repo, 'linear')
        pytest.raises_regexp(ValueError, 'destination branch "dendrified" exists',
                             empty_dendrifier.dendrify,
                             'dendrified', 'test-base', 'linear')

    def test_source_branch_does_not_exist_caught(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        # Doesn't really matter that these branches are unrelated:
        dendrify.create_base(repo, 'test-base')
        pytest.raises_regexp(ValueError, 'source branch "linear" does not exist',
                             empty_dendrifier.dendrify,
                             'dendrified', 'test-base', 'linear')

    def test_octopus_caught(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        base = dendrify.create_base(repo, 'test-base')
        base_tree_oid = repo[base.target].tree.oid

        sig = dendrify.create_signature(repo)
        def empty_commit(msg):
            return repo.create_commit(None, sig, sig,
                                      msg, base_tree_oid, [base.target.hex])
        commits = [empty_commit(str(i)) for i in range(3)]
        octopus = repo.create_commit(None, sig, sig, 'octopus', base_tree_oid, commits)
        repo.create_branch('octopus', repo[octopus])

        pytest.raises_regexp(ValueError, 'unexpected number of parents',
                             empty_dendrifier.linearize,
                             'linear', 'test-base', 'octopus')

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

    @pytest.mark.parametrize(
        'descrs',
        ['[[..][..]][....]', '[..]..[..][...][..]'],
        ids=['nested', 'with-singles'])
    #
    def test_linear_ancestry(self, empty_dendrifier, descrs):
        populate_repo(empty_dendrifier.repo, descrs)
        ancestry = empty_dendrifier.linear_ancestry('test-base', 'linear')
        self._test_ancestry_matches_descriptors(empty_dendrifier.repo,
                                                ancestry,
                                                descrs)

    @pytest.mark.parametrize(
        'repo_descr, exp_msgs',
        [(['.', '.', '.develop', '[', '[', '.', ']', ']'],
          ['</s>Finish work 7',
           '</s>Finish work 6',
           'Work item 5',
           '<s>Start work 4',
           '<s>Start work 3',
           'Work item 2',
           'Work item 1',
           'Work item 0']),
         (['[', '.', ']', '[', '.', ']', '.', '.develop', '[', '[', '.', ']', ']'],
          ['</s>Finish work 12',
           '</s>Finish work 11',
           'Work item 10',
           '<s>Start work 9',
           '<s>Start work 8',
           'Work item 7',
           'Work item 6',
           '</s>Finish work 5',
           'Work item 4',
           '<s>Start work 3',
           '</s>Finish work 2',
           'Work item 1',
           '<s>Start work 0'])],
        ids=['nested', 'with-consecutive-subsections'])
    #
    def test_populate_repo(self, empty_repo, repo_descr, exp_msgs):
        populate_repo(empty_repo, repo_descr)
        repo = empty_repo  # Can't really go on calling it 'empty_repo'.
        # Work backwards and check:
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
                             '[', # 5
                             '.', # 6
                             ']', # 7
                             ']', # 8
                             '.', # 9
                             ])
        empty_dendrifier.dendrify('dendrified', 'develop', 'linear')
        lin_commit_oids = empty_dendrifier.linear_ancestry('develop', 'linear')
        exp_links = [(9, 8), (8, 7), (8, 0), (7, 6), (7, 4), (6, 5),
                     (5, 4), (4, 3), (4, 1), (3, 2), (2, 1), (1, 0), (0, -1)]

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
                             '.', '[', '[', '.', ']', '[', '.', '.', ']', ']', '.'])
        empty_dendrifier.dendrify('dendrified', 'develop', 'linear')
        lin_commit_oids = empty_dendrifier.linear_ancestry('develop', 'linear')
        empty_dendrifier.linearize('linear-1', 'develop', 'dendrified')
        lin_commit_oids_1 = empty_dendrifier.linear_ancestry('develop', 'linear-1')
        orig_msgs = [repo[oid].message for oid in lin_commit_oids]
        rtrp_msgs = [repo[oid].message for oid in lin_commit_oids_1]
        assert orig_msgs == rtrp_msgs

    def test_linearize_swapped_parents(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        # Get repo started then manually create 'swapped' merge; we have to
        # try quite hard to arrange this as git tries quite hard to stop you
        # making that mistake.
        populate_repo(repo, ['.dev', '.', '.', '.'], branch_name='dendrified-0')
        feature_start_parent = repo.revparse_single('dev')
        tip = repo.revparse_single('dendrified-0')
        sig = dendrify.create_signature(repo)
        merge_oid = repo.create_commit(None, sig, sig, 'swapped merge test',
                                       tip.tree_id, [tip.oid, feature_start_parent.oid])
        repo.create_branch('dendrified', repo[merge_oid])
        pytest.raises_regexp(ValueError, 'expected .* to be pure merge',
                             empty_dendrifier.linearize, 'linear', 'dev', 'dendrified')

    def test_wrong_nesting(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        populate_repo(repo, ['.develop', '.', '.', ']'])
        pytest.raises_regexp(
            ValueError, 'unexpected section-end at .* \(no section in progress\)',
            empty_dendrifier.dendrify, 'dendrified', 'develop', 'linear')

    def test_nonlinear_ancestry(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        populate_repo(repo, ['.develop', '.', '.', '[', '.', '.', ']'])
        empty_dendrifier.dendrify('dendrified', 'develop', 'linear')
        pytest.raises_regexp(ValueError, 'ancestry of "dendrified" is not linear',
                             empty_dendrifier.dendrify,
                             're-dendrified', 'develop', 'dendrified')

    def test_dendrified_ancestry_reaches_root(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        populate_repo(repo, ['.develop', '.', '.', '[', '.', '.', ']'])
        empty_dendrifier.dendrify('dendrified', 'develop', 'linear')
        # Deliberately swap args so that base is not ancestor of branch:
        pytest.raises_regexp(ValueError, '"dendrified" is not an ancestor of "develop"',
                             empty_dendrifier.linearize,
                             'linear-1', 'dendrified', 'develop')

    def test_linear_ancestry_reaches_root(self, empty_dendrifier):
        repo = empty_dendrifier.repo
        populate_repo(repo, ['.develop', '.', '.'])
        # Deliberately swap args to linear_ancestry() such that the
        # 'base' is not an ancestor of the branch:
        pytest.raises_regexp(ValueError, '"linear" is not an ancestor of "develop"',
                             empty_dendrifier.linear_ancestry,
                             'linear', 'develop')


class TestCommandLine:
    def test_reporting(self):
        try:
            # Don't really like this, but:
            saved_stdout = sys.stdout
            sys.stdout = captured_io = StringIO()
            dendrify.ReportToStdout()('hello world')
            assert captured_io.getvalue() == 'hello world\n'
        finally:
            sys.stdout = saved_stdout

    def test_no_repo_found(self, tmpdir):
        subdir = os.path.join(tmpdir.strpath, 'not-a-git-repo')
        os.mkdir(subdir)
        exp_msg = 'could not find git repo starting from {}'.format(subdir)
        pytest.raises_regexp(ValueError, exp_msg,
                             dendrify.cli.dendrifier_for_path, subdir, tmpdir.strpath)

    def test_construct_dendrifier(self, empty_repo):
        repo_top = os.path.realpath(os.path.join(empty_repo.path, '..'))
        subdir = os.path.join(repo_top, 'foo', 'bar', 'baz')
        os.makedirs(subdir)
        dendrifier = dendrify.cli.dendrifier_for_path(subdir)
        assert dendrifier.repo.path == empty_repo.path
