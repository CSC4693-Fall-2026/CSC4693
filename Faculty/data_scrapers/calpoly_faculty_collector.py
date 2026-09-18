#!/usr/bin/env python3
"""Export Cal Poly's public catalog faculty and emeriti listings to CSV.

The public catalog's first table cell is rendered as ``NAME (YEAR)`` followed
by the department.  This collector preserves the other catalog text verbatim
(apart from whitespace normalization) and splits that cell into name,
year_hired, and department columns.

This script was created by ChatGPT
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

CATALOG_URL = "https://catalog.calpoly.edu/faculty-staff/"
USER_AGENT = "CalPolyFacultyCatalogCollector/1.0 (+contact: replace-with-your-email)"
DIRECTORY_ROOTS = (
    "https://ceng.calpoly.edu/about/directory",
    "https://cafes.calpoly.edu/about/faculty-and-staff-directory",
    "https://cla.calpoly.edu/about/departments-and-programs",
    "https://bailey.calpoly.edu/about/departments",
    "https://maritime.calpoly.edu/",
    "https://caed.calpoly.edu/faculty-and-staff",
    "https://orfalea.calpoly.edu/about-us/directory",
)
CAFES_ROSTER_URL = "https://dev-calpoly-cafes.pantheonsite.io/sites/default/files/2026-08/Fall%20Roster%202026.pdf"


@dataclass(frozen=True)
class FacultyRecord:
    name: str
    year_hired: str
    department: str
    position: str
    education: str
    email: str
    phone: str
    catalog_section: str
    name_raw: str
    source_url: str
    retrieved_at: str


def clean(value: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", unescape(value).replace("\xa0", " ")).strip()


class CatalogParser(HTMLParser):
    """Read HTML tables plus their nearest preceding H2 heading."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section = ""
        self._heading: list[str] | None = None
        self.tables: list[tuple[str, list[list[str]]]] = []
        self._table_depth = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h2": self._heading = []
        if self._heading is not None and tag == "br": self._heading.append(" ")
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1: self._rows = []
        elif self._table_depth and tag == "tr": self._row = []
        elif self._table_depth and tag in {"td", "th"} and self._row is not None: self._cell = []
        elif self._cell is not None and tag == "br": self._cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._heading is not None:
            self.section, self._heading = clean("".join(self._heading)), None
        if self._table_depth and tag in {"td", "th"} and self._cell is not None:
            assert self._row is not None
            self._row.append(clean("".join(self._cell)))
            self._cell = None
        elif self._table_depth and tag == "tr" and self._row is not None:
            if self._row: self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if not self._table_depth: self.tables.append((self.section, self._rows))

    def handle_data(self, data: str) -> None:
        if self._heading is not None: self._heading.append(data)
        if self._cell is not None: self._cell.append(data)


def parse_identity(value: str) -> tuple[str, str, str]:
    """Parse a first table cell: ``Surname, Given (YYYY)`` then department."""
    parts = [clean(part) for part in value.split("\n") if clean(part)]
    name_raw = parts[0] if parts else ""
    department = " ".join(parts[1:])
    match = re.fullmatch(r"(.*?)\s*\((\d{4})\)\s*", name_raw)
    if not match:
        return name_raw, "", department
    return clean(match.group(1)), match.group(2), department


def parse_catalog(html: str, source_url: str) -> list[FacultyRecord]:
    parser = CatalogParser(); parser.feed(html); parser.close()
    timestamp = datetime.now(UTC).isoformat()
    records: list[FacultyRecord] = []
    for section, rows in parser.tables:
        if not rows: continue
        headers = [cell.casefold() for cell in rows[0]]
        if not {"name", "position", "education"}.issubset(headers): continue
        name_i, position_i, education_i = (headers.index(key) for key in ("name", "position", "education"))
        for row in rows[1:]:
            if len(row) <= max(name_i, position_i, education_i):
                logging.warning("Skipping malformed catalog row: %r", row); continue
            name, year_hired, department = parse_identity(row[name_i])
            records.append(FacultyRecord(name, year_hired, department, row[position_i], row[education_i], "", "",
                                         section, row[name_i], source_url, timestamp))
    return records


