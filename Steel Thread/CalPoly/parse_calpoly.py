from bs4 import BeautifulSoup
import csv
import re

majors = {
    "Aerospace Engineering",
    "Agricultural Business",
    "Agricultural Communication",
    "Agricultural Science",
    "Agricultural Systems Management",
    "Animal Science",
    "Anthropology and Geography",
    "Architectural Engineering",
    "Architecture",
    "Art and Design",
    "Biochemistry",
    "Biological Sciences",
    "Biomedical Engineering",
    "BioResource and Agricultural Engineering",
    "Business Administration",
    "Chemistry",
    "Child Development",
    "City and Regional Planning",
    "Civil Engineering",
    "Communication Studies",
    "Comparative Ethnic Studies",
    "Computer Engineering",
    "Computer Science",
    "Construction Management",
    "Dairy Science",
    "Economics",
    "Electrical Engineering",
    "English",
    "Environmental Earth and Soil Sciences",
    "Environmental Engineering",
    "Environmental Management and Protection",
    "Experience and Event Management",
    "Facilities Engineering Technology",
    "Food Science",
    "Forest and Fire Sciences",
    "General Engineering",
    "Graphic Communication",
    "History",
    "Industrial Engineering",
    "Industrial Technology and Packaging",
    "Interdisciplinary Studies",
    "International Strategy and Security",
    "Journalism",
    "Kinesiology",
    "Landscape Architecture",
    "Liberal Arts and Engineering Studies",
    "Liberal Studies",
    "Manufacturing Engineering",
    "Marine Engineering Technology",
    "Marine Sciences",
    "Marine Transportation",
    "Materials Engineering",
    "Mathematics",
    "Mechanical Engineering",
    "Microbiology",
    "Music",
    "Nutrition",
    "Oceanography",
    "Philosophy",
    "Physics",
    "Plant Sciences",
    "Political Science",
    "Psychology",
    "Public Health",
    "Sociology",
    "Software Engineering",
    "Spanish",
    "Statistics",
    "Theatre Arts",
    "Wine and Viticulture",
}

major_aliases = {
    "Agribusiness": "Agricultural Business",
    "Civil and Environmental Engineering": "Civil Engineering",
    "Chemistry and Biochemistry": "Biochemistry",
    "Computer Science; Liberal Arts and Engineering Studies": "Liberal Arts and Engineering Studies",
    "English (Cal Poly Maritime)": "English",
    "Interdisciplinary Studies in the Liberal Arts" : "Interdisciplinary Studies",
    "Natural Resources Management and Environmental Sciences" : "Environmental Management and Protection",
    "and Environmental Sciences" : "Environmental Earth and Soil Sciences",
    "and Information Systems" : "Computer Science",
}

def clean_major(value):
    """Return a standardized major name, or NULL for an empty value."""
    value = null_if_empty(value)

    if value == "NULL":
        return "NULL"

    # "Bailey College of Science and Mathematics, Mathematics -> Mathematics"
    if "," in value:
        value = value.rsplit(",", 1)[-1].strip()

    return major_aliases.get(value, value)

filename = "Steel Thread/CalPoly/calpoly_faculty_html.html"

def null_if_empty(value):
    if value is None or not value.strip():
        return "NULL"
    return value.strip()

def is_initial(token):
    """True for M, M., G.W., S.L., etc., but not full names."""
    return bool(
        re.fullmatch(r"[A-Za-z]", token) or
        re.fullmatch(r"(?:[A-Za-z]\.)+", token)
    )

with open(filename, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

table = soup.find("table", class_="tbl_facdir")

if table is None:
    print("Faculty table was not found.")

else:
    with open("Steel Thread/CalPoly/calpoly_faculty.csv", "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow([
            "First Name",
            "Middle Initial",
            "Last Name",
            "Year Hired",
            "Major",
            "Position",
            "Education"
        ])

        for row in table.find_all("tr"):
            cells = row.find_all("td")

            if len(cells) == 0:
                continue

            name_parts = list(cells[0].stripped_strings)

            position = null_if_empty(
                cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
            )
            education = null_if_empty(
                cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
            )

            first_line = name_parts[0] if len(name_parts) > 0 else ""
            second_line = name_parts[1] if len(name_parts) > 1 else ""

            match = re.match(
                r"^(?P<last>[^,]+),\s*(?P<name_part>.*?)\s*\((?P<year>\d{3,4})\)$",
                first_line
            )

            if match:
                last_name = null_if_empty(match.group("last"))
                year_hired = null_if_empty(match.group("year"))
                major = clean_major(second_line)

                # Remove nicknames in parentheses and suffix commas.
                name_part = re.sub(r"\([^)]*\)", "", match.group("name_part"))
                name_part = name_part.replace(",", " ").strip()
                tokens = name_part.split()

                # First non-initial token is the first name.
                first_name = next(
                    (token for token in tokens if not is_initial(token)),
                    "NULL"
                )
                first_name = null_if_empty(first_name)

                # Store all initials, including multiple initials, together.
                middle_initial = " ".join(
                    token.replace(".", "") for token in tokens if is_initial(token)
                )
                middle_initial = null_if_empty(middle_initial)

            else:
                # Records without a year.
                name_match = re.match(
                    r"^(?P<last>[^,]+),\s*(?P<name_part>.+)$",
                    first_line
                )

                if name_match:
                    last_name = null_if_empty(name_match.group("last"))
                    tokens = name_match.group("name_part").split()

                    first_name = next(
                        (token for token in tokens if not is_initial(token)),
                        "NULL"
                    )
                    middle_initial = " ".join(
                        token for token in tokens if is_initial(token)
                    )

                    first_name = null_if_empty(first_name)
                    middle_initial = null_if_empty(middle_initial)
                else:
                    first_name = "NULL"
                    middle_initial = "NULL"
                    last_name = "NULL"

                year_hired = "NULL"
                major = null_if_empty(second_line)

            writer.writerow([
                first_name,
                middle_initial,
                last_name,
                year_hired,
                major,
                position,
                education
            ])

    print("Finished writing calpoly_faculty.csv")