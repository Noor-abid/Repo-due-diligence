# Repo Due Diligence Agent

## Introduction

Buying, licensing, or investing in a codebase you didn't build is a high-stakes 
decision made on thin evidence. Today, that decision usually comes down to a 
skim of the README, a glance at the star count, and a few hours of a senior 
engineer's time — not a rigorous, repeatable assessment of what's actually 
inside the repo.

This project builds an agentic pipeline that performs the due diligence a 
careful human reviewer would do, but consistently, quickly, and with every 
finding traceable back to evidence: test results, git history, and dependency 
audits — not just a gut-feel score.

## Who Has This Problem

The intended user is a **buyer** — a company, investor, or acquirer — 
evaluating whether to purchase, license, or invest in a codebase they did not 
write. This includes:

- Acquirers doing technical due diligence before an M&A deal
- Investors assessing a startup's core technical asset
- Companies licensing or acquiring a private repository from another team

These buyers typically don't have deep familiarity with the codebase, and 
often aren't equipped to independently verify its quality before negotiating 
a price.

## The Bottleneck

A README or working demo tells a buyer almost nothing about the actual 
quality of the code underneath. To properly assess a repository, someone has 
to:

- Understand an unfamiliar codebase well enough to judge its architecture
- Actually run the build and test suite, not just read about them
- Audit dependencies for risk, staleness, or vulnerabilities
- Mine git and PR history for signals like bus factor, review depth, and 
  accumulated technical debt

This is slow — often days of a senior engineer's time — and inconsistent: 
two reviewers looking at the same evidence can reach different conclusions, 
because there's no shared, repeatable method for weighing the signals. 
Without that consistency, the resulting valuation depends on whoever happened 
to review it, rather than on the codebase itself.

## Why Solving It Is Valuable

A consistent, evidence-backed due diligence report turns a subjective, 
multi-day manual review into a fast, repeatable, and defensible process. For 
the buyer, this means:

- **Speed** — seconds/minutes instead of days to get a first-pass assessment
- **Consistency** — the same rubric applied the same way every time, 
  regardless of who's reviewing
- **Leverage** — a documented, evidence-backed report strengthens the buyer's 
  position in price negotiation
- **Risk reduction** — hidden issues (thin test coverage, single-maintainer 
  bus factor, unmaintained dependencies) surface before the deal closes, not 
  after

## The Solution

A multi-agent pipeline that produces a buyer-facing **Due Diligence Report** 
(not just a score) for any given repository:

| Agent             | Job                                                                                           |
| ----------------- | --------------------------------------------------------------------------------------------- |
| Code & Test Agent | Clones repo, runs build/tests, reports pass/fail + coverage                                   |
| History Agent     | Mines git log & PRs — bus factor, review depth, red flags                                     |
| Dependency Agent  | Audits packages for outdated/vulnerable/unmaintained deps                                     |
| Synthesis Agent   | Combines findings into a report, verifies claims, flags uncertainty, recommends human review   |

**Baseline:** One direct prompt — "here's the repo, rate quality 1-10 and 
explain why" — no tools, no repo access beyond the README.

## Improvement Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the full iteration-by-iteration story 
of how this solution evolved — from the baseline through each experiment, 
what we tried, what the evidence showed, and what we decided next.

## Evaluation

We evaluated the pipeline on 10 public repositories (requests, flask, django, 
express, lodash, moment, request, black, tqdm, flask-mail), pre-ranked by us 
using a shared rubric (test health, maintenance activity, dependency risk, 
architecture clarity). One repo, **flask-mail**, was included as an 
adversarial "trap": its GitHub activity/pulse showed no recent commits and 
effectively abandoned maintenance, despite looking like a normal, usable 
package on the surface.

The same 10 repos were run through both the baseline (single direct prompt, 
no tools) and the full agent pipeline (code/test, history, dependency, and 
synthesis agents with a verification step), using Gemini (`gemini-3.6-flash`) 
as the underlying model.

**Primary metric:** Spearman rank correlation between each system's ranking 
and our human ranking.

| Metric                                  | Baseline        | Agent Solution  | Change   |
|-------------------------------------------|-----------------|-----------------|----------|
| Spearman correlation to human ranking     | 0.83            | 0.37            | -0.46    |
| Avg runtime per repo                      | 3.5s            | 26.1s           | +22.6s   |
| API calls per repo                        | 1               | 5               | +4       |
| Cost per repo                             | $0 (free tier)  | $0 (free tier)  | — (both free tier; agent uses ~5x the API calls) |