class DirectoryParser(HTMLParser):
    """Extract links and personnel blocks from Cal Poly's Drupal directories."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.blocks: list[tuple[str, str]] = []
        self._heading_level = 0
        self._heading: list[str] | None = None
        self._body: list[str] | None = None
        self._in_heading = False
        self._link_href: str | None = None
        self._link_text: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self._link_href, self._link_text = attributes["href"], []
        if tag in {"h3", "h4"}:
            if self._heading is not None:
                self.blocks.append((clean("".join(self._heading)), clean("".join(self._body or []))))
            self._heading_level, self._heading, self._body, self._in_heading = int(tag[1]), [], [], True
        elif tag == "br" and self._body is not None:
            self._body.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h3", "h4"} and self._heading is not None and int(tag[1]) == self._heading_level:
            # Keep collecting the card body; it ends at the next card heading.
            self._in_heading = False
        if tag == "a" and self._link_href is not None:
            self.links.append((self._link_href, clean("".join(self._link_text or []))))
            self._link_href, self._link_text = None, None

    def handle_data(self, data: str) -> None:
        if self._link_text is not None: self._link_text.append(data)
        if self._heading is not None and self._in_heading:
            self._heading.append(data)
        elif self._body is not None:
            self._body.append(data)

    def close(self) -> None:
        super().close()
        if self._heading is not None:
            self.blocks.append((clean("".join(self._heading)), clean("".join(self._body or []))))
            self._heading = None


ACADEMIC_ROLE = re.compile(r"\b(professor|lecturer|instructor|faculty|department chair|department head)\b", re.I)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}")


def directory_department(url: str, fallback: str) -> str:
    """Turn a directory URL into a readable department when cards omit it."""
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if slug in {"directory", "faculty-and-staff", "faculty-and-staff-directory"}: return fallback
    return clean(slug.replace("-", " ")).title()


def parse_directory(html: str, source_url: str, college: str) -> tuple[list[FacultyRecord], list[tuple[str, str]]]:
    parser = DirectoryParser(); parser.feed(html); parser.close()
    timestamp, records = datetime.now(UTC).isoformat(), []
    for name, body in parser.blocks:
        if not name or not ACADEMIC_ROLE.search(body): continue
        lines = [clean(line) for line in body.split("\n") if clean(line)]
        role = next((line for line in lines if ACADEMIC_ROLE.search(line)), "")
        email = next(iter(EMAIL.findall(body)), "")
        phone_match = PHONE.search(body)
        department = directory_department(source_url, college)
        # These directories usually print the department immediately after title.
        if role in lines:
            after_role = lines[lines.index(role) + 1:]
            candidate = next((line for line in after_role if line not in {"Contact", college} and not EMAIL.search(line)
                              and not PHONE.search(line) and not line.lower().startswith(("building", "office"))), "")
            if candidate: department = candidate
        records.append(FacultyRecord(name, "", department, role, "", email,
                                     phone_match.group(0) if phone_match else "", "Department directory", name,
                                     source_url, timestamp))
    return records, parser.links


def is_directory_link(url: str, label: str, source_url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc.endswith(".calpoly.edu"): return False
    text = f"{parsed.path} {label}".casefold()
    # Directory landing pages also link to student groups, marketing, and
    # administrative offices.  They are not department faculty directories,
    # and some intentionally reject automated requests with HTTP 403.
    excluded = ("student", "ambassador", "career", "advancement", "giving", "advising", "council", "programs")
    if any(word in text for word in excluded): return False
    if any(word in text for word in ("directory", "faculty", "department", "academic-area")): return True
    # These college landing pages link to department home pages using only the
    # department name; keep that exception allow-listed rather than crawling
    # unrelated navigation, news, or alumni links.
    department_hosts = {
        "https://cla.calpoly.edu/about/departments-and-programs": {
            "artdesign.calpoly.edu", "coms.calpoly.edu", "english.calpoly.edu", "ethnicstudies.calpoly.edu",
            "grc.calpoly.edu", "history.calpoly.edu", "isla.calpoly.edu", "journalism.calpoly.edu",
            "laes.calpoly.edu", "music.calpoly.edu", "philosophy.calpoly.edu", "politicalscience.calpoly.edu",
            "psycd.calpoly.edu", "socialsciences.calpoly.edu", "theatredance.calpoly.edu", "wgqs.calpoly.edu",
        },
        "https://bailey.calpoly.edu/about/departments": {
            "bio.calpoly.edu", "chemistry.calpoly.edu", "kinesiology.calpoly.edu", "liberalstudies.calpoly.edu",
            "math.calpoly.edu", "physics.calpoly.edu", "soe.calpoly.edu", "statistics.calpoly.edu", "maritime.calpoly.edu",
        },
        "https://caed.calpoly.edu/faculty-and-staff": {
            "arce.calpoly.edu", "architecture.calpoly.edu", "planning.calpoly.edu", "construction.calpoly.edu", "landscape.calpoly.edu",
        },
    }
    return parsed.netloc in department_hosts.get(source_url, set())


def collect_directories(delay: float, max_pages: int) -> list[FacultyRecord]:
    """Follow public, same-college directory links; never follows profile pages."""
    queue = [(url, urlparse(url).netloc.split(".")[0].upper()) for url in DIRECTORY_ROOTS]
    visited: set[str] = set(); records: list[FacultyRecord] = []
    while queue and len(visited) < max_pages:
        url, college = queue.pop(0)
        if url in visited or not robots_allow(url): continue
        visited.add(url); time.sleep(max(delay, 0))
        try:
            found, links = parse_directory(http_get(url), url, college)
        except (HTTPError, URLError, TimeoutError) as error:
            logging.warning("Could not retrieve directory %s: %s", url, error); continue
        records.extend(found)
        for href, label in links:
            candidate = urljoin(url, href).split("#", 1)[0]
            if candidate not in visited and is_directory_link(candidate, label, url):
                queue.append((candidate, college))
    logging.info("Visited %d public directory pages and found %d academic entries", len(visited), len(records))
    unique = {(r.name.casefold(), r.position.casefold(), r.department.casefold(), r.email.casefold()): r for r in records}
    return list(unique.values())


def http_get(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # nosec B310: user supplies a public catalog URL
        return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def http_get_bytes(url: str, timeout: int = 60) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed public roster URL
        return response.read()


def robots_allow(url: str) -> bool:
    parsed = urlparse(url)
    robots = RobotFileParser(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        robots.read()
        return robots.can_fetch(USER_AGENT, url)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not check robots.txt: {error}") from error


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, default=Path("output/cal_poly_faculty.csv"))
    cli.add_argument("--url", default=CATALOG_URL, help="Catalog URL; supports prior catalog editions.")
    cli.add_argument("--delay", type=float, default=1.0, help="Seconds to wait after checking robots.txt.")
    cli.add_argument("--skip-directories", action="store_true", help="Export only the academic catalog; omit college directories.")
    cli.add_argument("--max-directory-pages", type=int, default=100, help="Safety cap for public college directory pages.")
    args = cli.parse_args()
    if not robots_allow(args.url): raise SystemExit(f"robots.txt disallows collection of {args.url}")
    time.sleep(max(args.delay, 0))
    records = parse_catalog(http_get(args.url), args.url)
    if not records: raise SystemExit("No faculty rows found; the catalog structure may have changed.")
    if not args.skip_directories:
        records.extend(collect_directories(args.delay, max(args.max_directory_pages, 0)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(FacultyRecord.__annotations__))
        writer.writeheader(); writer.writerows(asdict(record) for record in records)
    print(f"Wrote {len(records):,} rows to {args.output}")


if __name__ == "__main__": main()
