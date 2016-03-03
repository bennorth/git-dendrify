import time
import pygit2 as git


class Dendrifier:
    default_base_branch_name = 'dendrify-base'

    def __init__(self, repository_path, base_branch_name=default_base_branch_name):
        self.repo = git.Repository(repository_path)
        self.base_branch_name = base_branch_name

    def _create_base(self, branch_name):
        """
        Create a branch in the repo with the given name, referring to a
        parentless commit with an empty tree.  Return the resulting Branch
        object.
        """
        m_existing_branch = self.repo.lookup_branch(branch_name)
        if m_existing_branch is not None:
            raise ValueError('branch "{}" already exists'.format(branch_name))

        tb = self.repo.TreeBuilder()
        empty_tree_oid = tb.write()

        # TODO: Extract from config.
        sig = git.Signature('Nobody', 'nobody@example.com', time=int(time.time()))

        base_commit_oid = self.repo.create_commit(None,
                                                  sig, sig,
                                                  "Base commit for dendrify",
                                                  empty_tree_oid,
                                                  [])

        base_commit = self.repo[base_commit_oid]
        base_branch = self.repo.create_branch(branch_name, base_commit)

        return base_branch
