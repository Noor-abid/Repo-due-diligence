# Human Ranking Rubric

Use this to rank your 10 chosen repos 1 (best) through 10 (worst) *before*
running the baseline or agent pipeline, so your ranking isn't biased by
their output. Spend ~10-15 min per repo.

Score each dimension 1-5, then sum (max 20) to help you order repos —
the final ranking is still your judgment call, the rubric just keeps it
consistent across repos.

| Dimension | 1 (poor) | 5 (excellent) |
|---|---|---|
| Test health | No tests, or tests fail | Comprehensive, passing tests, good coverage |
| Maintenance activity | No commits in 1+ years, no CI | Regular commits, active CI, recent releases |
| Dependency risk | Many outdated/vulnerable deps | Deps current, no known CVEs |
| Architecture & bus factor | One contributor, tangled structure | Multiple contributors, clear module boundaries |

## Instructions
1. Clone each repo yourself, skim the code for 10-15 min.
2. Score the 4 dimensions above.
3. Rank all 10 repos 1-10 based on total score (break ties using your judgment).
4. Record the ranking in `repos.json` under `human_rank` BEFORE looking at
   what the baseline or agent produces — this keeps your ground truth honest.
5. Pick one repo that looks clean on the surface (good README, decent
   stars) but scores poorly once you dig in — mark it as `"is_trap": true`.
   This is your "challenging case" for the writeup.
