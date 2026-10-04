# Revision Contract

These invariants bind every edit the revise skill makes. They are adapted from the polish
invariants of agent-style's `style-review` skill
([agent-style](https://github.com/yzhao062/agent-style), CC BY 4.0). If an edit cannot satisfy
all of them, leave the passage unchanged and report the finding as open.

## 1. No New Facts

Do not add metrics, numbers, dates, names, citations, references, links, code behaviour, or
claims that are not already in the source. To resolve an overstated claim (R18), weaken the
verb; never strengthen the evidence. An unsupported claim (R19) stays flagged for the author.

## 2. Preserve Structure

Keep these exactly as they are:

- frontmatter, byte for byte,
- code fences and their contents, and inline code spans,
- link syntax and link targets, image references, and footnotes,
- table layout (cell text may change, columns may not),
- heading levels and anchors other documents link to,
- list nesting and numbering style,
- the trailing newline convention.

The exception is a finding about the structure itself. Example: R14 flags a bullet list that is
really an argument, so the edit turns it into a paragraph. When a heading's text changes under
H2, check whether the change alters a link anchor (`#what-this-skill-does` does not change, since
GitHub anchors are lower case; a reworded heading does). If it does, update the links in the same
file, or leave the heading's wording alone and fix only its case.

## 3. Preserve Meaning

A revision resolves only the listed findings. Do not reorder sections, merge or split
paragraphs, or condense prose beyond what the flagged rule needs. Keep technical terms, even
where a plainer synonym exists, if the term is the document's defined vocabulary (R20 outranks
R7).

## 4. Preserve the Length Budget

Revisions may shorten text. They must not make it longer, except where H3 expands a
contraction or R6 rewrites a negative as a slightly longer positive.

## 5. Preserve Voice Where It Is Deliberate

A first-person team voice ("we build…"), a manifesto tone in an introduction, or a quoted maxim
is the author's choice. Revise mechanics (spelling, dashes, transitions) inside it, but do not
flatten its register.

## 6. When No Revision Is Possible

If a passage cannot satisfy the rule without breaking an invariant, leave it unchanged and list
it in the final report as open, with the reason.
