import pytest
import pygit2 as git

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


class TestTransformations:
    def test_ensure_base(self, empty_dendrifier):
        assert empty_dendrifier.base_branch is not None

    def test_base_recreation_caught(self, empty_dendrifier):
        pytest.raises_regexp(ValueError, 'branch .* already exists',
                             empty_dendrifier._create_base,
                             empty_dendrifier.base_branch_name)
