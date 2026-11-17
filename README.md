# Car Search Teardown: CarGurus vs. Autotrader

A hands-on teardown of used-car search on two marketplaces, and a feature proposal for CarGurus based on what the test showed.

**[View the live report](https://mansi-shiroya1.github.io/cargurus-search-teardown/report/report.html)**

## The question
Where does a shopper get stuck between a broad search and a shortlist, and what should CarGurus build first to fix it?

## Approach
1. **Task testing.** The same six shopper tasks on CarGurus and Autotrader, with one search: used SUVs under $25,000 within 25 miles of Santa Clara, CA. Each task is scored from 1 (painful) to 5 (easy). Scores are in `data/task_scores.csv` and the raw notes are in `docs/test_notes.md`.
2. **Result counts.** How many cars were left after each filter. → `data/funnel.csv`
3. **Landscape review.** The existing features on both sites that touch this problem and the gap each one leaves.
4. **Feature proposal.** Problem, why it comes first, a concept mock-up, the dealer tradeoff, V1 scope, metrics, an A/B test and rollout plan, risks, and next steps. → `docs/feature_proposal.md`

## Findings
- **Two must-have filters still leave 500+ cars.** CarGurus went from 2,939 results to 518 after Apple CarPlay and AWD. Autotrader went from 1,690 to 574.
- **CarGurus has 31 filter groups and no starting point.** Every option shows a count, but nothing suggests what to try next.
- **Autotrader already nudges shoppers, but bluntly.** Its 19 quick-filter chips mix useful options (AWD/4WD, 970 cars) with ones that barely matter ("Beige (7)", "2002 and newer").
- **CarGurus is strongest once a shortlist exists.** Deal ratings, price history and compare are ahead of Autotrader. Compare is limited to two cars.

| Task | CarGurus | Autotrader |
|---|---|---|
| Broad search | 4 | 4 |
| Must-have filters | 4 | 4 |
| Compare 3 cars | 3 | 2 |
| Judge the price | 5 | 4 |
| Check history | 4 | 3 |
| Contact dealer | 5 | 5 |
| **Average** | **4.17** | **3.67** |

## The proposal
**Smart filter suggestions:** 3 to 4 suggested filters above the results, picked for the current search and ranked by how much they narrow the list, each showing how many cars would be left. Success is measured by search-to-lead rate, with zero-result searches and total dealer leads as guardrails.

## Run it
```bash
python3 analyze.py       # standard library only, no installs
open report/report.html  # or double-click the file
```

## Repo structure
```
data/
  task_scores.csv         task scores (1-5) and notes for each site
  funnel.csv              cars left after each filter step
  interviews.csv          empty template for the interview step
  pain_point_effort.csv   empty template for ranking pain points
docs/
  feature_proposal.md     findings and proposal text (each "## " section becomes a page section)
  test_notes.md           raw notes from the test session
  interview_guide.md      10-minute interview script for the next step
analyze.py                builds the page from data/ and docs/
report/report.html        the built page
report/screenshots/       screenshots taken during the test
```

## Limitations
- One tester, one session per site, one market, on November 13, 2026. Scores are a judgment call.
- Result counts change during the day as inventory moves.
- Cars.com was planned as a third site but could not be loaded in the test session.
- No user interviews yet. The interview guide and templates are in the repo for that step.

## Sources
- [How CarGurus works](https://www.cargurus.com/about/how-cargurus-works)
- [What is IMV? (CarGurus help center)](https://cargurus.helpscoutdocs.com/article/10-what-is-imv)

Independent analysis, not affiliated with CarGurus or Autotrader.
