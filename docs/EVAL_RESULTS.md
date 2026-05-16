# SAFE Detection — Eval Results

Living document. Append new runs as they happen. Latest results at top.

---

## What this document is

A record of how the SAFE detection pipeline performs against documented test cases. Each entry captures: what model and prompt version were tested, which test cases were run, what numbers came out, and what those numbers mean.

This document is the source-of-truth for "how good is the detector right now?" When someone (including future-you) asks that question, the answer is whatever is at the top of this file.

---

## Important methodological note: single-run variance

LLM output is non-deterministic. The same prompt sent to the same model at the same temperature **does not produce identical outputs run-to-run.** This was confirmed directly tonight by running the eval twice against an unchanged codebase and observing different per-test numbers (see Run 1 vs Run 2 below).

What this means for interpreting the numbers in this document:
- **Single-run numbers are samples, not measurements.** A reported "category recall: 1.00" means "in this one run, recall was 1.00." Another run might produce 0.83 or 0.92.
- **Stable findings across multiple runs are more trustworthy than precise per-run numbers.** "Test 3 consistently misses `personal_identifiers`" (confirmed in both runs) is a stronger statement than "mean risk gap was 0.67" (one sample).
- **Future improvement work should report mean ± variance over 3-5 runs**, not single-run numbers. This is not done in the current scaffold — it's a known limitation, tracked as a follow-up.

The scaffold ships single-run numbers because it's the scaffold, not the suite. Multi-run averaging is later sprint work.

---

## What the eval measures

The eval harness runs each test case from `docs/PROMPT_DESIGN.md` (section 6) through `analyse_prompt()` and computes two metrics per case.

### Metric 1: Category recall

**The question it answers:** Of the categories the test expected the detector to flag, how many did it actually flag?

**How it's computed:** `len(expected_categories ∩ detected_categories) / len(expected_categories)`

**Example:**
- Test expects: `{personal_identifiers, client_account_information}`
- Detector flagged: `{personal_identifiers, client_account_information, performance_and_employment_status}`
- Recall = 2 / 2 = **1.00**

**Notes:**
- Extra categories the detector flags do NOT reduce recall. They reduce *precision*, which we don't measure yet.
- Recall of 1.00 means "the detector caught every category the test expected." It does not mean "the detector is perfect" — it could still be flagging too many things, or under-counting items within the right categories.
- For tests where only one category is expected, recall reduces to a binary yes/no signal. Test 2 has this property. For richer signal on those tests, item-count recall would be needed — deferred to a later sprint.

### Metric 2: Risk score gap

**The question it answers:** How far off is the detector's risk rating from the test's expected risk rating?

**How it's computed:** `abs(expected_risk_score - detected_risk_score)`

**Example:**
- Test expects: risk 9 out of 10
- Detector returned: risk 8 out of 10
- Gap = **1**

**Notes:**
- Smaller is better. 0 means exact match.
- This metric varies more run-to-run than category recall does, based on the two runs we have. The variance is real and limits how much can be read into any single gap number.
- This metric does not capture *direction* (under vs over-rating). In both runs so far, gaps have been the detector rating *lower* than ground truth, not higher.

### What the eval does NOT yet measure

The scaffold is deliberately minimal. Future sprints can add:
- **Item-count recall:** "Did the detector find 8 items where the test expected 8?" Requires fuzzy excerpt matching.
- **Precision:** "Of the categories the detector flagged, how many were in the expected set?"
- **Excerpt accuracy:** "Did the detector quote the right text spans for each flagged item?"
- **Combinatorial notes presence and quality.**
- **Multi-run statistics (mean, variance, percentiles)** to handle LLM non-determinism properly.
- **Latency tracking across runs.**

These are intentionally out of scope until the 3-case scaffold is proven to ship clean numbers run-over-run.

---

## Run 2 — May 16, 2026 14:19 (auto-loader added)

**Model:** gpt-4.1-mini
**Prompt version:** `DETECTION_PROMPT_V1_2`
**Cases run:** Tests 1, 2, 3 from `docs/PROMPT_DESIGN.md`
**Harness:** `scripts/run_evals.py` with `.env.local` auto-loader
**Why this run:** Validate the auto-loader works from a fresh terminal without manual `export`. Side effect: produced different numbers from Run 1 with no code change — see Stable findings section below.

