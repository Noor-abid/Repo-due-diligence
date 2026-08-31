# Reproduction Guide

This walks through running the baseline, the agent pipeline, and the evaluation
from a clean environment. Total time: ~5 minutes. Total cost: **$0** (runs entirely
on Google AI Studio's free tier).

## 1. Requirements

- Python 3.11+
- `git` (used to clone the 10 target repos into `data/`)
- Network access to GitHub and to `generativelanguage.googleapis.com`
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
  (no credit card required)

## 2. Setup

```bash
git clone https://github.com/Noor-abid/Repo-due-diligence.git
cd Repo-due-diligence

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 3. Configure your API key

```bash
export GEMINI_API_KEY=your-key-here      # Windows: set GEMINI_API_KEY=your-key-here
```

## 4. Run the baseline alone (optional, ~4s per repo)

```bash
python baseline/baseline.py https://github.com/psf/requests requests
```

Expected output: a JSON object with `quality_score`, `reasoning`, and
`recommendation`, printed to stdout.

## 5. Run a single agent alone (optional)

```bash
python agents/history_agent.py https://github.com/psf/requests requests
```

Expected output: JSON findings (commit stats, bus factor, red flags). A
matching trajectory file is written to `trajectories/requests__history_agent.json`.
The other agents (`code_test_agent.py`, `dependency_agent.py`) follow the
same `<script> <repo_url> <repo_name>` usage; `synthesis_agent.py` is meant
to be called from the full pipeline, not standalone, since it needs all
three agents' findings as input.

## 6. Run the full evaluation (baseline + agent pipeline + comparison, ~5 min)

```bash
python eval/run_eval.py
```

What this does:
- Clones all 10 repos listed in `eval/repos.json` into `data/` (shallow clones,
  ~200 commits of history each)
- Runs the single-prompt baseline on each repo
- Runs the full 4-agent pipeline (Code & Test → History → Dependency → Synthesis
  with verification) on each repo
- Computes Spearman rank correlation between each method's scores and the
  human ranking in `eval/repos.json`
- Writes one report per repo per method to `reports/`, plus `reports/eval_summary.json`

Expected console output ends with a `=== SUMMARY ===` block matching the
structure of `reports/eval_summary.json` — approximately:
- `baseline_spearman_vs_human`: ~0.83
- `agent_spearman_vs_human`: ~0.37 (see the Hot Take in `CHANGELOG.md` for why
  a *lower* correlation here is actually the more interesting finding)
- `agent_avg_runtime_sec`: ~26s per repo vs. ~3.5s for the baseline

## 7. What to look at afterward

| File | What it shows |
|---|---|
| `reports/<repo>_agent.json` | Final buyer-facing report per repo |
| `reports/eval_summary.json` | The full baseline-vs-agent comparison table |
| `trajectories/<repo>__<agent>.json` | Step-by-step trajectory for each agent run |
| `baseline_vs_agent_chart.png` | Visual comparison of scores per repo |
| `bug_fix_terminal.png` | Before/after evidence for the timestamp bug fix |
| `CHANGELOG.md` | The full iteration story, tied to evidence |

## 8. Costs and limits

- Gemini `flash-lite` free tier is used throughout — no billing required.
- The free tier has per-minute rate limits; `run_eval.py` sleeps 5s between
  repos and `common.py` auto-retries once on a 429 with a 20s backoff, so a
  full run should complete without manual intervention.
- Each of the 10 repos is shallow-cloned (`--depth 200`) into `data/`; this
  folder is safe to delete and will be re-created/refreshed on the next run.

