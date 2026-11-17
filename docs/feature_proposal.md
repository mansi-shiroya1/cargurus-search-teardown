# Teardown notes and feature proposal

<!--
analyze.py reads this file and turns each "## " section into a section of report/report.html.
Keep the "## " headings as they are. Lines starting with "- " become list items, and
"A | B | C" splits into columns where noted. Empty sections are hidden on the page.
-->

## Feature name
Smart filter suggestions

## Method
- Run on November 13, 2026, in one desktop browser session per site.
- Same search on both sites: used SUVs, max price $25,000, within 25 miles of Santa Clara, CA (ZIP 95050).
- Six shopper tasks per site, each scored from 1 (painful) to 5 (easy) on how much effort it took.
- Result counts written down at every step. Inventory moves during the day, so counts are approximate: the CarGurus broad search went from 2,939 to 2,944 within ten minutes.
- No forms were submitted and no account was created. Contact and history tasks were judged on what a signed-out shopper can see.
- Cars.com was planned as a third site but could not be loaded in the test session, so it is left out.

## Findings
- Two must-have filters still leave 500+ cars | The broad search returned 2,939 SUVs on CarGurus. Adding Apple CarPlay and AWD cut that to 518. Autotrader went from 1,690 to 574. Applying the filters was easy on both sites, which is why the task scored 4, but the outcome is still hundreds of cars away from a shortlist.
- CarGurus has 31 filter groups and no starting point | The filters sit in seven sections of one long left panel. Every option shows a count, which helps, but nothing suggests which filter to try next. CarPlay is under Features, while AWD is under Specs, well below it.
- Autotrader already nudges shoppers, but bluntly | A row of 19 quick-filter chips sits above its results. Some are useful, like AWD/4WD (970 cars). Others are not: "2002 and newer" would remove 5 of 1,690 cars, and "Beige (7)", "Manual (7)" and "Buick (7)" sit in the same row. The chips do not look ranked by what would help narrow this search.
- CarGurus is strongest once a shortlist exists | Deal rating, dollars below market, price history and days on market make price easy to judge, and compare works straight from the results page with no account. The weak spot is the limit of two cars per comparison.

## Problem
A shopper who starts broad gets thousands of cars, and the usual must-haves do not get them close to a shortlist. In this test, two filters took CarGurus from 2,939 results to 518. CarGurus offers 31 filter groups to keep going, but it leaves the choice of what to try next entirely to the shopper.

## Why this problem
Compare scored lower than filtering, so it is the obvious runner-up. Narrowing comes first for three reasons. Every shopper goes through it, while compare only matters to those who already have a shortlist. It sits earlier in the funnel, so friction there affects everything after it. And CarGurus already has the main ingredient on the page: a result count next to every filter option. Autotrader's chips show the idea is workable and also show how a generic version falls short.

## Proposal
Show 3 to 4 suggested filters above the results, picked for the current search. Rank them by how often shoppers running a similar search apply them and by how much each one narrows the list. Each chip shows how many cars would be left, and one tap applies it. Suggestions refresh after every filter, so the shopper always has a sensible next step until the list is short enough to browse.

## Mockup search
Used SUVs under $25k near Santa Clara · 2,939 results

## Suggested filters
- AWD (1,375)
- Heated seats (1,699)
- Apple CarPlay (1,160)
- Third-row seating (500)

## What exists today
- CarGurus: search filters | 31 filter groups, with a result count beside every option | No guidance on which filters matter for this search
- CarGurus: deal ratings + Instant Market Value | Rates each listing from Great Deal to Overpriced against an estimated market price | Helps judge price, not narrow a broad search
- CarGurus: Ask Guru | Conversational search box at the top of the results page | The shopper has to know what to ask for
- CarGurus: saved searches + alerts | Notifies shoppers of price drops and new matches | Helps once a shortlist exists, not while building one
- CarGurus: compare | Side-by-side view opened from the results page | Two cars at a time
- Autotrader: quick-filter chips | 19 one-tap filters with counts above the results | Not ranked for the search, so rare options sit beside useful ones
- Autotrader: filter search | "Find a filter" box inside the filter drawer | Only helps if the shopper already knows the filter's name

## Dealer tradeoff
CarGurus earns revenue from dealers who want their listings seen. Narrower searches mean some listings get fewer views, which could frustrate dealers whose cars get filtered out. The bet is that shoppers who reach a confident shortlist are more likely to contact a dealer, so leads hold up or improve even if raw listing views fall.

## How I'd limit it
- Never suggest a filter that would drop results below 50 listings
- Rank suggestions by shopper behavior only, never by dealer spend, the same way CarGurus says it orders deals today
- Track total dealer leads and leads per listing as guardrails
- Share test results with dealer account managers before full launch

## V1 in
- Suggestions on used-car search results pages on desktop web
- 3 to 4 suggested filters per search, each with the count of cars left
- One-tap apply, with suggestions refreshing after each filter

## V1 out
- Personalized suggestions from each shopper's own history
- New-car search and the mobile apps
- Comparing more than two cars at once (the runner-up problem from this test)

## Primary metric
Search-to-lead rate (share of searches that end in a dealer contact)

## Secondary metrics
- Suggestion tap rate
- Median results count when a shopper opens their first listing
- Time to first saved car

## Guardrails
- Zero-result searches
- Total dealer leads

## Test and launch
- A/B test | 50/50 split on used-car search for 2 weeks, or until the result is significant
- Limited rollout | 10% of shoppers, watching guardrails daily
- Full launch | 100% of shoppers, with a help-center note and a heads-up to dealer account managers

## Risks
- Suggestions feel pushy or irrelevant: track tap rate and let shoppers dismiss the row
- Popular filters just repeat the obvious: weight suggestions by how much they narrow the list, which is where Autotrader's chips fall short
- Rare searches have too little data: show no suggestions instead of weak ones
- Overlap with Ask Guru: test whether a chip row and a chat box together confuse shoppers
- The evidence is thin: scores are one tester's judgment from one session in one market

## Next steps
- Run 5 short interviews with recent car buyers using docs/interview_guide.md to check whether narrowing is where they struggled
- Ask for search-log data: the share of searches that return 500+ results and how many filters shoppers apply before opening a listing
- Repeat the test on Cars.com and on the mobile apps
- Rerun the same search in a smaller market, where inventory is thinner and the problem may look different

## Evidence
- cargurus-broad-search.png | CarGurus: the broad search returns about 2,900 used SUVs under $25k within 25 miles.
- cargurus-feature-filters.jpg | CarGurus: 518 cars left after AWD and CarPlay. Every feature has a count, but nothing suggests what to pick next.
- autotrader-quick-filters.png | Autotrader: quick-filter chips with counts sit above the results.
- cargurus-compare-limit.png | CarGurus: compare opens from the results page, limited to two cars.
- cargurus-price-context.png | CarGurus: deal rating, price drop and days on market on one listing.
