# Story and hypothesis checklists

## INVEST, applied

| Letter | Question to ask of the story | Fails when |
|---|---|---|
| **I**ndependent | Can it be built and shipped without another story landing first? | "U3 needs U2's table" — then U2 is the story and U3 waits |
| **N**egotiable | Is it a promise of a conversation, or already a design? | the "I want" names a table, an endpoint or a class |
| **V**aluable | Can the customer say why they want it in their own words? | the value is "so the system is more flexible" |
| **E**stimable | Can you say whether it is a day or a month? | not without a spike — then name the spike |
| **S**mall | Will it become one spec of 3–12 scenarios? | it has "and" in the "I want", or three "done when"s |
| **T**estable | Is "done when" one observable outcome? | "done when it works well" |

## Hypothesis checklist

A hypothesis earns its row in the brief when all four hold:

1. **It can be false.** Write the falsifier first. If nothing observable would refute it, it is a
   value statement; move it to *Non-goals* or *Constraints*.
2. **The evidence has a source.** A log, a measurement on real data, a user's action, a
   published series. "We'll know" is not a source.
3. **A story or a spike tests it.** A hypothesis nothing tests will be believed by default,
   which is the opposite of the point.
4. **It is the customer's.** The agent may propose hypotheses; the customer owns which ones the
   product is betting on.

## Smells that mean you are designing, not brainstorming

- A file tree, a module name, a class or type name beyond the ubiquitous-language seed.
- A technology choice that is not a constraint ("we'll use Postgres").
- A sequence ("first build X, then Y") — order is the roadmap's job, and the customer's value
  order is the only order the brief carries.
- A "phase 2" with more detail than phase 1.
- More than one paragraph on any single story.
