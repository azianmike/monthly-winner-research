# Data dictionary

All money is USD. Results use $1,000 monthly deposits unless specified otherwise. Decimal returns use 0.10 for 10%. Dates are ISO 8601 without time. Valuation cutoff: October 9, 2026 close.

## purchase_ledger.csv — one row per monthly deposit

`buy_date`: first recorded SPY trading day of the month. `signal_date`: previous month’s final trading day. `ticker`: historical security identifier; suffixes distinguish ended histories. `previous_month_return`: adjusted close at signal / preceding month-end adjusted close − 1. `entry_adj_open`: open × adjusted close / close. `contribution`: $1,000. `adjusted_units`: contribution / adjusted open, not actual shares. `ending_marked_value`: adjusted units × terminal adjusted price, or $0 under the ended-history rule. `last_adj_close`: zero if written off. `raw_terminal_adj_close`: last quote before the zero rule. `last_price_date`: final available quote. `spy_entry_adj_open`, `spy_final_adj_close`, and `spy_ending_value`: the identically timed SPY deposit. `status`: quoted through cutoff or written off.

## monthly_results.csv — one row per valuation month

`date`: month-end quote date, except October 2026 ends October 9. `buy_date`, `winner`, `previous_month_return`: this month’s purchase. `members`: supplied membership list at signal date. `ranked_members`: candidates with both required endpoints. `coverage`: ranked_members / members. `missing_tickers`: semicolon-separated missing candidate identifiers. `cumulative_contributions`: cumulative deposits. `strategy_marked_value`, `spy_value`: total portfolio values including contributed money. `written_off_cost`: initial cost of holdings whose histories have ended by that date. `stale_holdings_value`: zero in this model. These are wealth paths, not time-weighted return indices.

## holdings.csv

Aggregates purchases by historical stock identifier. `purchases`: lot count. `invested`: original cost. `marked_value`: ending model value. `portfolio_weight`: share of the total ending value. Ended histories receive zero. `last_price_date` and `status` describe the supplied series.

## Other data

- `monthly_rankings.csv`: every observable candidate return and rank for each signal month.
- `coverage.csv`: selection-date counts and missing identifiers, extracted from monthly results.
- `annual_results.csv`: the last recorded portfolio values each year; 2026 is partial. Not annual returns.
- `split_corrections.csv`: four heuristic correction factors; daily verification evidence is not included in the source archive.
- `sensitivity.csv`: supplied approximation, harsh missing-month writeoff stress, and matched complete-month subset. The subset contributes only $111,000. No row is a bound on the unknown full-data result.
- `original_summary.json`: the supplied summary, unchanged.
- `audit.json`: independent checks, including numerical residuals, hash agreement, workbook checks, and timing exception.
- `independent_price_checks.json`: fresh Yahoo comparisons on the specified purchase dates. Shared upstream data; not a full-universe certification.
- `report_data.json`: selected columns for the interactive HTML. The HTML also embeds this data to work offline.

The original ZIP contains price_endpoints.csv (first/last month quote dates), price_marks.csv (forward-filled holding marks), terminal_quotes.csv, membership_intervals.csv, original programs and provenance hashes. Raw daily parquet history is not included. Never interpret the missing-data proxy as verified bankruptcy status.