**Note on cost:** both baseline and agent pipeline ran on Gemini's free tier, 
so dollar cost was $0 for this evaluation. On a paid tier, the agent solution 
would cost roughly 5x more per repo than the baseline — see Hot Take for why 
that cost is still worth it.

**Trap repo (flask-mail):** human rank was 9 out of 10 (near the bottom). 
The baseline scored it 9/10, fooled by surface-level polish (working README, 
plausible package description) with no way to check actual activity. The 
agent pipeline scored it lower (6-7/10) — its History Agent surfaced the lack 
of recent commits, producing a more evidence-grounded (if still imperfect) 
assessment.

## Project Structure
repo-due-diligence/
├── README.md <- this file
├── CHANGELOG.md <- improvement changelog
├── agents/ <- agent instructions/code
│ ├── code_test_agent.py
│ ├── history_agent.py
│ ├── dependency_agent.py
│ └── synthesis_agent.py
├── baseline/ <- single-prompt baseline
│ └── baseline.py
├── eval/ <- evaluation harness + rubric
│ ├── rubric.md
│ ├── repos.json <- the 10 test repos + human rankings
│ └── run_eval.py
├── data/ <- cached repo clones / analysis artifacts (gitignored, regenerated locally)
├── reports/ <- generated due-diligence reports (output)
└── trajectories/ <- saved agent run logs


## Reproduction

**Requirements:** Python 3.13, a virtual environment, and a Gemini API key 
set as an environment variable. Also requires `git` and network access to 
clone target repositories.

**Setup:**
```bash
git clone https://github.com/Noor-abid/Repo-due-diligence.git
cd repo-due-diligence
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
```

**Run the full evaluation (baseline + agent pipeline on all 10 repos):**
```bash
python eval/run_eval.py
```

**Expected output:** Per-repo baseline and agent scores printed to the 
terminal, a JSON summary with Spearman correlation and runtime, and full 
reports written to `reports/`.

**Approximate runtime:** ~3.5s per repo for baseline, ~26-39s per repo for 
the full agent pipeline (10 repos complete in a few minutes total).

**Known issue:** Gemini free-tier rate limits (20 requests/day on some 
models) can interrupt a full run mid-way — re-running resumes and completes 
the remaining repos.

## Hot Take / Insight

On the surface, our agent pipeline "lost" to the baseline on ranking 
correlation (0.37 vs 0.83) — but this number is misleading, and understanding 
why is the most important finding in this project.

The baseline achieved its higher correlation by scoring 8 of 10 repos a 9 or 
10 out of 10 — it wasn't discriminating between repos at all, just reflexively 
associating fame with quality. Because well-known repos also tend to rank 
well in a human's assessment, this lazy strategy accidentally correlates 
decently well without providing any real signal — a system that outputs 
almost the same score for nearly everything looks accurate on a 
rank-correlation metric purely because it never sticks its neck out.

Our agent pipeline, by contrast, produced varied, evidence-grounded scores 
(3 to 7 out of 10) by actually running tests, checking dependency staleness, 
and mining git history — and diverged from a fame-biased prior specifically 
where the evidence warranted it.

The deeper lesson: a single ranking-correlation number can reward a lazy, 
non-discriminating baseline over a genuinely more rigorous system. Anyone 
evaluating agent-based tools against simple baselines should look past 
aggregate correlation alone and inspect *why* the scores differ — a system 
that's "wrong" relative to a noisy human prior may still be extracting more 
real signal than one that's "right" by coincidence.

Second, smaller lesson: verification steps need to be paired with 
root-cause debugging, not just flagging. Our Synthesis Agent's verification 
pass correctly caught a false claim (requests wasn't "4 years inactive"), 
but catching the error alone wasn't enough — tracing it back to a specific 
git-timestamp parsing bug (tied to a known quirk in requests' own commit 
history) required engineering-level debugging beneath the LLM layer. After 
the fix, `verification_passed` returned `true` for all 10 repos in the final 
run — confirming the fix resolved the issue at its root, not just for the 
one repo where it was first noticed. AI-based fact-checking and tool-level 
debugging are complementary, not substitutes for each other.

**Third, smaller observation:** the flask-mail trap case (see Changelog)
shows the same pattern from a different angle — the baseline's high
correlation partly comes from trusting surface polish (modern tooling,
ecosystem branding) as a quality proxy, the same failure mode that made it
score famous repos a reflexive 9 or 10.
