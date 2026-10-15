import re, sys

import polars as pl
import requests
from bs4 import BeautifulSoup

URL = "https://catalog.csusm.edu/content.php?catoid=12&navoid=2267"
SCHOOL = "California State University San Marcos"
EXTRA = r",? (?:Jr\.?|Sr\.?|II|III|IV)$|\s*\(.*?\)"

html = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else \
    requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
main = BeautifulSoup(html, "html.parser").find("td", class_="block_content")
for br in main.find_all("br"):
    br.replace_with("|")

rows, current = [], False
for el in main.find_all(["h2", "h3", "p"]):
    text = re.sub(r"\s+", " ", el.get_text()).strip()
    if el.name != "p":
        current = text == "Academic and Administrative Listing"
        continue
    lines = [s.strip() for s in text.split("|") if s.strip()]
    if not current or len(lines) < 2 or not el.find("strong") or "," not in lines[0]:
        continue
    nm = re.match(r"(.+?)\s*(?:\(\w+\))?$", lines[0]).group(1)
    last, first = [re.sub(EXTRA, "", s.strip()).strip() for s in nm.split(",", 1)]
    title, _, dept = [s.strip() for s in lines[1].partition(",")]
    dept = re.sub(r"^Department Chair, ", "", dept)
    rows.append(dict(name=f"{first} {last}", school=SCHOOL, department=dept or None, title=title, major=None))

df = pl.DataFrame(rows, schema_overrides={"major": pl.Utf8}).unique(subset=["name"], maintain_order=True)
(df.filter(pl.col("title").str.contains("Professor|Librarian"))
   .with_columns(pl.col("name").str.replace_all(r" (?:[A-Za-z]\.? )+", " "))
   .select("name", "school", "department", "title", "major")
   .write_parquet("csusm_cleaned.parquet", compression="zstd"))
