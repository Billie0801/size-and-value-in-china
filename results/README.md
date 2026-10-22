# Results

The main notebook writes only aggregate factor series, portfolio returns,
diagnostics, and summary tables here. Raw and record-level data remain outside
the repository.

## Current run: CSMAR total A-share size (2026-10-21)

Size screening, breakpoints, SIZE anomaly portfolios, and every portfolio
weight now use CSMAR monthly total A-share market capitalization (`Msmvttl`),
including the November 1999 reversal warm-up. This is not circulating market
cap and not CSMAR-implied shares multiplied by Wind prices. The processed
monthly source is already in yuan. Four historical ticker mappings align it
to Wind's identifiers; all 324,863 eligible stock-months have positive caps.

Wind returns, financial statements, publication-date matching, and EP/BM/CP
valuation denominators remain unchanged. Table 3 still uses ordinary mean t;
Tables 5–8 use White HC0. The 22-market-day filter, full 36-observation rolling
window, and CP's semiannual treatment through 2002 are retained. This is a
mixed-source replication, not an exact restoration of the original Wind data.
The `_total_share` output filenames are retained for compatibility and now
identify this total-A-share-size run rather than the older Wind-only run.

| Statistic | Published | Previous Wind-size run | Current |
| --- | ---: | ---: | ---: |
| Table 3 VMG mean (%) | 1.14 | 1.109034 | 1.146642 |
| Table 3 VMG standard deviation (%) | 3.75 | 3.856345 | 3.754939 |
| Table 3 VMG t | 4.34 | 4.107562 | 4.361544 |
| Table 5 FFHML alpha (%) | 0.34 | 0.492662 | 0.331117 |
| Table 5 FFHML alpha t | 0.97 | 1.480982 | 0.967958 |
| Table 7 unconditional SIZE alpha (%) | 0.21 | 0.233734 | 0.213900 |
| Table 7 unconditional SIZE alpha t | 1.71 | 2.425823 | 1.827516 |

SIZE alpha now has a two-sided asymptotic HC0 p-value of 0.067622, matching
the paper's nonrejection at 5%, not proving a zero alpha. Its alpha/t relative
errors are 1.86%/6.87%. At the usual two-sided 10% level it remains significant.

| Table | Nonzero comparison items | Within 10% | Median relative error |
| --- | ---: | ---: | ---: |
| Table 3 | 12 | 11 | 2.64% |
| Table 4, China only | 8 | 8 | 3.38% |
| Table 5 | 12 | 7 | 2.68% |
| Table 6 | 114 | 79 | 5.81% |
| Table 7 | 150 | 67 | 12.11% |
| Table 8 | 151 | 82 | 9.06% |

These are diagnostics across all listed means, alphas, loadings and t-values,
not a claim that every item meets the target. Three published zeros have only
absolute errors. Table 4's median worsens from 2.91% to 3.38%. MKT–SMB
correlation is 0.145909 versus 0.12; FFSMB alpha/t are -0.052777%/-0.797392
versus -0.04%/-0.66. The GRS F for FF factors regressed on CH-3 is 1.040824
versus 0.88 (18.28% relative error); the reverse F is 32.967830 versus 33.90.
Near-zero alphas and
tiny p-values still require absolute differences as well as relative errors.

CP has 204 unconditional months and 203 size-neutral months; only May 2000
is missing in Panel B. All other anomaly series have 204 months. Daily REV
was recomputed with the new pool and weights, not copied from the old run.
Source joins, unchanged financial values/returns, both GRS formulas, all
57 anomaly regressions, rolling R-squared, and REV compounding were checked
independently. Test scripts and record-level snapshots remain outside the
project; the licensed source parquet is not added to the repository.

## Historical runs

The dated sections below describe earlier Wind-size versions. Their uses of
"current" or "now" refer to those dates, not the CSMAR-size run above.

### Table 3 and Table 5 checks (2026-10-17)

All primary results use self-constructed factors over January 2000–December
2016 (204 months), total-share market capitalization, the 22-market-day trading
filter, ordinary mean t-statistics for Table 3, and White HC0 regressions for
Table 5. The source-data limitation for total A-share capitalization remains.

This revision removes next-month return availability from formation filters,
uses the retained universe's size median in both models, and applies statement
type priority only among records already public at the formation date.
It also converts reported YTD earnings into single-quarter earnings from 2002
and single-half-year earnings before 2002. By default, FF retains negative BM
so its sortable universe matches CH's in this data; the positive-book-only
alternative was tested separately.

