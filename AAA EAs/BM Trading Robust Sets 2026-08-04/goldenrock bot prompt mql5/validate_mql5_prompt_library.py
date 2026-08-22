from pathlib import Path
import sys

out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd() / "goldenrock bot prompt mql5"
index = out_dir / "00 - GOLDENROCK MQL5 PROMPT INDEX.txt"
files = sorted([p for p in out_dir.glob("*.txt") if p.name != index.name])
errors = []

if not index.exists():
    errors.append("missing index file")

expected = 0
if index.exists():
    lines = index.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if line.startswith("Templates discovered:"):
            try:
                expected = int(line.split(":", 1)[1].strip())
            except ValueError:
                errors.append("could not parse template count from index")
            break

if len(files) != expected:
    errors.append(f"expected {expected} prompt files, found {len(files)}")

seen = set()
for file in files:
    key = file.name.lower()
    if key in seen:
        errors.append(f"duplicate filename: {file.name}")
    seen.add(key)
    text = file.read_text(encoding="utf-8")
    lower = text.lower()
    checks = [
        "strategy blueprint",
        "metaTrader 5 / mql5",
        "direct complete code",
        "risk engine",
        "entry engine",
        "stop-loss engine",
        "take-profit engine",
        "non-repainting requirement",
        "compilable",
    ]
    for check in checks:
        if check.lower() not in lower:
            errors.append(f"{file.name}: missing {check}")
    if "target:" in lower and "metaTrader 5 / mql5 expert advisor".lower() not in lower:
        errors.append(f"{file.name}: contains unintended non-MQL5 target")
    if len(text.strip()) < 2000:
        errors.append(f"{file.name}: unexpectedly short")

if errors:
    print("\n".join(errors))
    raise SystemExit(1)

print(f"PASS: {len(files)} prompt files validated")
