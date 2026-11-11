# Shell completion for git-dendrify

This directory provides completion of subcommands, options and branch
names, for both `git dendrify ...` and `git-dendrify ...`.


## zsh

Copy `_git-dendrify` into a directory on your `$fpath`.  zsh's `git`
completion finds it there, and so also offers `dendrify` as a `git`
subcommand.  For example, in `~/.zshrc`:

```zsh
fpath=(~/.zsh/completions $fpath)  # directory containing _git-dendrify
autoload -U compinit && compinit
```

With oh-my-zsh, `$ZSH_CUSTOM/completions` is already on `$fpath`, so
copying `_git-dendrify` there is enough.

You might need to remove `~/.zcompdump` (with oh-my-zsh,
`~/.zcompdump-*`) and start a new shell for the new completion to be
picked up.

### Hints and headings

When completing the new branch name, nothing is offered (the branch
must not exist yet, or be "-" to only show the result), but a hint
"new branch (must not exist; - to only show result)" is available.
zsh only displays such hints, and the headings above each group of
completions, if a `format` is set for completion descriptions, for
example:

```zsh
zstyle ':completion:*:descriptions' format '%B%d%b'
```

This affects all completions, not just git-dendrify's.  With oh-my-zsh,
a file such as `$ZSH_CUSTOM/80-completion-styles.zsh` is a tidy place
for it.


## bash

With the `bash-completion` package and git's bash completion installed,
copy `git-dendrify` to
`~/.local/share/bash-completion/completions/git-dendrify`.  It is loaded
automatically when first needed, so no change to `~/.bashrc` is
required.
