import pygit2 as git


class Dendrifier:
    def __init__(self, repository_path):
        self.repo = git.Repository(repository_path)
