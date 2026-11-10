
from pathlib import Path
import json
import html
import re

HERE = Path(__file__).resolve().parent
HTML_PATH = HERE / "index.html"
DATA_PATH = HERE / "golden_campus_earnings.json"

# Load the 32 golden campus records
records = json.loads(DATA_PATH.read_text(encoding="utf-8"))

# Keep original HTML backup
backup = HERE / "index_before_golden.html"
if not backup.exists():
    backup.write_bytes(HTML_PATH.read_bytes())

# Build JavaScript array (HTML-escaped because it's inside data-srcdoc)
js_array = json.dumps(records, ensure_ascii=True, indent=2)
escaped_array = html.escape(js_array, quote=True)

source = HTML_PATH.read_text(encoding="utf-8")

# Replace only the embedded campus data array
pattern = r"(const data = \[).*?(\];\s*const labels =)"
replacement = (
    r"\g<1>\n"
    + escaped_array[1:-1]
    + r"\n  \g<2>"
)

updated, count = re.subn(
    pattern,
    lambda match: (
        match.group(1)
        + "\n"
        + escaped_array[1:-1]
        + "\n  "
        + match.group(2)
    ),
    source,
    count=1,
    flags=re.DOTALL,
)

if count != 1:
    raise RuntimeError(
        f"Expected one data array, found {count}. No changes saved"
    )

HTML_PATH.write_text(updated, encoding="utf-8")

print("Updated campus records:", len(records))
print("Backup:", backup)
print("Updated:", HTML_PATH)
