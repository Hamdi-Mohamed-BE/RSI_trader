"""Independent Python operationalisation used ONLY to verify native signals."""
import numpy as np

def classify(p,c,d):
 if p>=.65 and c>=.60 and d>=.25:return 1
 if p<=.35 and c<=.40 and d<=-.25:return -1
 if .35<=p<=.65 and .40<=c<=.60 and abs(d)<=.25:return 0
 return 9

def profile(frame):
 lo=float(frame.low.min());hi=float(frame.high.max());width=(hi-lo)/64
 assert width>0 and len(frame)==60 and (frame.tick_volume>0).all()
 edges=np.linspace(lo,hi,65);bins=np.zeros(64)
 for r in frame.itertuples():
  if r.high==r.low:
   bins[min(63,max(0,int(np.floor((r.close-lo)/width))))]+=r.tick_volume
  else:
   overlap=np.maximum(0,np.minimum(edges[1:],r.high)-np.maximum(edges[:-1],r.low))
   bins+=overlap*r.tick_volume/(r.high-r.low)
 total=float(frame.tick_volume.sum());assert np.isclose(bins.sum(),total,rtol=1e-11)
 p=int(np.argmax(bins));left=right=p;covered=bins[p]
 while covered<total*.7 and (left>0 or right<63):
  below=bins[left-1] if left else -1;above=bins[right+1] if right<63 else -1
  if above>=below and right<63:right+=1;covered+=bins[right]
  else:left-=1;covered+=bins[left]
 c=float(np.dot(bins,(np.arange(64)+.5)/64)/total)
 d=float((frame.close.iloc[-1]-frame.open.iloc[0])/(hi-lo))
 return dict(low=lo,high=hi,poc=lo+(p+.5)*width,val=lo+left*width,vah=lo+(right+1)*width,centroid=c,net_move=d,shape=classify((p+.5)/64,c,d),volume=total)

def context(bars):
 assert len(bars)==22
 h=bars.high.to_numpy();l=bars.low.to_numpy();c=bars.close.to_numpy()
 tr=np.maximum(h[7:21]-l[7:21],np.maximum(abs(h[7:21]-c[6:20]),abs(l[7:21]-c[6:20])))
 return float(tr.mean()),float(bars.tick_volume.iloc[1:21].mean())

def signal(r,previous_close,p,atr,volume,module):
 shape=p['shape'];lo=p['val'];hi=p['vah']
 inside=lo<r['close']<hi;bull=r['close']>r['open'];bear=r['close']<r['open']
 if module==1:
  buy=shape in (1,0) and r['low']<lo and inside and bull
  sell=shape in (-1,0) and r['high']>hi and inside and bear
 elif module==2:
  buy=shape==-1 and r['low']<lo and inside and bull and r['tick_volume']<=volume
  sell=shape==1 and r['high']>hi and inside and bear and r['tick_volume']<=volume
 else:
  prev=lo<=previous_close<=hi;strong=r['tick_volume']>=1.5*volume
  buy=shape in (1,0) and prev and strong and bull and r['close']>hi+.1*atr and r['close']-r['open']>=.5*atr
  sell=shape in (-1,0) and prev and strong and bear and r['close']<lo-.1*atr and r['open']-r['close']>=.5*atr
 return 0 if buy==sell else (1 if buy else -1)
