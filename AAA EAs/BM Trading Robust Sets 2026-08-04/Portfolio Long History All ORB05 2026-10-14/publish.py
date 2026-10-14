"""Offline publication using the audited existing normalisation and guard models."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'Portfolio Long History 2026-10-08'
spec=importlib.util.spec_from_file_location('prior_long_publish',OLD/'publish.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p.ROOT=ROOT
if __name__=='__main__':p.main()
