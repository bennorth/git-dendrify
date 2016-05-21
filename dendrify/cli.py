import pygit2 as git
import dendrify

def dendrifier_for_path(dirname, _ceiling_dir_for_testing=''):
    try:
        repo = git.discover_repository(dirname, False, _ceiling_dir_for_testing)
    except KeyError:
        raise ValueError('could not find git repo starting from {}'.format(dirname))
    return dendrify.Dendrifier(repo)
