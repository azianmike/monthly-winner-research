# Last month’s winner — a backtest, checked

A public research report with interactive charts, the supplied source data, an independent offline reproduction, an Agents API workflow, and a script for rendering a local animated explainer.

**Verdict: the arithmetic reproduces, but the actual full-universe strategy remains unverified.** Missing candidate prices affect 235 of 346 monthly rankings. This is an approximation that buys the best observable stock, not necessarily the true winner.

## Results and audit

| Item | Independently reproduced |
|---|---:|
| Period | January 2, 1998–October 9, 2026 |
| Deposits into each portfolio | 346 × $1,000 = $346,000 |
| Observed-leader ending value | $8,204,466.91 |
| Matched SPY ending value | $2,258,566.73 |
| Money-weighted return, 365.25 days | 17.8388% / 11.1149% |
| Standard XIRR, 365 days | 17.8256% / 11.1069% |
| Incomplete / complete rankings | 235 / 111 |
| First-month available candidates | 264 / 499 |
| Ending Apple + Nvidia share | 71.4% |
| Purchases beating matched SPY | 95 / 346 |
| Purchases worth zero | 113 in 72 stocks |

The independent implementation recomputed all rankings, dates, and month-by-month valuations from frozen inputs. The maximum monthly difference against supplied CSVs is below $0.000005. All four recorded input SHA-256 checksums match. The workbook’s individual lot differences are below $0.001; its cached values contain no Excel error cells.

Fresh Yahoo chart API queries on October 12, 2026 checked all SPY entry dates and all Apple/Nvidia entry dates plus terminal values. Prices match within input rounding; adjusted growth differences are below one part per million. Yahoo is a shared upstream provider, so this checks consistency rather than independently authenticating the market data. These checks do not establish all candidate prices, corporate actions, or the historical membership reconstruction.

Further findings:

- Membership is evaluated at the prior month-end. JCP is bought on December 2, 2013, which is its exclusive membership end date in the supplied intervals. A purchase-day membership rule could select differently.
- Any series whose quotes end before the cutoff is zeroed. That is broader than verifying that a company actually stopped trading. Cash acquisitions also receive no recovery under the user’s rule. This cannot remedy missing candidates.
- Four split corrections are heuristic. The archive preserves correction records and endpoints but not the daily action evidence required to certify them independently.
- Dividend/spin-off adjustments are provider conventions, not an explicit simulation of every distribution and successor holding. Adjusted opens and adjusted units are accounting constructs.
- The 17.8% and 11.1% figures are **money-weighted annual returns**, not CAGR on a lump sum or average yearly gains. Summary!C12 and D12 in the original workbook contain fixed numeric formulas. They do not update when the underlying returns change.
- The final observation is October 9, 2026, not October month-end. No taxes, commissions, bid/ask spread, or slippage are modeled. Fractional shares and reinvestment are assumed; SPY fees are embedded.

## Open the report

Open `index.html` directly in a browser; the chart and purchase-table data are embedded. Keep the folder together for download links. Or serve it locally:

```sh
python -m http.server 8000
```

The hosted report is at https://azianmike.github.io/monthly-winner-research/ after deployment.

## Reproduce without an API key

