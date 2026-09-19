import shutil
from run_native import run,ROOT
from parse_native import parse
for name,source,start,delay in [
 ('NativeFullBestV2','NativeFullBestV2','2025.09.19',1),
 ('NativeTrainSelectedV2','NativeTrainSelectedV2','2025.09.19',1),
 ('NativeTrainHoldoutV2','NativeTrainSelectedV2','2026.05.19',1),
 ('NativeFullBestDelay250V2','NativeFullBestV2','2025.09.19',250),
]:
 if source!=name:shutil.copy2(ROOT/(source+'.mq5'),ROOT/(name+'.mq5'))
 run(name,delay,start)
 parse(name)
