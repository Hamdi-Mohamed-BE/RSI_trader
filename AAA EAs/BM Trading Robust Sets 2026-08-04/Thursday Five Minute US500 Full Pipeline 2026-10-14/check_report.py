from html.parser import HTMLParser
from pathlib import Path
import json
class Check(HTMLParser):
    def __init__(self):super().__init__();self.capture=False;self.search='';self.sections=0;self.svg=0;self.tables=0
    def handle_starttag(self,tag,attrs):
        self.sections+=tag=='h2';self.svg+=tag=='svg';self.tables+=tag=='table'
        if tag=='script' and dict(attrs).get('id')=='search-data':self.capture=True
    def handle_endtag(self,tag):
        if tag=='script':self.capture=False
    def handle_data(self,data):
        if self.capture:self.search+=data
p=Path(__file__).resolve().parent/'Results.html';body=p.read_text(encoding='utf-8');c=Check();c.feed(body);data=json.loads(c.search)
assert len(data)==8500 and c.svg==1 and c.sections==13 and c.tables==13
assert 'Tuesday 09:35' in body and '2024-10-14' in body and '39% real ticks' in body
print(dict(search_rows=len(data),sections=c.sections,tables=c.tables,html_bytes=p.stat().st_size,static_structure_pass=True,visual_preview='not performed: browser blocks local file URLs'))