"Before" below refers to the version before both the formation-date corrections
and the earnings-frequency change, not the isolated effect of either change.

| Statistic | Published | Before | Current |
| --- | ---: | ---: | ---: |
| Table 3 MKT mean (%) | 0.66 | 0.692631 | 0.692639 |
| Table 3 SMB mean (%) | 1.03 | 0.953056 | 0.965168 |
| Table 3 VMG mean (%) | 1.14 | 0.963488 | 1.109034 |
| Table 3 VMG t | 4.34 | 3.361669 | 4.107562 |
| Table 5 FFSMB alpha (%) | -0.04 | -0.053120 | -0.041671 |
| Table 5 FFHML alpha (%) | 0.34 | 0.539329 | 0.492662 |
| Table 5 SMB alpha (%) | 0.47 | 0.465091 | 0.460325 |
| Table 5 VMG alpha (%) | 1.39 | 1.208329 | 1.337528 |
| GRS: FF factors on CH-3 | 0.88 | 2.064585 | 1.513132 |
| GRS: CH factors on FF-3 | 33.90 | 24.037537 | 30.594764 |

`table3_table5_errors.csv` includes absolute differences and relative errors
for all Table 3 means, standard deviations, t-statistics, and off-diagonal
correlations, plus Table 5 alphas, t-statistics, GRS statistics, and p-values.
The full 5–10% target has **not** been achieved. All 12 Table 3 statistics are
within 10%, including VMG's mean, standard deviation, and t-statistic (errors
2.72%, 2.84%, and 5.36%). In Table 5, FFSMB, SMB, and VMG alphas and their
t-statistics are within 10%. FFHML alpha and t-statistic still differ by 44.90%
and 52.68%. The two GRS F-statistics differ by 71.95% and 9.75%; neither
GRS p-value is within 10%. Overall, 19 of the 24 displayed metrics are within
10%. Near-zero alphas and very small p-values need the absolute differences
as well as relative errors; the small GRS p-value differs by more than an order
of magnitude even though both versions reject the null.

### Earnings frequency and negative-BM sensitivity

The largest improvement comes from earnings frequency rather than the trading
window. After the formation-date corrections but before the frequency change,
VMG mean and t were 0.963603% and 3.364509. Single-period earnings raise them
to 1.109034% and 4.107562. Correlation with the author's updated monthly VMG
increases from approximately 0.970 to 0.991 over the same 204 months.

An independent check against Wind's `S_QFA_DEDUCTEDPROFIT` matches 101,336
out of 101,363 comparable observations within RMB 1 (99.97%). Previous-period
profit is matched as of the current report's publication date; subsequent
revisions are not borrowed. Missing previous components remain missing rather
than being set to zero. The paper does not provide a complete cumulative-to-
single-period conversion algorithm, so this evidence supports the chosen
conversion but does not establish the author's exact original implementation.

Keeping negative BM affects 732 stock-months out of 227,050 observations with
available EP after the base filters and microcap exclusion. It makes the two
sortable universes coincide in the current data. The following comparison
holds the single-period earnings and every other parameter fixed:

| Table 5 statistic | Positive BM only | Negative BM retained (current) | Published |
| --- | ---: | ---: | ---: |
| FFSMB alpha (%) | -0.052736 | -0.041671 | -0.04 |
| FFSMB alpha t | -0.737369 | -0.607071 | -0.66 |
| FFHML alpha (%) | 0.480810 | 0.492662 | 0.34 |
| FFHML alpha t | 1.467778 | 1.480982 | 0.97 |
| GRS: FF factors on CH-3 | 1.617535 | 1.513132 | 0.88 |
| GRS: CH factors on FF-3 | 30.881909 | 30.594764 | 33.90 |

Retaining negative BM helps FFSMB but slightly worsens FFHML. It is a disclosed
interpretation of the same-universe requirement, not an author-confirmed rule
or a general replacement for positive-book FF conventions. The current notebook
retains negative BM and no longer exposes the earlier `ff_positive_book_only`
switch. Table 3 is unaffected by this choice.

### Separate official-factor diagnostics

