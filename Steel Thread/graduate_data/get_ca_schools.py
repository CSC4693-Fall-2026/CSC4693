from bs4 import BeautifulSoup

filename = "graduate_data/2026 A-Z list of 130 California Universities _ uniRank.html"
names = []


with open(filename, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

    table = soup.find("table", class_="table table-hover")

    if table is None:
        print("Table 404")
        
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("th")

        if len(cells) == 0:
            continue

        name = cells[0].get_text(" ", strip=True)
        names.append(name)

with open("ca_universities", "w") as t:
    for n in names:
        t.write(f"{n}\n")
print(names)
