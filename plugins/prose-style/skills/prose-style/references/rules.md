# Prose Style Rules in Full

Each rule has a bad example, a good example, and the reason it exists. The revise skill uses
this file as its rule set, and its audit cites these identifiers.

Sources: W. Strunk Jr., *The Elements of Style* (1918, public domain); G. Orwell, "Politics and
the English Language" (1946); S. Pinker, *The Sense of Style* (2014); G. Gopen and J. Swan,
"The Science of Scientific Writing", *American Scientist* (1990). Several rules in groups C and
D adapt the field-observed rules of
[agent-style](https://github.com/yzhao062/agent-style) by Yue Zhao (CC BY 4.0).

---

## A. Reader and Purpose

### R1 Name the Reader

**Bad:** The SSG falls back to the CAS when the LRU misses.
**Good:** The static site generator reads from the content store when a page is not in its
in-memory cache.

**Why:** Pinker calls this the curse of knowledge: once you know something, it is hard to
imagine not knowing it. Writing for a named reader (a new team member, a reviewer, an on-call
engineer at 3 a.m.) tells you which terms need defining and which steps you can skip.

### R2 Lead with the Point

**Bad:** We looked at several options for the cache. Redis was considered, as was an in-process
map. After some benchmarking, and taking operational cost into account, we went with the map.
**Good:** We use an in-process map for the cache. It matched Redis on our benchmarks and needs
no extra service to run.

**Why:** Readers skim. Many stop after the first sentence, and in a commit log or PR list the
first line may be all they see.

---

## B. Sentences

### R3 Active Voice

**Bad:** The configuration is validated and an error is returned if a field is missing.
**Good:** The loader validates the configuration and returns an error if a field is missing.

**Why:** The passive hides who acts. In technical writing the actor is usually the point: which
component validates, which person approves. The passive is right when the actor is unknown or
does not matter ("the file was deleted in 2023").

### R4 Concrete Words

**Bad:** Various factors affect performance in certain scenarios.
**Good:** Queries slow down when the result set exceeds the page cache, which happens on reports
covering more than a year.

**Why:** Abstract words make the reader do the work of guessing what you meant. If you cannot
replace "factors" with the factors, you do not yet know what you are claiming.

### R5 Cut Needless Words

| Instead of | Write |
|---|---|
| in order to | to |
| due to the fact that | because |
| is able to | can |
| at this point in time | now |
| in the event that | if |
| a number of | some, or the number |
| the question as to whether | whether |
| it should be noted that | (delete) |
| very, really, quite, simply, just, basically, actually | (usually delete) |

**Bad:** In order to ensure that the build is able to run, it is necessary to simply install
the dependencies first.
**Good:** Install the dependencies before you build.

**Why:** Strunk: "A sentence should contain no unnecessary words, a paragraph no unnecessary
sentences." Each needless word dilutes the ones that matter.

### R6 Positive Form

**Bad:** The service did not respond in a timely manner. It is not uncommon for this to happen.
**Good:** The service was slow. This happens often.

**Bad (staged contrast):** This is not just a linter, it is a philosophy of code.
**Good:** The linter enforces the team's naming rules.

**Why:** Negatives make the reader hold the opposite in mind and then flip it. Staged contrasts
("not X, but Y"; "it is not about X, it is about Y") invent an opponent to argue against. They
are among the strongest signs of machine-written text.

### R7 Plain Words

**Bad:** We leverage a robust methodology to facilitate the utilisation of the functionality.
**Good:** We use a tested method to make the feature easier to use.

**Why:** Orwell's rule 2: never use a long word where a short one will do. Inflated words sound
like they mean more but usually mean less. See `word-list.md` for swaps.

### R8 No Dead Metaphors

**Bad:** This release is a game-changer that unlocks a seamless experience and pushes the
boundaries of what is possible.
**Good:** This release halves start-up time and removes the separate login step.

**Why:** Orwell's rule 1: never use a figure of speech you are used to seeing in print. A worn
metaphor carries no image, only the sound of a claim.

### R9 Keep Related Words Together

**Bad:** The scheduler, which was written in 2019 by a contractor who has since left and which
nobody has touched because the tests are flaky, retries failed jobs.
**Good:** The scheduler retries failed jobs. A contractor wrote it in 2019, and nobody has
touched it since, because its tests are flaky.

**Why:** Gopen and Swan: readers expect the verb soon after the subject. Until it arrives they
hold the subject in memory, and a long gap loses them.

### R10 Stress Position

**Bad:** A race condition between the two writers is what the bug turned out to be caused by.
**Good:** The bug turned out to be a race condition between the two writers.

**Why:** Gopen and Swan: readers give the most weight to the end of a sentence. Put known
context first and the new information last.

### R11 Sentence Length

**Bad:** The migration runs in three phases, the first of which copies the data into the new
schema while the old one stays live, after which a verification step compares row counts and
checksums, and finally the switch flips the read path, which can be rolled back within an hour.
**Good:** The migration runs in three phases. First it copies the data into the new schema while
the old one stays live. Then it compares row counts and checksums. Finally it switches the read
path. You can roll the switch back within an hour.

**Why:** Comprehension drops sharply past about 30 words. Uniform length is a problem too: a
paragraph of identical medium sentences drones. Vary the length.

### R12 Parallel Form

**Bad:** The command validates input, the cache is refreshed, and then sending a notification.
**Good:** The command validates input, refreshes the cache, and sends a notification.

**Why:** Strunk: express co-ordinate ideas in similar form. A change of shape tells the reader
that something has changed in kind.

---

## C. Paragraphs and Structure

### R13 One Topic per Paragraph

**Why:** Strunk: make the paragraph the unit of composition. The first sentence states the
topic; the rest develops it. A reader skimming the first sentences of each paragraph should get
the outline of the argument.

### R14 Prose for Reasoning, Lists for Items

**Bad:**
- Caching improves speed
- It also adds complexity
- Therefore we should measure first

**Good:** Caching would make reads faster, but it adds invalidation logic we would have to
maintain. We should measure the read path before deciding.

**Why:** Bullets remove the words ("but", "so", "because") that carry reasoning. Language
models reach for bullets and for groups of exactly three by default. Use a list when the items
are truly separate and the reader will scan them: steps, options, file names.

### R15 No Summary Closers

**Bad:** The guard rejects requests without a token, so unauthenticated callers never reach the
handler. Overall, this ensures that the endpoint remains secure.
**Good:** The guard rejects requests without a token, so unauthenticated callers never reach the
handler.

**Why:** The closer repeats what the reader just read and often inflates it ("remains secure"
claims more than the paragraph showed).

### R16 No Stock Transitions

**Bad:** The parser is fast. Additionally, it is small. Furthermore, it has no dependencies.
**Good:** The parser is fast and small, and it has no dependencies.

**Why:** Stock transitions announce a connection without stating it. If the link is
"also", combine the sentences; if it is "because" or "but", say so.

### R17 Vary Openings

**Bad:** The tool reads the file. The tool then parses it. The tool writes the result.
**Good:** The tool reads the file, parses it, and writes the result.

**Why:** Repeated openings sound mechanical and usually mean the sentences should be merged.

---

## D. Claims and Terms

### R18 Calibrate Claims

| Evidence | Verb |
|---|---|
| A proof, or a test that fails without the change | shows, proves, guarantees |
| Measurements on representative data | indicates, measured |
| A single run, an anecdote, a plausible argument | suggests, may |
| Nothing yet | we expect, we assume, untested |

**Bad:** This change ensures the service never drops messages.
**Good:** With this change, the service dropped no messages in a 24-hour soak test.

**Why:** An overstated claim is a defect that readers act on. It is the prose version of a
protection claim no test supports (see pr-validation, Analysis 4).

### R19 No Invented Facts

**Bad:** This approach is used by over 80% of Fortune 500 companies [1].
**Good:** (If you have no source) Several large companies use this approach; TODO: cite.

**Why:** A plausible invented fact is worse than a gap, because nobody goes looking for it.
When revising, never add support that the source does not contain.

### R20 One Term per Concept

**Bad:** The worker picks up a job. Once the task finishes, the processor marks the item done.
**Good:** The worker picks up a job. Once the job finishes, the worker marks it done.

**Why:** Varying synonyms to avoid repetition is a school habit. In technical text, each new
word suggests a new thing. This is the ubiquitous language of domain-driven design, applied to
prose.

### R21 No Padding

**Bad:** Great question! Let me walk you through it. It is important to understand that the
cache may potentially be stale. I hope this helps; let me know if you have any other questions!
**Good:** The cache can be stale for up to five minutes after a write.

**Why:** Padding costs the reader time and tells them nothing. Stacked hedges ("may
potentially", "could possibly", "somewhat likely") blur the one hedge that is warranted.

---

## E. House Conventions

### H1 British Spelling

| American | British |
|---|---|
| behavior, color, favor | behaviour, colour, favour |
| organize, recognize, normalize | organise, recognise, normalise |
| modeling, labeled, canceled | modelling, labelled, cancelled |
| center, meter (length) | centre, metre |
| catalog, dialog (prose) | catalogue, dialogue |
| defense, license (noun) | defence, licence (noun) |
| practice (verb) | practise (verb) |

Exceptions: code identifiers, API names, CLI flags, product names, and quotations keep their
original spelling (`normalize()`, `Color` enum, "dialog box" when quoting a UI). "Program" is
correct in British English for software.

### H2 Title Case Headings

Capitalise nouns, pronouns, verbs, adjectives, adverbs, and subordinating conjunctions. Keep
articles (a, an, the), coordinating conjunctions (and, but, or, nor, for, so, yet), and
prepositions of four letters or fewer (as, at, by, for, from, in, into, of, on, to, with) in
lower case, unless they come first or last. Capitalise both parts of a hyphenated compound
("Test-First Development"). Code in a heading keeps its own case.

**Bad:** ## What this skill does
**Good:** ## What This Skill Does

### H3 No Contractions

**Bad:** It's fast, but it doesn't scale and you can't shard it.
**Good:** It is fast, but it does not scale and you cannot shard it.

### H4 Em Dashes, Very Sparingly

**Bad:** The guard — which runs first — rejects bad input — before the handler sees it.
**Good:** The guard runs first and rejects bad input before the handler sees it.

**Bad (list label):** **Purity** — every changed function is classified.
**Good:** **Purity:** every changed function is classified.

**Allowed:** We tested every path but one — the one that failed in production.

**Why:** Dashes used as all-purpose punctuation are a strong sign of machine-written text, and
they hide the relationship between clauses that a comma, colon, or semicolon would state. Keep
the em dash for one deliberate interruption, at most once in a paragraph. When you do use one,
match the spacing the document already uses.

### H5 Serial Comma

**Bad:** It supports Claude Code, Cursor and Codex.
**Good:** It supports Claude Code, Cursor, and Codex.
