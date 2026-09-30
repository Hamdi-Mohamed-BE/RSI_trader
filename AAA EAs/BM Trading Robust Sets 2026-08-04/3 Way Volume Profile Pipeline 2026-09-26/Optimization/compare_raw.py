"""Unoptimized same-window reference, never uses the reserved holdout."""
import os
from pathlib import Path
import search

lock=Path(__file__).resolve().parent.parent/'.qualification.lock'
fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
os.write(fd,str(os.getpid()).encode()); os.close(fd)
try:
    result=search.batch('XAUUSD','raw-validation',[search.BASE],start='2024.09.26',end='2025.09.26',model=4,optimize=False)
    print(result[0]['metrics'])
finally:
    lock.unlink(missing_ok=True)
