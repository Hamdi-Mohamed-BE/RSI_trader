"""Do not tune settings: compare locked candidates at 250ms and repeat random delay."""
import json
from native import ROOT,PAIRS,compile_ea,run
def main():
    choices=json.loads((ROOT/'selection.json').read_text());compile_ea()
    for pair in PAIRS:
        c=choices[pair]['config']
        run(pair,'selected',c,'test',0,250)
        for i in (1,2):run(pair,f'selected-repeat{i}',c,'test',0)
if __name__=='__main__':main()
