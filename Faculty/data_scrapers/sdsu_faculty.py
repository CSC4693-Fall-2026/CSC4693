import re, sys

import polars as pl
import requests
from bs4 import BeautifulSoup

URL = "https://caa.sdsu.edu/curriculum/faculty-listing"
SCHOOL = "San Diego State University"
SECTIONS = {"Tenured": "tenure_track", "Additional": "tenure_track", "Lecturers": "lecturer",
            "Adjunct": "adjunct", "Emeritus": "emeritus"}
DEGREE = r"(?:[A-Z][A-Za-z]{0,5}\.){1,4}[A-Za-z]{0,3}\.?|Doctor of\.?|Ph\.? ?D\.?|MFA|MBA|MA|MS|JD|DPT|DNP"
ADMIN = r"Director|President|Dean|Chair|Coordinator|Provost|Program|Advis|Professor"
RANK = r"((?:Distinguished |Assistant |Associate )?(?:Professor|Librarian)|Lecturer|Counselor)"

html = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else \
    requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
main = BeautifulSoup(html, "html.parser").find("main")

rows, cat = [], None
for el in main.find_all(["h2", "li"]):
    text = re.sub(r"\s+", " ", el.get_text(" ", strip=True).replace("​", "")).replace(" ,", ",")
    if el.name == "h2":
        cat = next((v for k, v in SECTIONS.items() if text.startswith(k)), None)
        continue
    if cat is None or text.count(",") < 1:
        continue
    last, first, *rest = [p.strip() for p in text.split(",", 2)]
    rest = rest[0] if rest else ""
    if re.fullmatch(r"II|III|IV|Jr\.?|Sr\.?", first):
        first, _, rest = (p.strip() for p in rest.partition(","))
    if re.match(RANK, first) and " " in last:
        rest, (first, last) = f"{first}, {rest}", last.rsplit(" ", 1)
    m = re.search(rf"(?:(?<=[a-z])\.)? (?={RANK}|Associate Dean)", first)
    if m:
        first, rest = first[:m.start()], f"{first[m.end():]}, {rest}"
    first = re.sub(r"^(?:MSG|LTC|CPT|Capt|Maj|Col|SFC|FNU) |\s*\(.*", "", first).strip()
    rest = re.split(r"\s*\((?=[A-Z])|\s(?=B\.[AS]\.,)", rest)[0]
    rest = re.sub(r",? SDSU Imperial Valley", "", rest)

    title, dept = None, None
    if cat in ("lecturer", "adjunct"):
        dept = re.sub(rf"^(?:(?:{DEGREE})[,;/ ]*)+", "", rest).strip(" ,.;(") or None
        title = "Lecturer" if cat == "lecturer" else "Adjunct"
    else:
        rest = re.sub(r"^(?:[A-Z][A-Za-z]*\.?[A-Z]?\.?, )?\d{4}-\d{4}, ", "", rest)
        m = re.search(rf"{RANK}s?(?: (?:of|in|,) (.+))?", rest)
        if m:
            title = m.group(1)
            dept = re.split(r",? and (?:Interim |Assistant |Associate |Vice |Director|Chair|Dean|Professor)|"
                            r"; |, (?:The|Director|Chair|Dean|Emerit)", m.group(2) or "")[0].strip(" ,.;(") or None
            if dept:
                parts = re.sub(r"\s*\[.*?\]", "", dept).split(", ")
                cut = next((i for i, p in enumerate(parts) if re.search(ADMIN, p)), len(parts))
                dept = ", ".join(parts[:cut]).strip(" ,.;(") or None
    rows.append(dict(name=f"{first} {last}", school=SCHOOL, department=dept, title=title, major=None,
                     category="librarian" if cat == "tenure_track" and "Librarian" in (title or "") else cat))

df = pl.DataFrame(rows, schema_overrides={"major": pl.Utf8}).unique(subset=["name", "category"], keep="first", maintain_order=True)
(df.filter(pl.col("category").is_in(["tenure_track", "lecturer", "adjunct", "librarian"]) & pl.col("title").is_not_null())
   .with_columns(pl.col("name").str.replace_all(r" (?:[A-Za-z]\.? )+", " "))
   .select("name", "school", "department", "title", "major")
   .write_parquet("sdsu_cleaned.parquet", compression="zstd"))
