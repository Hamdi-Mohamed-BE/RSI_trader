import native
case=dict(module=4);rows=[]
cases=[('parity-1y','2025.10.02','2026.10.02',150),
 ('full-3y','2023.10.02','2026.10.02',150),('full-5y','2021.10.02','2026.10.02',150),
 ('annual-2021','2021.10.02','2022.10.02',150),('annual-2022','2022.10.02','2023.10.02',150),
 ('annual-2023','2023.10.02','2024.10.02',150),('annual-2024','2024.10.02','2025.10.02',150),
 ('real-2026','2026.01.01','2026.10.02',150),
 ('delay500-1y','2025.10.02','2026.10.02',500),('delay500-6m','2026.04.02','2026.10.02',500)]
for name,start,end,delay in cases:
 rows+=native.batch(name,[case],start,end,model=4,delay=delay,symbol='XAUUSD')
 native.save(native.ROOT/'PROGRESS RESULTS.json',rows)
native.save(native.ROOT/'SUMMARY.json',rows)
