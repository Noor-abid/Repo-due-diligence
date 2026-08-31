# Repo Due Diligence Agent

## The Problem

**Who has this problem:** A buyer (company, investor, or acquirer) evaluating
whether to purchase, license, or invest in a codebase they didn't write.

**The bottleneck:** Manual code due diligence takes a senior engineer days,
requires reading unfamiliar code, running tests/builds, auditing dependencies,
and mining git/PR history for risk signals (bus factor, review quality,
technical debt). Different reviewers often reach inconsistent conclusions,
which directly affects negotiated price and deal risk.

**Why it's valuable to solve:** A consistent, evidence-backed report turns a
subjective days-long manual review into a fast, repeatable, defensible
process — giving the buyer real leverage in negotiation.

## The Solution

A multi-agent pipeline that produces a buyer-facing **Due Diligence Report**
(not just a score) for any given repository:

| Agent | Job |
|---|---|
| Code & Test Agent | Clones repo, runs build/tests, reports pass/fail + coverage |
| History Agent | Mines git log & PRs — bus factor, review depth, red flags |
| Dependency Agent | Audits packages for outdated/vulnerable/unmaintained deps |
| Synthesis Agent | Combines findings into a report, flags uncertainty, recommends human review of specific items |

**Baseline:** One direct prompt — "here's the repo, rate quality 1-10 and
explain why" — no tools, no repo access beyond README.

## Evaluation

- 10 public repos, pre-ranked by us using a simple rubric (test health,
  maintenance activity, dependency risk, architecture clarity)
- Same 10 repos run through baseline and agent system
- Primary metric: ranking correlation with our human ranking (e.g. Spearman)
- Secondary: time & cost per repo
- One adversarial "trap" repo included — looks clean, has hidden risk

## Project Structure

```
repo-due-diligence/
├── README.md                  <- this file
├── CHANGELOG.md                <- improvement changelog (required deliverable)
├── agents/                     <- agent instructions/code
│   ├── code_test_agent.py
│   ├── history_agent.py
│   ├── dependency_agent.py
│   └── synthesis_agent.py
├── baseline/                   <- single-prompt baseline
│   └── baseline.py
├── eval/                       <- evaluation harness + rubric
│   ├── rubric.md
│   ├── repos.json              <- the 10 test repos + human rankings
│   └── run_eval.py
├── data/                       <- cached repo clones / analysis artifacts
├── reports/                    <- generated due-diligence reports (output)
└── trajectories/               <- saved agent run logs (required deliverable)
```

## Reproduction

See `eval/run_eval.py` for exact commands. Requires: Python 3.11+,
`ANTHROPIC_API_KEY`, git, and network access to clone target repos.

## Hot Take

_(fill in after running experiments — e.g. "naive baselines over-trust
README polish and star count as quality proxies; real risk lives in PR
review depth and bus factor, which they completely miss.")_
