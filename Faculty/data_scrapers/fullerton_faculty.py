import re, sys

import polars as pl
import requests
from bs4 import BeautifulSoup

URL = "https://catalog.fullerton.edu/content.php?catoid=101&navoid=15092"
SCHOOL = "California State University, Fullerton"
RANK = r"((?:Assist\w+ |Assoc\w+ )?Professor|Lecturer|(?:Senior Assistant |Associate )?Librarian)"
EXTRA = r",? (?:Jr\.?|Sr\.?|II|III|IV)$|\s*\(.*?\)"
DEGREE = r"\s+(?=(?:[A-Z][a-z]?\.){2,}|Ph\.D|Ed\.D|MBA\b)"

html = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else \
    requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
main = BeautifulSoup(html, "html.parser").find("td", class_="block_content")
for br in main.find_all("br"):
    br.replace_with("|")

rows = []
for p in main.find_all("p"):
    lines = [s.strip() for s in re.sub(r"\s+", " ", p.get_text().replace("​", "")).split("|")]
    head = lines[0]
    m = re.match(r"(.+?)\s*\(\s*(\d{4})\s*\)\s*,?\s*(.*)", head)
    if not m and re.search(RANK, head):
        m = re.match(r"([^,]+,[^,]+?)()\s*,\s*(.*)", head)
    if not m:
        continue
    nm, _, raw = m.groups()
    if len(lines) == 1:
        raw = re.split(DEGREE, raw)[0]
    last, first = [re.sub(EXTRA, "", s.strip(" ,")).strip() for s in (nm.split(",", 1) if "," in nm else nm.split(" ", 1))]

    seg = re.split(r"[;:]", raw)[0].strip(" ,")
    m = re.match(rf"{RANK}(?: (?:of|in) (.+))?$", seg)
    title, dept = m.groups() if m else (seg.partition(", ")[0], seg.partition(", ")[2])
    title = re.sub(r"Assoc\w+ P", "Associate P", re.sub(r"Assist\w+ P", "Assistant P", title))
    rows.append(dict(name=f"{first} {last}", school=SCHOOL, department=dept or None, title=title or None,
                     major=None, raw=raw or None))

df = pl.DataFrame(rows, schema_overrides={"major": pl.Utf8}).unique(subset=["name", "raw"], maintain_order=True)
(df.filter(pl.col("title").str.contains("Professor|Librarian") | (pl.col("title") == "Lecturer"))
   .with_columns(pl.col("name").str.replace_all(r" (?:[A-Za-z]\.? )+", " "))
   .select("name", "school", "department", "title", "major")
   .write_parquet("fullerton_cleaned.parquet", compression="zstd"))
