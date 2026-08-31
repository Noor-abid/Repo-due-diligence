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

- **Speed** — hours instead of days to get a first-pass assessment
- **Consistency** — the same rubric applied the same way every time, 
  regardless of who's reviewing
- **Leverage** — a documented, evidence-backed report strengthens the buyer's 
  position in price negotiation
- **Risk reduction** — hidden issues (thin test coverage, single-maintainer 
  bus factor, unmaintained dependencies) surface before the deal closes, not 
  after.