### Headline numbers

| Metric | Value |
|---|---|
| Mean category recall | **0.83** |
| Mean risk score gap | **0.67** |
| Cases run successfully | 3 / 3 |

### Per-test results

| Test | Recall | Risk gap | Items flagged | Detected categories |
|---|---|---|---|---|
| Test 1 — Wealth Management | **1.00** | **0** | 5 | client_account_information, internal_financial_metrics, personal_identifiers, trade_and_transaction_data |
| Test 2 — M&A Advisory | **1.00** | 1 | 5 | deal_and_corporate_finance_information, internal_financial_metrics, regulatory_and_compliance_matters |
| Test 3 — Compensation | **0.50** | 1 | 3 | compensation_data, performance_and_employment_status |

### What's different from Run 1

- Test 1 risk gap: 1 → **0** (detector returned 9, matching expected 9)
- Test 1 detected categories: 5 → 4 (lost `performance_and_employment_status`)
- Test 2 items flagged: 6 → 5 (lost one item)
- Mean risk gap: 1.00 → 0.67

### What's the same as Run 1

- Category recall on all three tests: **identical** (1.00, 1.00, 0.50)
- Test 3 still misses `personal_identifiers` — confirmed across both runs
- Test 2's extra categories (`internal_financial_metrics`, `regulatory_and_compliance_matters`) identical to Run 1
- Test 3's exact category set identical to Run 1

---

## Run 1 — May 16, 2026 13:53 (initial baseline)

**Model:** gpt-4.1-mini
**Prompt version:** `DETECTION_PROMPT_V1_2`
**Cases run:** Tests 1, 2, 3 from `docs/PROMPT_DESIGN.md`
**Harness:** `scripts/run_evals.py` (pre-auto-loader; required manual `export OPENAI_API_KEY`)
**Why this run:** First execution of the eval scaffold. Establish baseline.

### Headline numbers

| Metric | Value |
|---|---|
| Mean category recall | **0.83** |
| Mean risk score gap | **1.00** |
| Cases run successfully | 3 / 3 |

### Per-test results

| Test | Recall | Risk gap | Items flagged | Detected categories |
|---|---|---|---|---|
| Test 1 — Wealth Management | **1.00** | 1 | 5 | client_account_information, internal_financial_metrics, performance_and_employment_status, personal_identifiers, trade_and_transaction_data |
| Test 2 — M&A Advisory | **1.00** | 1 | 6 | deal_and_corporate_finance_information, internal_financial_metrics, regulatory_and_compliance_matters |
| Test 3 — Compensation | **0.50** | 1 | 3 | compensation_data, performance_and_employment_status |

---

## Stable findings across both runs

The numbers above varied between runs. These observations did not.

### Finding 1: Test 3 misses `personal_identifiers` consistently

In both runs, the detector failed to flag `personal_identifiers` despite the prompt containing two named employees (Rohan Iyer, Meera Krishnan) and one identifiable-by-context senior hire ("our new senior hire from Morgan Stanley"). It appears the detector collapses name+role flags into `performance_and_employment_status` rather than treating names themselves as personal identifiers.

**Why this matters:**
- Under DPDP Act 2023, the names of identifiable individuals are personal data. A detector that misses this category produces an incomplete warning to the user about what categories of regulated data they are about to expose.
- This is the kind of weakness an eval is supposed to surface. Without measurement, the gap was invisible. With measurement, it's a reproducible, actionable finding.
- The two-run confirmation makes this finding meaningfully stronger than a single-run observation would be. It is unlikely to be sampling noise.

**Possible remediation paths (NOT tonight):**
- Refine `DETECTION_PROMPT_V1_2` to be more explicit about classification rules for name+role combinations.
- Test with Claude (when Anthropic API access is available) to disambiguate prompt-engineering issue vs model-quality issue.
- Either remediation path requires re-running the eval after the change to verify improvement. The eval scaffold supports this directly.

### Finding 2: Detector performs well on financial/deal-shaped prompts, weaker on people-shaped prompts

Tests 1 (wealth management) and 2 (M&A) both consistently achieve recall 1.00. Test 3 (compensation, the only test with significant people-content as the central risk) consistently achieves only 0.50. This pattern is consistent with Finding 1 but is its own observation: the failure mode is specifically around personal-identifier detection in human-context prompts.

