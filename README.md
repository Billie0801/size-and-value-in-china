# Size and Value in China

This repository reproduces the China three-factor model in Liu, Stambaugh,
and Yuan (2019) and compares it with the Fama-French three-factor model.

The main analysis is in `notebooks/replicate_main.ipynb`. The supporting code
is deliberately limited to three files:

- `data.py` reads the large Wind files and builds a point-in-time monthly panel.
- `factors.py` applies the common 2 x 3 portfolio construction to EP or BM.
- `inference.py` contains the statistics used in Tables 3 and 5.

The published paper and its online appendix are in `docs/` for reference.

## Current scope

The sample runs from January 2000 through December 2016. Both models remove
the smallest 30% of eligible stocks and use the same monthly 2 x 3 portfolio
sort. CH-3 constructs MKT, SMB, and the EP-based VMG factor; FF-3 replaces EP
with BM and constructs FFSMB and FFHML. Size, portfolio weights, and valuation
denominators use market value based on `TOT_SHR_TODAY`. The raw earnings-price
ratio is kept as `EP_raw`; the CH-3 sorting variable is `EP = max(EP_raw, 0)`.
A stock must have at least 15 trading records in the most recent 22
market trading days, in addition to 120 trading records over the preceding 12
months.

The FF-3 portfolios use the same sortable stock universe as CH-3 and require
positive book equity. Raw BM is retained in the monthly panel; observations
without EP or with nonpositive BM are excluded only from the FF-3 six-portfolio
sort.

Following the paper's online appendix, BM uses point-in-time
`TOT_SHRHLDR_EQY_EXCL_MIN_INT`. Duplicate income and balance-sheet statements
prefer type `408005000`, falling back to `408001000`. The notebook reports the
Table 3 factor summary and the Table 5 White-HC0 regressions and GRS tests.
Following Appendix A.1, financial information before 2002 is restricted to
semiannual and annual reports; quarterly reports are used from 2002 onward.

## Running the notebook

Create an untracked `config.local.json` in the project root:

```json
{
  "data_root": "/absolute/path/to/the/raw/data"
}
```

Run the notebook from top to bottom. Intermediate parquet files are stored
under `work/ch3_total_share_cache` so the multi-gigabyte raw files do not need to
be scanned on every run. Aggregate outputs are written to `results`.

Raw Wind data, local paths, caches, and record-level processed data must not be
committed.