The optional `official_*_diagnostic.csv` outputs use the author's updated
monthly CH-3 series and self-constructed FFSMB/FFHML. They are **not** the
self-constructed CH-3 reproduction above. With the current FF factors, their
GRS statistics are 0.798492 and 30.757383, versus published 0.88 and 33.90.
The corresponding p-values are 0.451443 and 2.293838e-12. Agreement of the F
statistics does not imply that all alphas, t-statistics, or p-values meet the
target. Updated official series also differ from the published Table 3 values.
Replacing self-constructed CH-3 with the updated official CH-3 reduces FFHML
alpha from 0.492662% to 0.400078%, still above the published 0.34%. This
diagnostic does not isolate a single causal source of the remaining error.

### Diagnostic checks

Tests covered ANN_DT versus ACTUAL_ANN_DT, publication at the month-end versus
last trading day, cumulative/single-period/TTM earnings, negative EP and BM,
common sorting samples, breakpoint interpolation, listing-age conventions,
risk-free-rate conversion, and total-share versus free-float size and weights.
Not every alternative has equal documentary support; closeness alone is not
evidence of the author's convention. TTM alternatives lack necessary early
quarterly components, and free-float capitalization does not consistently
improve the results and is not the paper's total-A-share definition.

The 20/21/22/23-market-day windows were compared with the selected earnings
and BM rules. None fixes the FFHML discrepancy, and 22 days is retained rather
than changing the window for one statistic. Calendar-month, trailing-30-day,
and trailing-31-day filters each leave five return months without eligible
stocks: March 2000, February 2001, March 2002, February 2004, and March 2005.
These months were not silently dropped. Daily adjusted-price returns in 2005–2009 agree
with returns formed from consecutive adjusted closing prices, apart from small
rounding differences. Matrix-formula cross-checks confirm White HC0 and GRS.

Diagnostic scripts and alternative runs are outside the repository. No months
were removed, factors rescaled, or inference methods selected to fit the
published table. The evidence does not identify missing A-share capitalization
as the sole remaining cause; historical financial-data versions and unresolved
construction details still warrant investigation.

### First extension: Tables 4 and 6-8 (2026-10-19)

This run keeps the existing CH-3/FF-3 construction and all 14 earlier CSV
outputs unchanged. It adds the China panels of Table 4 and all ten anomaly
strategies used in Tables 6-8, including the size-neutral variants (which omit
the size anomaly). It is a baseline, not a parameter search for the new tables.

| Table | Nonzero published statistics | Within 10% | Median relative error |
| --- | ---: | ---: | ---: |
| Table 4, China only | 8 | 8 | 3.44% |
| Table 6 | 114 | 64 | 9.05% |
| Table 7 | 150 | 52 | 15.42% |
| Table 8 | 151 | 70 | 12.93% |

These counts include means, alphas, factor loadings, and t-statistics, not just
alphas. They also include CP regressions with shorter samples and must not be
interpreted as same-sample matches throughout. Three additional published
statistics equal zero after rounding and have no defined relative error;
their absolute differences remain in the comparison file. Near-zero targets
can produce large relative errors even when the absolute gap is small.

### Table 4

| Panel and model | Published R-squared | First run |
| --- | ---: | ---: |
| A: MKT | 0.385 | 0.372232 |
| A: MKT, SMB | 0.507 | 0.525587 |
| A: MKT, VMG | 0.471 | 0.498205 |
| A: MKT, SMB, VMG | 0.536 | 0.555117 |
| B: MKT | 0.417 | 0.386979 |
| B: MKT, SMB | 0.528 | 0.518796 |
| B: MKT, VMG | 0.501 | 0.499639 |
| B: MKT, SMB, VMG | 0.562 | 0.549916 |

Regressions include an intercept, use monthly excess returns, and use complete
36-calendar-month windows within the available 2000-2016 factor sample. The
first window ends in December 2002. A window needs 24 valid observations, a
disclosed implementation choice. Panel A applies the existing base eligibility
filters but keeps microcaps; Panel B additionally masks the bottom 30% each
month before fitting. R-squared is averaged first across windows for a stock,
then equally across stocks. It is not adjusted R-squared. The US panel is not
reproduced, and earlier factor history is not invented to fill the first 35
window endpoints.

### Anomaly construction and coverage

