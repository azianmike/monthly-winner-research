"""Rebuild the supplied approximation from frozen price and membership inputs.

Default refuses incomplete rankings. --allow-incomplete explicitly reproduces
the original best-observed-candidate convention; it does not certify it.
No API or network needed. Results go to a separate directory.
"""
import argparse
from pathlib import Path
from io import BytesIO
import hashlib
import json
import math
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def annual_return(dates, contributions, terminal_date, final_value, basis=365.25):
    years = (pd.Timestamp(terminal_date) - pd.DatetimeIndex(dates)).days.to_numpy() / basis
    payments = np.asarray(contributions, dtype=float)
    if final_value <= 0 or not np.all(payments > 0):
        raise ValueError('Positive ending value and deposits required')
    lo, hi = -0.999999, 1.0
    while np.sum(payments * (1 + hi) ** years) < final_value:
        hi = 2 * hi + 1
        if hi > 1e6: raise ValueError('Return could not be bracketed')
    for _ in range(160):
        mid = (lo + hi) / 2
        if np.sum(payments * (1 + mid) ** years) > final_value: hi = mid
        else: lo = mid
    return (lo + hi) / 2

def run(archive, destination, allow_incomplete=False, amount=1000.0):
    if not math.isfinite(amount) or amount <= 0: raise ValueError('Deposit must be positive')
    with zipfile.ZipFile(archive) as z:
        prefix = 'outputs/backtest_1998/'
        hashes = json.loads(z.read(prefix + 'frozen_input_hashes.json'))
        for name, expected in hashes.items():
            if hashlib.sha256(z.read(prefix + name)).hexdigest() != expected:
                raise ValueError('Input checksum failed: ' + name)
        def read(name, **kwargs): return pd.read_csv(BytesIO(z.read(prefix + name)), **kwargs)
        p = read('price_endpoints.csv', parse_dates=['date'])
        marks = read('price_marks.csv', index_col=0, parse_dates=[0])
        last = read('terminal_quotes.csv', parse_dates=['date']).set_index('ticker')
        member = read('membership_intervals.csv', parse_dates=['start', 'end'])
        corrections = read('split_corrections.csv', parse_dates=['date'])
        reference = json.loads(z.read('outputs/final_backtest/summary.json'))
    if p.duplicated(['date', 'ticker']).any(): raise ValueError('Duplicate prices')
    if not np.isfinite(p[['open','close','adj_close']].to_numpy()).all() or (p[['open','close','adj_close']] <= 0).any().any():
        raise ValueError('Invalid prices')
    for e in corrections.itertuples():
        p.loc[(p.ticker == e.ticker) & (p.date < e.date), 'adj_close'] *= e.correction_factor
        marks.loc[marks.index < e.date, e.ticker] *= e.correction_factor
        if last.loc[e.ticker, 'date'] < e.date: last.loc[e.ticker, 'adj_close'] *= e.correction_factor
    p['adjusted_open'] = p.open * p.adj_close / p.close
    close = p.pivot(index='date', columns='ticker', values='adj_close')
    prices = p.set_index(['date', 'ticker'])
    spy = p[p.ticker == 'SPY'].set_index('date').sort_index()
    calendar = {m: (g.index.min(), g.index.max()) for m, g in spy.groupby(spy.index.to_period('M'))}
    asof = pd.Timestamp('2026-10-09')
    units = {}; spy_units = 0.0; lots = []; monthly = []; rankings = []
    for i, month in enumerate(pd.period_range('1998-01', '2026-10', freq='M')):
        buy, end = calendar[month]; signal = calendar[month-1][1]; base = calendar[month-2][1]
        eligible = set(member.loc[(member.start <= signal) & (member.end.isna() | (member.end > signal)), 'ticker'])
        candidates = sorted(eligible.intersection(close.columns))
        returns = (close.loc[signal, candidates] / close.loc[base, candidates] - 1).dropna()
        ordered = sorted(returns.items(), key=lambda item: (-item[1], item[0]))
        missing = sorted(eligible.difference(returns.index))
        if missing and not allow_incomplete:
            raise ValueError(f'{month}: cannot identify true winner; {len(missing)}/{len(eligible)} candidates missing. Use --allow-incomplete only for the disclosed approximation.')
        if not ordered: raise ValueError(f'No candidates in {month}')
        ticker, signal_return = ordered[0]
        entry = float(prices.loc[(buy,ticker), 'adjusted_open'])
        if not math.isfinite(entry) or entry <= 0: raise ValueError(f'Missing executable open: {buy} {ticker}; no silent substitution')
        quantity = amount / entry; units[ticker] = units.get(ticker,0) + quantity
        spy_entry = float(spy.loc[buy,'adjusted_open']); spy_units += amount / spy_entry
        terminal = float(last.loc[ticker,'adj_close']) if last.loc[ticker,'date'] >= asof else 0.0
        final = quantity * terminal
        lots.append(dict(buy_date=str(buy.date()), signal_date=str(signal.date()), ticker=ticker, previous_month_return=float(signal_return), entry_adj_open=entry, contribution=amount, adjusted_units=quantity, ending_marked_value=final, spy_ending_value=amount*float(spy.loc[asof,'adj_close'])/spy_entry, last_price_date=str(last.loc[ticker,'date'].date()), status='current price' if terminal else 'written off ($0 rule)'))
        value = 0.0
        for t, qty in units.items():
            if last.loc[t,'date'] >= end:
                mark = marks.loc[end,t]
                if not math.isfinite(mark): raise ValueError(f'Unexplained missing holding mark: {end} {t}')
                value += qty * mark
        monthly.append(dict(date=str(end.date()), buy_date=str(buy.date()), winner=ticker, previous_month_return=float(signal_return), members=len(eligible), ranked_members=len(returns), coverage=len(returns)/len(eligible), missing_tickers=';'.join(missing), contribution=amount, cumulative_contributions=(i+1)*amount, strategy_marked_value=value, spy_value=spy_units*float(spy.loc[end,'adj_close'])))
        rankings.extend(dict(signal_date=str(signal.date()), ticker=t, rank=r+1, total_return=float(ret)) for r,(t,ret) in enumerate(ordered))
    ledger = pd.DataFrame(lots); path = pd.DataFrame(monthly)
    total = float(ledger.ending_marked_value.sum()); benchmark = float(ledger.spy_ending_value.sum())
    for col, terminal_value in [('strategy_marked_value',total), ('spy_value',benchmark)]:
        if abs(path[col].iloc[-1]-terminal_value) > .01: raise AssertionError('Lot/path reconciliation failed')
    if len(ledger)!=346 or not (pd.to_datetime(ledger.signal_date)<pd.to_datetime(ledger.buy_date)).all(): raise AssertionError('Invalid contribution schedule')
    for key, value in [('strategy_marked_value', total), ('spy_value', benchmark)]:
        if abs(value-reference[key]*amount/1000) > .01: raise AssertionError('Reference reconciliation failed: '+key)
    holdings = ledger.groupby('ticker').agg(purchases=('contribution','size'), invested=('contribution','sum'), marked_value=('ending_marked_value','sum')).reset_index().sort_values('marked_value',ascending=False)
    holdings['portfolio_weight'] = holdings.marked_value/total
    summary = dict(status='Reproduced approximation; true full-universe result unavailable', as_of=str(asof.date()), purchases=len(ledger), contributed=float(ledger.contribution.sum()), strategy_value=total, spy_value=benchmark, strategy_money_weighted_return=annual_return(ledger.buy_date,ledger.contribution,asof,total), spy_money_weighted_return=annual_return(ledger.buy_date,ledger.contribution,asof,benchmark), day_basis=365.25, incomplete_months=int(path.coverage.lt(1).sum()), original_input_hashes_verified=True)
    destination.mkdir(parents=True,exist_ok=True)
    for name, frame in [('purchase_ledger',ledger),('monthly_results',path),('holdings',holdings),('monthly_rankings',pd.DataFrame(rankings))]: frame.to_csv(destination/(name+'.csv'),index=False)
    (destination/'summary.json').write_text(json.dumps(summary,indent=2))
    return summary

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive', type=Path, default=ROOT/'data/Backtest_Data_and_Code.zip')
    ap.add_argument('--output', type=Path, default=ROOT/'reproduced')
    ap.add_argument('--allow-incomplete', action='store_true')
    ap.add_argument('--monthly', type=float, default=1000.0)
    args = ap.parse_args()
    print(json.dumps(run(args.archive,args.output,args.allow_incomplete,args.monthly),indent=2))
