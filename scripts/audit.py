"""Independent full-input and workbook audit; uses only the supplied local files."""
from pathlib import Path
import pandas as pd, numpy as np, openpyxl, json, hashlib, math
import zipfile, tempfile
ROOT=Path(__file__).resolve().parents[1]
TEMP=tempfile.TemporaryDirectory()
R=Path(TEMP.name); I=R/'outputs/backtest_1998'; O=R/'outputs/final_backtest'
I.mkdir(parents=True); O.mkdir(parents=True)
with zipfile.ZipFile(ROOT/'data/Backtest_Data_and_Code.zip') as z:
 for folder,names in [(I,['price_endpoints.csv','price_marks.csv','terminal_quotes.csv','membership_intervals.csv','split_corrections.csv','frozen_input_hashes.json']), (O,['purchase_ledger.csv','monthly_results.csv','holdings.csv'])]:
  for name in names:
   (folder/name).write_bytes(z.read(str(folder.relative_to(R)/name)))
panel=pd.read_csv(I/'price_endpoints.csv',parse_dates=['date'])
marks=pd.read_csv(I/'price_marks.csv',index_col=0,parse_dates=[0])
last=pd.read_csv(I/'terminal_quotes.csv',parse_dates=['date']).set_index('ticker')
members=pd.read_csv(I/'membership_intervals.csv',parse_dates=['start','end'])
ledger=pd.read_csv(O/'purchase_ledger.csv',parse_dates=['buy_date','signal_date'])
monthly=pd.read_csv(O/'monthly_results.csv',parse_dates=['date','buy_date'])
for e in pd.read_csv(I/'split_corrections.csv',parse_dates=['date']).itertuples():
 panel.loc[(panel.ticker==e.ticker)&(panel.date<e.date),'adj_close']*=e.correction_factor
 marks.loc[marks.index<e.date,e.ticker]*=e.correction_factor
 if last.loc[e.ticker,'date']<e.date:last.loc[e.ticker,'adj_close']*=e.correction_factor
p=panel.set_index(['date','ticker']); close=panel.pivot(index='date',columns='ticker',values='adj_close')
spy=panel[panel.ticker=='SPY'].set_index('date').sort_index()
cal={str(m):(g.index.min(),g.index.max()) for m,g in spy.groupby(spy.index.to_period('M'))}
fail=[]; units={}; spunits=0; maxpath=0; maxlot=0; switches=[]; candidates=[]
for k,lot in ledger.iterrows():
 mon=lot.buy_date.to_period('M'); buy,end=cal[str(mon)]; signal=cal[str(mon-1)][1]; base=cal[str(mon-2)][1]
 eligible=set(members.loc[(members.start<=signal)&(members.end.isna()|(members.end>signal)),'ticker'])
 cand={t:float(close.loc[signal,t]/close.loc[base,t]-1) for t in sorted(eligible&set(close.columns)) if pd.notna(close.loc[signal,t]) and pd.notna(close.loc[base,t])}
 chosen=min(cand,key=lambda t:(-cand[t],t))
 if chosen!=lot.ticker or buy!=lot.buy_date or signal!=lot.signal_date:fail.append([k,'selection/date'])
 if abs(cand[chosen]-lot.previous_month_return)>1e-9:fail.append([k,'return'])
 entry=p.loc[(buy,chosen),'open']*p.loc[(buy,chosen),'adj_close']/p.loc[(buy,chosen),'close']
 q=1000/entry; units[chosen]=units.get(chosen,0)+q
 spe=spy.loc[buy,'open']*spy.loc[buy,'adj_close']/spy.loc[buy,'close']; spunits+=1000/spe
 final=q*last.loc[chosen,'adj_close'] if last.loc[chosen,'date']>=pd.Timestamp('2026-10-09') else 0
 val=sum(qty*marks.loc[end,t] for t,qty in units.items() if last.loc[t,'date']>=end and pd.notna(marks.loc[end,t]))
 maxpath=max(maxpath,abs(val-monthly.iloc[k].strategy_marked_value),abs(spunits*spy.loc[end,'adj_close']-monthly.iloc[k].spy_value))
 maxlot=max(maxlot,abs(final-lot.ending_marked_value))
 if len(cand)!=monthly.iloc[k].ranked_members or len(eligible)!=monthly.iloc[k].members:fail.append([k,'coverage'])
 buyeligible=set(members.loc[(members.start<=buy)&(members.end.isna()|(members.end>buy)),'ticker'])
 if chosen not in buyeligible:switches.append({'buy_date':str(buy.date()),'ticker':chosen})
 candidates.append({'buy_date':str(buy.date()),'eligible':len(eligible),'ranked':len(cand)})
def irr(total,basis=365.25):
 years=(pd.Timestamp('2026-10-09')-ledger.buy_date).dt.days.to_numpy()/basis
 lo,hi=-.99,2.
 for _ in range(160):
  mid=(lo+hi)/2
  if (1000*(1+mid)**years).sum()>total:hi=mid
  else:lo=mid
 return (lo+hi)/2
total=ledger.ending_marked_value.sum(); benchmark=ledger.spy_ending_value.sum()
f=openpyxl.load_workbook(ROOT/'data/Monthly_Winner_Backtest_1998.xlsx',data_only=False)
v=openpyxl.load_workbook(ROOT/'data/Monthly_Winner_Backtest_1998.xlsx',data_only=True)
wb_diff={}
for sheet,col,csvcol in [('Purchases','I','ending_marked_value'),('Purchases','L','spy_ending_value')]:
 wb_diff[sheet+'!'+col]=max(abs(v[sheet][f'{col}{k+7}'].value-row[csvcol]) for k,row in ledger.iterrows())
hashes=json.loads((I/'frozen_input_hashes.json').read_text())
out={'verdict':'Arithmetic reproduced; full-universe strategy unverified','checks':{'purchases':len(ledger),'contributions':float(ledger.contribution.sum()),'selection_or_date_or_coverage_failures':fail,'max_monthly_value_difference_dollars':maxpath,'max_lot_difference_dollars':maxlot,'input_hashes_match':{n:hashlib.sha256((I/n).read_bytes()).hexdigest()==h for n,h in hashes.items()},'workbook_max_lot_difference':wb_diff,'workbook_cached_errors':[(s.title,c.coordinate,c.value) for s in v for row in s for c in row if c.data_type=='e'],'duplicates':int(panel.duplicated(['date','ticker']).sum()),'nonpositive_prices':int((panel[['open','close','adj_close']]<=0).any(axis=1).sum())},'strategy_value':total,'spy_value':benchmark,'annualized_365_25':{'strategy':irr(total),'spy':irr(benchmark)},'excel_xirr_365':{'strategy':irr(total,365),'spy':irr(benchmark,365)},'incomplete_months':int((monthly.coverage<1).sum()),'first_month_coverage':candidates[0],'minimum_coverage':float(monthly.coverage.min()),'not_members_at_buy':switches,'missing_entry_count':int(ledger.adjusted_units.eq(0).sum()),'workbook_static_return_formulas':{'Summary!C12':f['Summary']['C12'].value,'Summary!D12':f['Summary']['D12'].value},'top_holdings':pd.read_csv(O/'holdings.csv').head(10).to_dict('records')}
(ROOT/'data/audit.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,indent=2,default=str))
