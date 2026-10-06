"""Frozen logistic efficiency gate. No holdout fitting/threshold selection."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss,log_loss,accuracy_score
R=Path(__file__).resolve().parent
FEATURES=['er','er_mean5','er_mean20','abs_oc','signed_oc','range_pct','rv','mean_abs_ret','close_location','body_fraction','positive_fraction','overnight_gap','cc_vol5','cc_vol20','range_ratio5_20']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sessions(raw):
 d=raw.copy()
 assert d.time.is_unique and d.time.is_monotonic_increasing
 d['ny']=pd.to_datetime(d.time,unit='s',utc=True).dt.tz_convert('America/New_York')
 minute=d.ny.dt.hour*60+d.ny.dt.minute
 d=d[(d.ny.dt.weekday<5)&(minute>=570)&(minute<960)]
 rows=[]
 for day,b in d.groupby(d.ny.dt.strftime('%Y-%m-%d')):
  minutes=b.ny.dt.hour*60+b.ny.dt.minute
  complete=len(b)==78 and np.array_equal(minutes.to_numpy(),np.arange(570,960,5))
  if not complete:continue
  o=float(b.open.iloc[0]);c=float(b.close.iloc[-1]);hi=float(b.high.max());lo=float(b.low.min())
  prices=np.r_[o,b.close.to_numpy()];delta=np.diff(prices);lr=np.diff(np.log(prices))
  denom=np.abs(delta).sum();rng=hi-lo
  rows.append(dict(date=pd.Timestamp(day),available=int(b.time.iloc[-1])+300,open=o,close=c,er=abs(c-o)/denom if denom else 0,
    abs_oc=abs(c/o-1),signed_oc=c/o-1,range_pct=rng/o,rv=float(np.sqrt(np.sum(lr**2))),mean_abs_ret=float(np.mean(np.abs(lr))),
    close_location=(c-lo)/rng if rng else .5,body_fraction=abs(c-o)/rng if rng else 0,positive_fraction=float((delta>0).mean())))
 s=pd.DataFrame(rows).set_index('date').sort_index()
 s['er_mean5']=s.er.rolling(5).mean();s['er_mean20']=s.er.rolling(20).mean()
 s['overnight_gap']=s.open/s.close.shift(1)-1
 ret=s.close.pct_change()
 s['cc_vol5']=ret.rolling(5).std();s['cc_vol20']=ret.rolling(20).std()
 s['range_ratio5_20']=s.range_pct.rolling(5).mean()/s.range_pct.rolling(20).mean()
 return s
def make_forecasts(s):
 f=s.dropna(subset=FEATURES).reset_index().rename(columns={'date':'feature_date'})
 targets=pd.DataFrame({'date':pd.bdate_range('2020-01-01','2026-10-04')})
 z=pd.merge_asof(targets,f,left_on='date',right_on='feature_date',allow_exact_matches=False,direction='backward').dropna(subset=FEATURES)
 z=z.merge(s[['er']].rename(columns={'er':'target_er'}),left_on='date',right_index=True,how='left')
 assert (z.feature_date<z.date).all()
 entry=z.date.dt.tz_localize('America/New_York')+pd.Timedelta(hours=9,minutes=35)
 assert np.all(z.available.to_numpy()<entry.map(lambda t:t.timestamp()).to_numpy())
 return z
def main():
 raw=pd.read_csv(R/'data/USTEC-M5.csv.gz');s=sessions(raw);z=make_forecasts(s)
 train=(z.date<'2024-01-01')&z.target_er.notna()
 valid=(z.date>='2024-01-01')&(z.date<'2024-10-05')&z.target_er.notna()
 test=(z.date>='2024-10-05')&z.target_er.notna()
 assert train.sum()>=400,('Insufficient training',train.sum(),s.index.min())
 cut=float(z.loc[train,'target_er'].median());y=(z.target_er>=cut).astype(int)
 assert y[train].nunique()==2
 config=dict(features=FEATURES,C=1.,probability_cutoff=.5,training_target_er_median=cut,train_end_exclusive='2024-01-01',
  holdout_start='2024-10-05',data_sha256=sha(R/'data/USTEC-M5.csv.gz'),protocol_sha256=sha(R/'PROTOCOL.md'),model_source_sha256=sha(Path(__file__)))
 path=R/'model-frozen.json'
 if path.exists():assert json.loads(path.read_text())==config
 else:save(path,config)
 model=make_pipeline(StandardScaler(),LogisticRegression(C=1.,max_iter=3000,solver='lbfgs',random_state=20261005))
 model.fit(z.loc[train,FEATURES],y[train]);z['probability']=model.predict_proba(z[FEATURES])[:,1]
 z['ml_allow']=z.probability>=.5;z['lag_er_allow']=z.er>=cut;z['label_high']=np.where(z.target_er.notna(),y,np.nan)
 score={}
 prevalence=float(y[train].mean())
 for name,mask in [('train',train),('calibration_no_tuning',valid),('unseen_2y',test),('unseen_6m',test&(z.date>='2026-04-05')),('unseen_3m',test&(z.date>='2026-07-05'))]:
  yy=y[mask];p=z.loc[mask,'probability'];base=np.repeat(prevalence,len(yy))
  score[name]=dict(n=int(mask.sum()),first=z.loc[mask,'date'].min().strftime('%Y-%m-%d'),last=z.loc[mask,'date'].max().strftime('%Y-%m-%d'),
   auc=roc_auc_score(yy,p) if yy.nunique()==2 else None,brier=brier_score_loss(yy,p),baseline_brier=brier_score_loss(yy,base),
   brier_skill=1-brier_score_loss(yy,p)/brier_score_loss(yy,base),log_loss=log_loss(yy,p),
   accuracy=accuracy_score(yy,p>=.5),ml_days_allowed=int((p>=.5).sum()),mean_er_allowed=float(z.loc[mask&z.ml_allow,'target_er'].mean()),
   mean_er_blocked=float(z.loc[mask&~z.ml_allow,'target_er'].mean()))
 # Repeat exactly from frozen scalar weights, and verify changing future rows cannot change any prior feature.
 scaler=model.named_steps['standardscaler'];lr=model.named_steps['logisticregression']
 xx=(z[FEATURES].to_numpy()-scaler.mean_)/scaler.scale_;pp=1/(1+np.exp(-(xx@lr.coef_[0]+lr.intercept_[0])))
 assert np.allclose(pp,z.probability,atol=1e-12)
 mutation=raw.copy();pivot=int(pd.Timestamp('2026-07-05',tz='UTC').timestamp())
 mutation.loc[mutation.time>=pivot,['open','high','low','close']]*=1.17
 zp=make_forecasts(sessions(mutation));pre=z.date<'2026-07-05';np.testing.assert_allclose(z.loc[pre,FEATURES],zp.loc[zp.date<'2026-07-05',FEATURES],atol=0,rtol=0)
 z.to_csv(R/'forecasts.csv',index=False);s.to_csv(R/'sessions.csv')
 embed=z[z.date>='2024-10-05']
 def arr(name,typ,values):return f'{typ} {name}[]={{'+','.join(values)+'};\n'
 body='// Frozen past-only forecast. No realized target in executable.\n'
 body+=arr('ER_dates','int',[d.strftime('%Y%m%d') for d in embed.date])
 body+=arr('ER_available','long',[str(int(x)) for x in embed.available])
 body+=arr('ER_probability','double',[format(x,'.17g') for x in embed.probability])
 body+=arr('ER_lag_allow','int',['1' if x else '0' for x in embed.lag_er_allow])
 (R/'EA/Forecasts.mqh').write_text(body,encoding='utf-8')
 weights=dict(features=FEATURES,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coef=lr.coef_[0].tolist(),intercept=float(lr.intercept_[0]),training_prevalence=prevalence)
 save(R/'weights.json',weights)
 save(R/'MODEL.json',dict(config=config,score=score,data=dict(rows=len(raw),sessions=len(s),first=str(s.index.min()),last=str(s.index.max())),
  checks=dict(scalar_replay_equal=True,future_price_mutation_prior_features_unchanged=True,forecast_precedes_entry=True),forecast_sha256=sha(R/'forecasts.csv'),embedded_sha256=sha(R/'EA/Forecasts.mqh')))
 print(json.dumps(score,indent=2),flush=True)
if __name__=='__main__':main()
