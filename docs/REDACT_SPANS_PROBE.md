# redact-spans difficulty probe

Ten rollouts, two per language, at the same rung the cohorts use. This
is a go/no-go on the task. It is not a cohort result, it estimates no
pass rate, and it must never be pooled with one.

**10 of 10 passed. 0 of 10 failed at least one wrong-unit case. $0.052132 measured spend.**

## The pre-registered rule

Written into the probe JSON before the first paid call and not touched
since. It says text-redact v1.0 because it was written before the
family was given its own id; it is this family.

Admit text-redact v1.0 to a cohort only if it passes at most 7 of 10 AND at least 1 rollout fails a wrong-unit hidden case. Both conditions must hold. Passing 8 or more means the family saturates again. Passing few but never failing a wrong-unit case means the difficulty is coming from somewhere other than the hazard the family exists to test, which is a different task and needs a different justification.

Verdict: **do not admit**.

## By language

| Language | Passed | Runs failing a wrong-unit case |
|---|---:|---:|
| JavaScript | 2/2 | 0 |
| TypeScript | 2/2 | 0 |
| Python | 2/2 | 0 |
| Python (typed) | 2/2 | 0 |
| Go | 2/2 | 0 |

## Failing verifier cases

| Language | Failing cases |
|---|---|
| JavaScript | none |
| TypeScript | none |
| Python | none |
| Python (typed) | none |
| Go | none |

## What this rules out

The v0.9 diagnosis was that the instruction telegraphed the hazard: it
titled the task after the code point rule, gave the rule a paragraph of
its own ending in a sentence saying it does not matter how your language
indexes a string, and closed by naming the two hidden cases that catch a
wrong unit. This family removes all of that, states the unit once where
each field is defined, and adds three more hidden cases that a wrong unit
breaks. Changing the one code point conversion in the JavaScript
reference to text.split("") now fails seven of the thirteen cases
against four of twelve before.

It made no difference. Every language passed twice, and no run failed a
wrong-unit case. So the signposting was not what made v0.9 saturate. At
this rung the model counts code points correctly in all five languages
without being told to. Ten rollouts cannot put a number on how often it
would slip, but they are enough to say that hiding the hazard better is
not the lever. The mechanism is real and this model is not visibly
vulnerable to it, which is a fact about the model, not a fault in the
task.

That leaves two honest options and one dishonest one. The task can be
made larger, which is the lever the DeepSWE comparison already points
at: their median reference patch is 844 lines against 301 here, and
their median instruction is 15 lines against 69. Or the rung can move,
which contradicts the selection ladder and buys a result about a weaker
model. The dishonest option is to keep probing small variations until
one lands under the threshold, which is fitting the task to a target and
is not done here.

`redact-spans` stays in the tree, gate green, unadmitted. It costs
nothing to keep and it is the receipt for a claim worth having: the
code point hazard does not discriminate at this rung.
