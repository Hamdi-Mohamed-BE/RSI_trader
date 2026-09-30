"""Static scientific parameter-plateau plots; no invented observations."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import search

ROOT=Path(__file__).resolve().parent

def main():
    files=[]
    for manifest in sorted(search.OUT.glob('*-plateau-*/manifest.json')):
        folder=manifest.parent
        if not (folder/'results.json').exists():continue
        spec=json.loads(manifest.read_text());rows=json.loads((folder/'results.json').read_text())
        axes=json.loads((ROOT/(folder.name+'-axes.json')).read_text())['axes']
        if len(axes)<2:continue
        x,y=axes[:2];z=axes[2] if len(axes)>2 else None
        xv=sorted({r['parameters'][x] for r in rows});yv=sorted({r['parameters'][y] for r in rows})
        zv=sorted({r['parameters'][z] for r in rows}) if z else [None]
        pfs=[r['net']['profit_factor'] for r in rows]
        base=rows[0]['parameters']
        price_unit='USD/oz' if spec['asset']=='XAU' else 'USD' if spec['asset']=='BTC' else 'index points'
        labels={'rr':'Target (initial R)','hold':'Maximum hold (minutes)','ttl':'Retest expiry (signal bars)',
                'atr':'ATR period (bars)','start':'Trail activation (initial R)',
                'sl':f"Initial stop ({['ATR multiple','% of price',price_unit,'configured units','configured units','configured units'][int(base['stop'])]})",
                'offset':f"Pending offset ({price_unit if base['entry']==3 else 'ATR multiple'})",'dist':'Trail distance (configured units)'}
        norm=TwoSlopeNorm(vmin=min(.999,min(pfs)),vcenter=1,vmax=max(1.001,max(pfs)))
        fig,axs=plt.subplots(1,len(zv),figsize=(3.5*len(zv)+1,3.9),squeeze=False,layout='constrained')
        for ax,zv0 in zip(axs[0],zv):
            grid=np.full((len(yv),len(xv)),np.nan)
            for r in rows:
                p=r['parameters']
                if z and p[z]!=zv0:continue
                a,b=yv.index(p[y]),xv.index(p[x]);assert np.isnan(grid[a,b])
                grid[a,b]=r['net']['profit_factor']
            im=ax.imshow(grid,origin='lower',aspect='auto',cmap='BrBG',norm=norm)
            ax.set_xticks(range(len(xv)),[f'{v:g}' for v in xv]);ax.set_yticks(range(len(yv)),[f'{v:g}' for v in yv])
            ax.set_xlabel(labels.get(x,x));ax.set_ylabel(labels.get(y,y))
            ax.set_title(f"{labels.get(z,z)} = {zv0:g}" if z else 'Joint neighborhood',fontsize=10)
            for (a,b),pf in np.ndenumerate(grid):
                if np.isfinite(pf):
                    color=im.cmap(im.norm(pf));lum=.2126*color[0]+.7152*color[1]+.0722*color[2]
                    ax.text(b,a,f'{pf:.2f}',ha='center',va='center',color='black' if lum>.55 else 'white',fontsize=11)
        positive=sum(r['net']['net_profit']>0 for r in rows)
        fig.suptitle(f"{spec['asset']} {spec['name']}: net profit-factor stability\nModel 1 development only | positive: {positive}/{len(rows)} | not validation",fontsize=12)
        fig.colorbar(im,ax=list(axs[0]),label='Net profit factor',shrink=.75)
        output=ROOT/(folder.name+'.png');fig.savefig(output,dpi=160);plt.close(fig);files.append(output.name)
    (ROOT/'CHARTS.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
    print(json.dumps(files))

if __name__=='__main__':main()