Use Python 3.11 or later. Create a virtual environment and install dependencies:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/reproduce.py --allow-incomplete
```

Windows activation: `.venv\Scripts\activate`.

The new outputs are written to `reproduced/`. Without `--allow-incomplete`, the program stops at the first missing ranking and explains why the true winner cannot be identified. The original source archive is read directly; its code is not executed and files are not blindly extracted. Input hashes are verified. The supplied final code can also be reproduced after manual review with its original numpy/pandas/scipy dependencies.

Run `python scripts/audit.py` to recompute the independent input/workbook diagnostics in `data/audit.json`. Run `python -m unittest discover -s tests -v` for the cash-flow, incomplete-ranking, and download-safety tests. Fresh SPY/Apple/Nvidia query responses used in this audit are preserved in `data/price_check_snapshots.zip`. Regenerate the downloadable archive with `python scripts/package.py` after changing deliverables.

`--monthly 500` changes the size of every deposit. This scales the existing strategy; it does not optimize or change its ranking rules. Results are reconciled against the supplied reference at the same scale.

## Run through OpenAI’s Agents API and download the outputs

This uses the **hosted Agents API**, `client.beta.agents.sessions`, not the local Agents SDK or an ordinary Responses request. The model is exactly `gpt-6.1-sol`, with reasoning effort `medium`.

```sh
cp .env.example .env
# Edit .env locally to add OPENAI_API_KEY. Never commit it.
python run_agents.py --dry-run
python run_agents.py
```

The application key needs Agents API read/write, model-inference, and file-upload access in an eligible OpenAI Platform project. Usage is billed to that project. The script uploads the two supplied files, creates an OpenAI-hosted environment, sends `RESEARCH_PROMPT.txt`, waits for a confirmed completed root turn, lists the artifacts from that exact turn, and **streams their bytes to local files**. It requires twelve named outputs including a research ZIP, checks for missing/empty files, validates JSON/ZIP structure, and saves a download manifest with SHA-256 hashes.

The default output folder is `agent_downloads/`. API state and the .env file are ignored by Git. The API key is never placed in the agent sandbox. Artifact filenames are checked for traversal and symlink escapes. The session and uploads are retained for recovery; delete them in your Platform project when no longer needed.

If download transfer is interrupted after the turn finishes:

```sh
python run_agents.py --download-only
```

The script retains `.agent-state.json` and refuses to start a duplicate session automatically. If the session itself is interrupted, inspect that session’s saved events/items using the official recovery documentation before rerunning. A completed API turn does not establish valid financial conclusions; review the resulting audit.

**Execution provenance:** the delivered audit was computed locally. The hosted runner was checked against OpenAI Python SDK 3.29.0 and tested with simulated file transfers. At the user’s choice, no live paid Agents API run was made. Future hosted runs may produce different analysis; preserve their returned files separately.

## Local video rendering

Generated media stays local: `/media/` is ignored by Git and excluded from the public download bundle. The hosted report does not include the video.

To render the 30-second animation locally, install Pillow and ffmpeg, then run `python scripts/make_video.py`. This creates `media/strategy-30s.mp4` and `media/poster.jpg`. macOS system Arial and Georgia are used by default; the renderer also supports Linux DejaVu fonts or `--font-dir`.

## Files and sources

- `data/Backtest_Data_and_Code.zip`: unchanged original archive, including frozen raw price endpoints/marks, membership intervals, terminal quotes, correction table, original code, and outputs.
- `data/Monthly_Winner_Backtest_1998.xlsx`: unchanged original workbook, with the limitations described above.
- `data/*.csv`: readable derived data; see `data/DATA_DICTIONARY.md`.
- `data/audit.json`: independent arithmetic and workbook checks.
- `data/independent_price_checks.json`: fresh price-check diagnostics.
- `data/report_data.json`: the same data embedded in the HTML.
- `RESEARCH_PROMPT.txt`: full goal, assumptions, uncertainty rules, and required downloadable outputs.
- `research_bundle.zip`: report, data, code, and documentation (excludes itself, generated media, secrets, and run state).

Public source reconstruction: [price data](https://github.com/Johnbrick123/sp500-data) and [historical members](https://github.com/fja05680/sp500). The original frozen source metadata identifies release 392203743 and a download date of October 12, 2026. The full original parquet files are not in the attachment; the frozen CSV subsets are sufficient to reproduce its reported approximation. Third-party data retains its providers’ terms; this project grants no new rights over those inputs.

Official API references: [quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart), [configuration](https://developers.openai.com/api/docs/guides/agents-api/configuration), [files and artifacts](https://developers.openai.com/api/docs/guides/agents-api/environments/files), [stream recovery](https://developers.openai.com/api/docs/guides/agents-api/sessions), [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

Research only. The approximation does not establish repeatable outperformance or expected future returns.
