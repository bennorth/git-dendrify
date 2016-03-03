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


def test_empty_repo(empty_repo):
    all_refs = empty_repo.listall_references()
    assert len(all_refs) == 0