### Finding 3: Risk scores trend low

In both runs, every test's risk score came in at or below ground truth, never above. This may reflect calibration: the detector appears to be slightly conservative on severity ratings. Two runs is not enough data to claim this with confidence, but the direction is consistent so far.

### Finding 4: Over-flagging of related categories is consistent

Both runs flag `internal_financial_metrics` on both Tests 1 and 2. Both runs flag `regulatory_and_compliance_matters` on Test 2. These are defensible additions (EV/EBITDA *is* an internal financial metric; pre-announcement deal data *is* a regulatory matter), but they reduce precision. Precision will become measurable when a precision metric is added in a later sprint.

---

## What we are NOT doing with these results

- **Not changing test cases to make Test 3 score better.** The 0.50 recall is the baseline. Modifying tests to fit detector behavior would destroy the measurement.
- **Not switching models tonight to chase a better number.** Anthropic API access is a future sprint.
- **Not adjusting `DETECTION_PROMPT_V1_2` tonight.** Prompt-refinement is its own task with its own discipline, tracked as a follow-up.
- **Not over-claiming what the scaffold shows.** Single-run numbers are samples. The headline claim of this scaffold is "we now have a measurement that surfaces real findings (Finding 1)," not "we've established a definitive baseline number."

---

## How tonight's runs were actually produced

Recorded honestly because the environment friction was non-trivial and future-you (or a collaborator) will hit similar issues.

Before Run 1 succeeded:
1. First attempt failed: `structlog` was not installed in the local Python environment outside vercel's runtime. Fixed by creating a virtualenv and `pip install -r api/requirements.txt`.
2. Second attempt failed: `OPENAI_API_KEY` was not exported to the shell. Vercel auto-loads `.env.local`; bare `python3` does not.
3. Third attempt failed: the inline `export OPENAI_API_KEY=$(grep ... | cut ...)` extraction included the literal double quotes wrapping the value in `.env.local`. The detector got a quoted string and OpenAI rejected it as invalid (401).
4. Fourth attempt succeeded after `| tr -d '"'` was added to strip the quotes.
5. The OpenAI key was exposed in chat during diagnostic. **Rotation pending.**

Before Run 2:
- Added `.env.local` auto-loader to `scripts/run_evals.py` so the script reads and loads `OPENAI_API_KEY` directly from the file with proper quote stripping.
- Verified the loader works from a fresh terminal: `cd ...; source .venv/bin/activate; python3 scripts/run_evals.py` produced results without needing any `export` step.

---

## How to run the eval yourself

```bash
cd /Users/manan/Desktop/PerniciaAI/TrainingTopics/ResponsibleAI/tool

# One-time setup (if not already done):
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt

# Every run:
source .venv/bin/activate   # if not already in venv
python3 scripts/run_evals.py
```

Output prints to stdout. The harness file is `scripts/run_evals.py`; the test case data lives in `scripts/eval_cases.py`. `.env.local` is loaded automatically.

**Adding new test cases:** edit `scripts/eval_cases.py` and append a new dict to the `EVAL_CASES` list. The dict needs `id`, `name`, `prompt`, `expected_categories` (a set of strings matching detection category names), and `expected_risk_score` (an int 1-10).

**Cost per run:** approximately 3 OpenAI API calls at ~1300 tokens each → roughly $0.02-0.05 per run at current pricing.

---

## Follow-up tasks

- [ ] **Rotate the OpenAI API key** (exposed in chat May 16). Highest priority.
- [ ] Add `.venv/` to `.gitignore` if not already present.
- [ ] Expand test cases from 3 to 20+ (Day 4-5 of Sprint 1 per the sprint plan).
- [ ] Add multi-run averaging: run each case N=5 times, report mean ± std for each metric. Addresses single-run variance directly.
- [ ] Add additional metrics (item-count recall, precision) once 20-case suite is stable.
- [ ] Wire `python scripts/run_evals.py` into GitHub Actions CI on every push (Day 5 of Sprint 1 per the sprint plan).
- [ ] Investigate Test 3 `personal_identifiers` miss — is it a prompt-engineering issue or model-quality issue? Re-run with Claude when Anthropic API access is available to disambiguate.

---

*Document started: May 16, 2026. Append new runs above the latest run as they happen.*