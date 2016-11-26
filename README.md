# Git-Dendrify

Tool for converting `git` histories between hierarchical (tree-like) and
linear structures.

[![Build Status](https://travis-ci.org/bennorth/git-dendrify.svg?branch=master)](https://travis-ci.org/bennorth/git-dendrify)
[![Coverage Status](https://coveralls.io/repos/github/bennorth/git-dendrify/badge.svg?branch=master)](https://coveralls.io/github/bennorth/git-dendrify?branch=master)


## Acknowledgements

Thanks to [Adam Spiers](https://github.com/aspiers) for interesting and
helpful discussions, and contributing several ideas to this document.
Any errors remain my own.


## Motivation: Literate Programming

The claim that
['Code is read much more often than it is written'](https://blogs.msdn.microsoft.com/oldnewthing/20070406-00/?p=27343)
is certainly highly plausible, even if actual data seems hard to find.
In that post, Chen urges developers to 'design for readability', and the
idea goes back at least to Knuth's
[*Literate Programming*](http://www.literateprogramming.com/):

> Instead of imagining that our main task is to instruct a computer what
> to do, let us concentrate rather on explaining to human beings what we
> want a computer to do.

A good example of this approach is Pfaff's presentation of
[GNU libavl](http://adtinfo.org/).  While not being 'literate
programming' as such, it is related that when designing
the [Raft Consensus Algorithm](https://raft.github.io/), the authors
state that the 'primary goal was _understandability_'.

I've been wondering whether treating the code as a static snapshot is
missing a whole dimension in explanatory power.  Can we use the
development history of the code as an additional aid to understanding
it, especially if that history is 'designed for readability'?

One particular application I have in mind is for producing histories
which are explicitly intended as tutorial material, say for teaching
children about programming.  This seems an under-explored area, although
it has been discussed:

- Tauber talks about the two dimensions of versioning (as you read
  through the history of the repo; and as the repo itself is developed)
  in his
  ['Versioned Literate Programming for Tutorials'](https://thoughtstreams.io/jtauber/versioned-literate-programming-for-tutorials/).
- Giles Bowkett describes his use of a git repo as support
  material for his
  [book on Rails development](http://gilesbowkett.blogspot.ie/2016/10/modern-front-end-development-with-ruby_12.html):
  "A code base isn't a finished product, it's a continuum over time, and
  with a git repo, it's a *carefully indexed* continuum over time. I think
  that's an important aspect of making code clear, so I first did all my
  code-related research in other repos, and then built these repos so
  that the repos would themselves be easy to read".
- Jon Aquino talks about interspersing explanation with code in ['Git
  commit messages are the new Literate Programming'](http://jona.ca/blog/git-commit-messages-are-the-new-literate-programming).
- **Update 20160813:** See also
  [my `literate-git` project](https://github.com/bennorth/literate-git)
  for a fuller explanation of this idea, including a demo.

The idea need not be restricted to the presentation of a complete
program.  Making pieces of incremental development more readable is a
worthwhile goal.  For example, if a pull request can be presented as a
miniature literate program, building on the current state of the
codebase, it should be easier to review.

### Example

Suppose we are working on a word-processor, and we have released
`v0.8.0`.  Now we want to add the ability to print the document.  A
simplified flat list of commits to achieve this might be as follows,
most recent at the top:

```
* Allow choice of colour for printing watermarks
* Add known-good test cases for watermarks
* Emit watermark 'underneath' main output (printing)
* Drop-down for printing common watermarks
* Submit PDF to system print service
* Add known-good PDF-generation test cases
* Generate PDF
* Sort paper size choices alphabetically
* Read paper size choices from database
* Add selection box for paper sizes
* Read printer list from system
* Add selection box for which printer
* Parse 'chosen pages' input like '5-8,11,12-15'
* Allow free-form CSV list of pages
* Radio list for 'pages' UI: current, all, chosen
* Release v0.8.0
* Add spell-checker
:
:
```

Now suppose we could present this work in 'sections', such as when
writing an article or paper.  There is a natural fit for this tree-like
structure in terms of `git` merge commits:

```
* Add printing facility
|\
| * Add watermarks
| |\
| | * Allow choice of colour
| | * Add known-good test cases
| | * Emit watermark 'underneath' main output
| | * Drop-down for common watermarks
| |/
| * Add actual printing via PDF
| |\
| | * Submit PDF to system print service
| | * Add known-good test cases
| | * Generate PDF
| |/
| * Add paper selection UI
| |\
| | * Sort choices alphabetically
| | * Read paper size choices from database
| | * Add selection box for paper sizes
| |/
| * Add printer selection UI
| |\
| | * Read printer list from system
| | * Add selection box for which printer
| |/
| * Add page selection UI
| |\
| | * Parse input like '5-8,11,12-15'
| | * Allow free-form CSV list of pages
| | * Radio list: current, all, chosen
| |/
| |
|/
* Release v0.8.0
* Add spell-checker
:
:
```


### Advantages of hierarchical presentation

* The structure of the commits in terms of sub-tasks is immediately
  apparent, making the code easier to review and understand.

* Each non-merge commit explicitly exists within the context of which
  section it is in, meaning that you don't have to spend some of your 50
  'subject' characters establishing that context.  'Test' would be a
  terrible commit subject in a flat history, but if the context has
  already been established as to what feature you are adding and testing,
  it could be all that needs to be said.  In the above example, `Parse
  'chosen pages' input like '5-8,11,12-15'` in the flat history can be
  just `Parse input like '5-8,11,12-15'` in the hierarchical history,
  because the section establishes the context of choosing which pages to
  print.

* A reviewer with reasonable knowledge of the codebase could look at
  just the 'big diffs' (e.g., from `Add paper selection UI` to `Add
  actual printing via PDF`).  Somebody who needed more detail on each
  step could read the individual commits within that section.  Somebody
  very familiar with the codebase might be happy to review just the
  'top-level' diff from `Release v0.8.0` to `Add printing facility`.


### Disadvantages

Unfortunately, creating and working with a tree-structured history in
`git` comes with some disadvantages:

* The `git` commands required to achieve the structure are not complex,
  but you do need quite a lot of `git merge --no-ff` invocations.

* Suppose you want to re-order two of the finest-level commits, for
  example swapping the order of the two commits within the `Add printer
  selection UI` section.  In a flat structure this is a simple
  interactive rebase, but an interactive rebase involving merge commits
  is non-trivial.
  [The manual](https://git-scm.com/docs/git-rebase) says under *Bugs*
  (with **emphasis** added): *The todo list presented by
  `--preserve-merges --interactive` does not represent the topology of
  the revision graph. Editing commits and rewording their commit
  messages should work fine, but* ***attempts to reorder commits tend to
  produce counterintuitive results.***

* When working with the invariant that 'the repo shall be in a
  compilable and all-tests-passing state at each commit', the notion
  needs refining such that only commits to the mainline need have this
  property.  For example, a bugfix branch might introduce a failing test
  to capture the errant behaviour, and then in a separate commit, fix
  the bug.  Only after the 'transaction' consisting of both commits has
  been applied to the codebase does the 'all tests pass' invariant
  hold.

* Cherry-picking is made more complex and
  fragile.  One either cherry-picks individual commits, which may
  violate the 'all test pass' invariant, or has to use the
  [`-m` flag to cherry-pick](https://git-scm.com/docs/git-cherry-pick)
  to specify the mainline parent, which loses the structure of the
  branch.

* Not all tools are friendly to the idea of a nested, tree-like history.
  The cherry-pick example is one case.  Some `git`-based systems present
  commit histories with the merge commits *subdued* (e.g., Bitbucket, as
  visible in the third screenshot for the
  ['Commit Graph' plugin](https://marketplace.atlassian.com/plugins/com.plugin.commitgraph.commitgraph/server/overview)),
  which is contrary to their use as section headings.  The hierarchical
  structure might not fit well with code-review systems; e.g., [Gerrit](https://www.gerritcodereview.com/)
  has the concept that the unit of code review is a single commit.  The
  Stack Exchange question
  ['Gerrit, git and reviewing whole branch'](http://programmers.stackexchange.com/questions/153094/gerrit-git-and-reviewing-whole-branch)
  illustrates this in the setting of a non-hierarchical topic branch
  containing multiple commits.

* One could even question whether this hierarchical structure is the
  best one --- see [further discussion](#is-serialized-optimal) below.


## Git-Dendrify

To make it easier to experiment with these ideas, I wanted a tool to
translate back and forth between the two representations.  The developer
can then work with a linear history, which is easy to re-arrange,
squash, etc., but then transform the history to its hierarchical form
for others to read.

Inherent in this approach is the assumption that it is completely
acceptable to re-write one's own local commit history; I don't think
this is too controversial.  There's also the thornier question of
whether it is acceptable to re-write published but 'read-only' history;
more on this [below](#ok-to-rewrite-history).

Therefore I developed the tool `git dendrify`, so called because it
turns the linear history into a tree.

It is easy to flatten the hierarchical version, but to turn the flat
history back into the hierarchical form, we need more information:
Where are the branch and merge points?  I considered various ways of
doing this, settling on adding short magic strings to the flat-history
commit 'subjects'.  (See also the
[discussion on a similar topic on the `topgit` issue tracker](https://github.com/greenrd/topgit/issues/38).)

### Structure labels

* Starting a commit message with `<s>` labels it as the first commit of a
  topic (sub-)branch.

* Starting a commit message with `</s>` labels it as a merge point; such
  a commit will typically have an empty diff to its parent, and a
  message whose body summarizes the work done in the 'contained'
  commits.

### Operation of the 'git dendrify' tool

The `git dendrify` tool then allows transformation back and forth
between the two structures:

```
                -------------------------[ linearize ]----------------------->

                <------------------------[ dendrify ]-------------------------

* Add printing facility                               * </s>Add printing facility [empty]
|\                                                    |
| * Add watermarks                                    * </s>Add watermarks [empty]
| |\                                                  |
| | * Allow choice of colour                          * Allow choice of colour
| | * Add known-good test cases                       * Add known-good test cases
| | * Emit watermark 'underneath' main output         * Emit watermark 'underneath' main output
| | * Drop-down for common watermarks                 * <s>Drop-down for common watermarks
| |/                                                  |
| * Add actual printing via PDF                       * </s>Add actual printing via PDF [empty]
| |\                                                  |
| | * Submit PDF to system print service              * Submit PDF to system print service
| | * Add known-good test cases                       * Add known-good test cases
| | * Generate PDF                                    * <s>Generate PDF
| |/                                                  |
| * Add paper selection UI                            * </s>Add paper selection UI [empty]
| |\                                                  |
| | * Sort choices alphabetically                     * Sort choices alphabetically
| | * Read paper size choices from database           * Read paper size choices from database
| | * Add selection box for paper sizes               * <s>Add selection box for paper sizes
| |/                                                  |
| * Add printer selection UI                          * </s>Add printer selection UI [empty]
| |\                                                  |
| | * Read printer list from system                   * Read printer list from system
| | * Add selection box for which printer             * <s>Add selection box for which printer
| |/                                                  |
| * Add page selection UI                             * </s>Add page selection UI [empty]
| |\                                                  |
| | * Parse input like '5-8,11,12-15'                 * Parse input like '5-8,11,12-15'
| | * Allow free-form CSV list of pages               * Allow free-form CSV list of pages
| | * Radio list: current, all, chosen                * <s>Radio list: current, all, chosen
| |/                                                  |
| * Start work on 'print' dialog [empty]              * <s>Start work on 'print' dialog [empty]
|/                                                    |
* Release v0.8.0                                      * Release v0.8.0
* Add spell-checker                                   * Add spell-checker
:                                                     :
:                                                     :
```

The magic labelling strings (`<s>` and `</s>`) are visible in the
linearized history shown in the right-hand column.


### Usage

After installation, a `git-dendrify` script is available, and can be
used as follows.

#### Convert linear to hierarchical: 'dendrify'

<pre>git dendrify dendrify <i>output-tree-like-branch base source-linear-branch</i></pre>

converts the linear history starting at (but excluding)
<code><i>base</i></code> up to (and including)
<code><i>source-linear-branch</i></code> into a hierarchical branch
called <code><i>output-tree-like-branch</i></code> starting from the same
<code><i>base</i></code>.  The magic `<s>` and `</s>` strings are used
to deduce the desired structure, and are stripped from the resulting
commit messages in <code><i>output-tree-like-branch</i></code>.

#### Convert linear to hierarchical: 'linearize'

<pre>git dendrify linearize <i>output-linear-branch base source-tree-like-branch</i></pre>

converts the hierarchical history starting at (but excluding)
<code><i>base</i></code> up to (and including)
<code><i>source-tree-like-branch</i></code> into a linear branch called
<code><i>output-linear-branch</i></code> starting from the same
<code><i>base</i></code>.  The magic `<s>` and `</s>` strings are
inserted to store the structure.


### Implementation note

The only thing that `git dendrify` needs to do is create new commit
objects with different parent lists; the trees referred to by the new
commits are the self-same trees as referred to by the 'source' commits.
This is in contrast to a full rebase which needs to create tree objects
via the creation and application of patches.  As a result, `git
dendrify` runs very quickly: In an example repo I used, it could
transform a history of c.70 commits in c.120ms.


### Open questions and problems

The usual `git` meaning of `A..B` excludes `A`, so it is a bit odd to
have the magic `<s>` label on the first branch commit.  The alternative
would be to label a commit as being both the inclusive end of a section
and also the exclusive start of the next section, but experiments with
that were not very compelling.

While working in the linear history, if you re-order commits within a
section and change which is the first one, you have to remember to move
the `<s>`.  The error does become apparent when you `dendrify`, and is
easily fixed, but it is an extra bit of friction.

The linear-structure commits which will become merge commits in the
hierarchical structure are empty; you have to remember to specify the
`--keep-empty` flag when you `git rebase --interactive`.  Also, the
experience of exporting to (`git format-patch`) and importing from (`git
am`) email-style patches is not very smooth when empty commits are
present.

It is slightly clunky to have to insert an empty commit at the start of
a nested topic branch.  (The `Start work on 'print' dialog` commit in
the dendrify/linearize example above.)  The tool could instead allow
multiple `<s>` at start, to signify depth of branch to start?

The 'dendrify dendrify' syntax is also slightly clunky.  Maybe grabbing
two `git` subcommands would be better?  Then the usage would be `git
dendrify output_tree_like_branch base source_linear_branch` and `git
linearize output_linear_branch base source_tree_like_branch`.


## Relation to standard 'pull request' workflow

In some ways the common pull-request-based workflow is similar to the
above, in that a mainline branch receives merges from multi-commit topic
branches.  The merge commit then serves as the 'section summary',
although often the summary is behind another layer of indirection: the
commit subject is, say,
[`Merge pull request #6014 from afvincent/afvincent-patch-issue-6009`](https://github.com/matplotlib/matplotlib/commit/59e0ab9a7b991d57acbe3d8121e6189ebe5e1041)
and one has to click through to the
[issue itself](https://github.com/matplotlib/matplotlib/issues/6009) to
discover what the branch does.

The difficulty that `git dendrify` aims to address is the local
maintenance of a history with nested branching structure.  The
review and acceptance of the branch into mainline could then be via the
standard pull-request mechanism.

As an aside, I find it mildly troubling that some important explanatory
information lives in the pull request rather than the repository itself.

There was a period when the Linux kernel was developed using the
proprietary [BitKeeper](https://www.bitkeeper.org/) product.  There was
disquiet at the fact that although the Linux kernel, frozen at any one
instant, was free software, a developer would have to use non-free
software to see the code's inter-release development history &mdash;
much of the information required to effectively study the system was
locked up.  (As it happens, BitKeeper was recently released under a
free-software licence.)

A similar situation has developed around GitHub &mdash; access to a
project's code history is freely available via `git clone`, but much
meta-data, in the form of discussions around issues and pull requests,
is owned (in some sense) by GitHub.


## <a name="is-serialized-optimal"></a>Is the 'serialized' structure optimal?

Even in the hierarchical structure, there is still an implicit
serialization of the work.  This is not necessarily an accurate
representation of the structure of the code and its development.  In
the word-processor example, the 'printer selection' work is likely to be
independent of the 'paper selection' work, and so the choice of
committing the 'printer selection' work first is arbitrary.  Perhaps an
even richer use of the `git` history would be better?  Taking some
liberties with the following two-dimensional commit graph, and
abbreviating commit messages a bit, we could have:

```
* Add printing facility
|\
| * Add actual printing via PDF
| |\
| | * Submit PDF to system print service
| | * Add known-good test cases
| | * Generate PDF
| |/
| * Gather user requirements for printing
| |\
| | `----------------------+------------------------+------------------------+
| |                        |                        |                        |
| * Watermarks             * Paper selection UI     * Printer selection UI   * Page selection UI
| |\                       |\                       |\                       |\
| | * Allow colour choice  | * Sort choices         | * System printer list  | * Parse comma-sep ranges
| | * Add test cases       | * Paper sizes from DB  | * 'Which printer' UI   | * Allow CSV
| | * Emit watermark       | * Add paper sizes UI   |/                       | * Radio buttons
| | * Common watermarks    |/                       |                        |/
| |/                       |                        |                        |
| +------------------------+------------------------+------------------------+
|/
* Release v0.8.0
* Add spell-checker
```

This illustrates the situation where the four UI strands required to let
the user describe what they want printed and how are independent of each
other.  However, the task of actually generating a PDF depends on all
four of those choices, and so the `Gather user requirements for
printing` commit correspondingly has four parents.

This is not possible within `git dendrify`, as a linear structure is
required.  This is partially to ease working with rebases, but also has
in mind the presentational angle of literate programming.  A human
reader *does* read serially, so perhaps there is no harm to arbitrarily
performing that serialization.

On the other hand, since a `git` history *can* represent the full
dependence structure of the pieces of the code, it would be a shame to
throw that away.  Within that approach,
[`git work`](https://github.com/jonseymour/gitwork) (see 'related work'
below) appears promising.  It would seem to allow truly independent
'sibling' branches.  One could rebase within a single topic, whose
history is truly linear, and then recursively rebase all dependent
topics on top of the new head afterwards.


## Related work

There are some interesting ideas being worked on in this area, and also
plenty of opportunities to explore further.

Other work in this general area of richer use of git's history
mechanisms include the following.  I do not have direct experience of
all of them, but they are addressing the same broad question of how to
make it easier to work with more complex branching structures.  Future
work could include reading about and experimenting with these ideas.

### TopGit

> TopGit aims to make handling of large amounts of interdependent topic
> branches easier.

* [TopGit on GitHub](https://github.com/greenrd/topgit)

### git work

> git work is designed to support workflows where a developer's
> workspace perpetually contains a mixture of work items at different
> levels of maturity.

* ['git work' on GitHub](https://github.com/jonseymour/gitwork)

### git-deps

> `git-deps` is a tool for performing automatic analysis of dependencies
> between commits in a git repository.

* ['git-deps' on GitHub](https://github.com/aspiers/git-deps)

### git-splice and git-transplant

Tools for copying or moving groups of commits from one branch to
another, arising in the context of `git-deps`:

* [Discussion archive](http://thread.gmane.org/gmane.comp.version-control.git/295755)

### Hamano's documentation on `git` maintenance

A detailed description of workflow and policies for developing `git`
itself, which has to handle large numbers of active topic branches.

* [howto/maintain-git.txt](https://github.com/git/git/blob/master/Documentation/howto/maintain-git.txt)

### git series

A structured history can perhaps be considered in its own right as an
object to be version-controlled.  The `git series` tool addresses this:

> git series tracks changes to a patch series over time.  git series
> also tracks a cover letter for the patch series, formats the series
> for email, and prepares pull requests.

* ['git series' on GitHub](https://github.com/git-series/git-series/)


---

## <a name="ok-to-rewrite-history"></a>Appendix: How acceptable is it to re-write history?

The above is based on the idea that in many circumstances it is
acceptable to re-write history.  Under this approach, we take the view
that the `git` history is a way of presenting your work, rather than an
immutable audit trail of changes to the codebase.  The appropriateness
of this view depends on the stage the code has reached in its journey
towards inclusion in the mainline:

### Local work

Do whatever you like.

### Published for code review

By this we mean a branch that is published (perhaps by being pushed to a
central repo), but with the intent that others will *look at* but not
*develop on* that branch.  I'm still thinking about the best way to
handle mutable history in this case, but have a couple of thoughts:

* Under the approach used by some mailing-list-driven projects (e.g.,
  `git` itself), a would-be contributor produces a 'patch series', gets
  feedback, and produces a new 'patch series'.  This repeats until the
  patch series is accepted or rejected.  The process appears quite like
  force-pushing each iteration of a topic branch to a view-only repo.

* Suppose a reviewer requests a minor clean-up to one commit of a
  branch: is the right thing to add a new commit effecting that
  clean-up, or to mutate the commit in question?  A third option is to
  add a new commit, which the reviewer can confirm implements the
  clean-up she had in mind, and then mutate the original commit after a
  suitable 'batch' of feedback?  There are arguments both ways.

### Merged into mainline / master / develop

Now it is pretty much set in stone, and changing the history can
inconvenience many people.


---

This README: Copyright 2016 Ben North; licensed under
[CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/)
