"""Publish compact lossless native exports, preserving local originals."""
from pathlib import Path
import gzip,hashlib,json
R=Path(__file__).resolve().parent
rows=[]
for p in sorted((R/'native').glob('*/*.csv')):
    q=p.with_suffix(p.suffix+'.gz');data=p.read_bytes();q.write_bytes(gzip.compress(data,mtime=0))
    assert gzip.decompress(q.read_bytes())==data
    rows.append(dict(source=str(p.relative_to(R)),archive=str(q.relative_to(R)),source_sha256=hashlib.sha256(data).hexdigest(),archive_sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
(R/'COMPRESSION.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(dict(native_exports=len(rows),lossless=True))
