"""Additional native runs with new report identities; no production deployment."""
import shutil
from run_native import ROOT,run
from parse_native import parse
for name in ('NativeFullBest','NativeTrainSelected'):parse(name)
for source,name,start,delay in [('NativeBaseline','NativeBaselineHoldout','2026.05.19',1),('NativeTrainSelected','NativeTrainHoldout','2026.05.19',1),('NativeBaseline','NativeBaselineDelay250','2025.09.19',250),('NativeFullBest','NativeFullBestDelay250','2025.09.19',250)]:
 shutil.copy2(ROOT/(source+'.mq5'),ROOT/(name+'.mq5'))
 run(name,delay,start);parse(name)