Monthly strategies use SIZE, positive EP, BM, positive CP, ROE, VOL, MAX, TURN,
and ABTURN. Directions are fixed before observing the results. In the
size-neutral strategies, size deciles are fixed using the retained monthly
universe before filtering each characteristic. Stocks from the same anomaly
decile are pooled across size groups and then value-weighted. Ties are broken
by stock code. Missing next-month returns do not change sorting breakpoints.

VOL/MAX use the last 20 market trading days with at least 15 active records.
TURN is the 250-day mean of daily volume divided by total shares, with at
least 120 valid records. ABTURN is the 20-day mean divided by the 250-day
mean. ROE uses the current single-period earnings and book equity from the
same report period already public at formation. Before 2002 its numerator
remains semiannual, consistent with the current EP basis; it is not relabeled
as observed quarterly profit.

Cash flow prefers ending minus beginning cash balances and uses reported net
cash change only when that difference is missing. The annual source audit
reports which field was used and disagreements between overlapping fields.
Single-period changes require the previous component already public at the
current report's release. Through 2002, only semiannual and annual reports
are used and single-half-year changes are divided by two. Quarterly conversion
starts in 2003 for CP only. The source has only 16 usable first-quarter and
22 third-quarter cash-flow records for 2002 before conversion; extending
semiannual treatment avoids subtracting these mostly missing quarters. This
is a data-coverage choice, not an author-confirmed rule. No zero is substituted
for a missing component.

CP now has 204 unconditional months and 201 size-neutral months. The remaining
size-neutral missing months are May–July 2000, where some fixed size groups
lack ten positive-CP stocks. All other anomaly series have 204 monthly
observations. The comparison records the regression sample lengths; the
size-neutral CP results are still not a full-period reproduction.

Reversal is computed daily, with the last 20-day signal lagged one trading
day, five staggered five-day holdings, and drifting weights within each
holding. Four pre-sample trading days initialize the five slices using only
the earlier, available monthly universe and market values. Daily spread
returns are compounded into monthly returns. Missing holding quotes carry
the last valuation and their weight is reported, not hidden. Average missing
quote weights are approximately 0.0031% and 0.0064% for panels A and B;
no delisting return is fabricated. These strategies are before transaction
costs, and the existing total-share capitalization proxy remains.

### What the first results show

The principal EP/profitability comparison is visible. In unconditional sorts,
ROE alpha is -0.322% under CH-3 (t=-0.797) and 1.697% under FF-3 (t=5.304),
versus published -0.36% and 1.75%. EP alpha is 0.134% under CH-3 and 1.485%
under FF-3, versus 0.04% and 1.54%. The CH-3 EP alpha remains statistically
insignificant despite its large relative difference from the near-zero target.

Not all findings are reproduced closely. Unconditional size has a CH-3
alpha t-statistic of 2.426 instead of 1.71, changing its 5% significance
classification. CH-3 volatility/MAX alphas are higher than published; the
size-neutral MAX alpha is 0.405% rather than the rounded 0.00%. CP's source
limitations and remaining size-neutral sample gaps are disclosed separately.

### New outputs and checks

- `table4_china_total_share.csv`, `table6_total_share.csv`,
  `table7_total_share.csv`, `table8_total_share.csv`: primary tables.
- `table4_table6_table8_errors.csv`: all 426 new comparisons, including Table 7,
  absolute/relative errors, and anomaly regression sample lengths.
- `new_tables_error_summary.csv`: compact error counts by table.
- `anomaly_returns_total_share.csv`, `anomaly_monthly_portfolios.csv`:
  aggregate spreads, leg returns, and sorting counts.
- `reversal_daily_portfolios.csv`, `reversal_monthly_diagnostics.csv`:
  aggregate reversal returns, slice counts, and missing-quote weights.
- `anomaly_signal_coverage.csv`, `cash_flow_source_audit.csv`: data coverage.

Independent tests cross-check rolling R-squared against separate statsmodels
fits, pooled value weights, missing-data behavior, lagged reversal signals,
holding-period weight drift, and daily-to-monthly compounding. Source checks
also reproduce the existing recent-22-day counts and monthly return series.
All Table 6-8 reference numbers were checked against PDF text extraction.
Diagnostic scripts remain outside the repository, and only aggregate outputs
are saved here.

### Controlled follow-up checks (2026-10-20)

Table 4 now requires 36 valid monthly observations in each 36-calendar-month
window instead of the first run's minimum of 24. All other construction rules
stay fixed. The paper specifies a past-36-month regression but does not give
an explicit minimum-observation rule. Requiring the full window is the stricter
interpretation adopted here, not a claim to have recovered the author's code.

| Panel and model | Published | Minimum 24 | Minimum 36 (current) |
| --- | ---: | ---: | ---: |
| A: MKT | 0.385 | 0.372232 | 0.397773 |
| A: MKT, SMB | 0.507 | 0.525587 | 0.529497 |
| A: MKT, VMG | 0.471 | 0.498205 | 0.500938 |
| A: MKT, SMB, VMG | 0.536 | 0.555117 | 0.556129 |
| B: MKT | 0.417 | 0.386979 | 0.417689 |
| B: MKT, SMB | 0.528 | 0.518796 | 0.521607 |
| B: MKT, VMG | 0.501 | 0.499639 | 0.501516 |
| B: MKT, SMB, VMG | 0.562 | 0.549916 | 0.547916 |

The median relative error across these eight statistics falls from 3.44% to
2.91%; all eight remain within 10%. This is not a uniform improvement: three
statistics improve and five worsen (Panel A's MKT difference is almost unchanged).
Stocks contributing to the time-first
average fall from 2,572 to 2,193 in Panel A and from 2,006 to 1,473 in Panel B.
The 24-observation alternative remains available through the notebook parameter.
Table 3, Table 5, and Tables 6-8 are unchanged by this revision.

Other controlled tests were not adopted. These included cumulative cash flow,
carrying the latest computable cash flow, a 2002 semiannual cash-flow diagnostic,
alternative decile allocation, characteristic-specific size groups, positive-book
ROE, different daily-return coverage, and turnover excluding inactive dates.
None was a consistent improvement across Tables 6-8 at that stage. The 2002
semiannual diagnostic changes the earlier date boundary and was not adopted
in this October 20 run; its subsequent adoption for CP only is recorded below.
Missing components and portfolio returns were not filled to match the target.

With the same anomaly returns but updated official CH-3 factors, Table 7's
mean absolute alpha difference falls from 0.1239 to 0.0878 percentage points;
its median error across all nonzero statistics falls from 15.42% to 13.60%.
This is only a diagnostic: some entries worsen and size-neutral MAX alpha
remains 0.3812% against a published rounded 0.00%. It does not justify replacing
self-constructed factors or attributing all remaining differences to one source.

The available share-structure workbook starts in 2009 and labels its A-share
field as circulating A shares. It cannot supply the missing total-A-share
history. Tests and alternative outputs remain outside this project. Existing
cached inputs are retained; this follow-up is not a rebuild from a new raw-data
snapshot. The notebook's input filenames were updated to the files currently
present on the external drive.

### CP semiannual treatment through 2002 (2026-10-21)

At the user's request, CP now uses semiannual and annual reports through
2002, with single-half-year cash changes divided by two. Quarterly cash-flow
conversion starts in 2003. The visible notebook parameter is
`cash_flow_quarterly_start="2003-01-01"`; the earnings/book-equity boundary
remains 2002, and EP, BM, ROE, the factor construction, and Table 4's full
36-observation requirement are unchanged. This is a disclosed adjustment for
the available cash-flow coverage, not a claim about the author's exact rule.

CP's unconditional sample increases from 196 to 204 months and its size-neutral
sample from 193 to 201. Only May–July 2000 remain missing in the size-neutral
series because some size groups lack enough positive-CP stocks. Publication
dates still govern availability; no missing component or return is set to zero.

| CP alpha, monthly % | Published | Previous | Current |
| --- | ---: | ---: | ---: |
| Table 6 A | 0.70 | 0.436179 | 0.521164 |
| Table 6 B | 0.76 | 0.672270 | 0.729769 |
| Table 7 A | 0.20 | 0.032221 | 0.054702 |
| Table 7 B | 0.18 | 0.202241 | 0.211386 |
| Table 8 A | 0.63 | 0.167054 | 0.217580 |
| Table 8 B | 0.52 | 0.530411 | 0.564026 |

The sample becomes more complete, but not every statistic improves. Current
median relative errors for Tables 6/7/8 are 8.68%/15.74%/12.93%, compared with
9.05%/15.42%/12.93% before this change. All non-CP anomaly returns and regression
statistics, Table 3–5 outputs, and daily reversal outputs are unchanged. The
separate CSMAR-implied A-share-size experiment has not been incorporated.
