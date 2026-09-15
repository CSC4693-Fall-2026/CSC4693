"""
This script standardizes the majors referenced in Scorecard
so that they align with the categories used for Cal Poly.
"""
import pandas as pd

category_to_major = {
    "Agricultural Business and Management": "Agricultural Business",
    "Animal Sciences": "Animal Science",
    "Food Science and Technology": "Food Science",
    "Plant Sciences": "Plant Sciences",

    "Architecture": "Architecture",
    "City/Urban, Community, and Regional Planning": "City and Regional Planning",
    "Landscape Architecture": "Landscape Architecture",
    "Architectural Sciences and Technology": "Architectural Engineering",

    "Ethnic, Cultural Minority, Gender, and Group Studies":
        "Comparative Ethnic Studies",
    "Communication and Media Studies": "Communication Studies",
    "Journalism": "Journalism",
    "Graphic Communications": "Graphic Communication",

    "Computer and Information Sciences, General": "Computer Science",
    "Computer Science": "Computer Science",

    "Engineering, General": "General Engineering",
    "Aerospace, Aeronautical, and Astronautical/Space Engineering":
        "Aerospace Engineering",
    "Agricultural Engineering": "BioResource and Agricultural Engineering",
    "Architectural Engineering": "Architectural Engineering",
    "Biomedical/Medical Engineering": "Biomedical Engineering",
    "Civil Engineering": "Civil Engineering",
    "Computer Engineering": "Computer Engineering",
    "Electrical, Electronics, and Communications Engineering":
        "Electrical Engineering",
    "Environmental/Environmental Health Engineering":
        "Environmental Engineering",
    "Materials Engineering": "Materials Engineering",
    "Mechanical Engineering": "Mechanical Engineering",
    "Industrial Engineering": "Industrial Engineering",
    "Manufacturing Engineering": "Manufacturing Engineering",

    "Foods, Nutrition, and Related Services": "Nutrition",
    "Nutrition Sciences": "Nutrition",
    "Dietetics and Clinical Nutrition Services": "Nutrition",
    "Human Development, Family Studies, and Related Services":
        "Child Development",

    "English Language and Literature, General": "English",
    "Rhetoric and Composition/Writing Studies": "English",
    "Liberal Arts and Sciences, General Studies and Humanities":
        "Liberal Studies",

    "Biology, General": "Biological Sciences",
    "Biochemistry, Biophysics and Molecular Biology": "Biochemistry",
    "Microbiological Sciences and Immunology": "Microbiology",
    "Mathematics": "Mathematics",
    "Statistics": "Statistics",
    "Marine Sciences": "Marine Sciences",
    "Multi/Interdisciplinary Studies, Other": "Interdisciplinary Studies",

    "Sports, Kinesiology, and Physical Education/Fitness": "Kinesiology",
    "Philosophy": "Philosophy",
    "Chemistry": "Chemistry",
    "Geological and Earth Sciences/Geosciences":
        "Environmental Earth and Soil Sciences",
    "Physics": "Physics",
    "Psychology, General": "Psychology",

    "Economics": "Economics",
    "Political Science and Government": "Political Science",
    "Sociology": "Sociology",
    "Drama/Theatre Arts and Stagecraft": "Theatre Arts",
    "Fine and Studio Arts": "Art and Design",
    "Music": "Music",
    "Public Health": "Public Health",

    "Business/Commerce, General": "Business Administration",
    "Business Administration, Management and Operations":
        "Business Administration",
    "Construction Management": "Construction Management",
    "History": "History",
}

df = pd.read_csv("Steel Thread/for_analysis/ca_collegescore.csv")

calpoly_df = df[df["INSTNM"] == "California Polytechnic State University-San Luis Obispo"]

calpoly_df["Major"] = (
    df["CIPDESC"]
    .astype("string")
    .str.strip()
    .str.rstrip(".")
    .map(category_to_major)
)
calpoly_df = (
    calpoly_df
    .dropna(subset=["Major"])
    .drop(
        columns=["CIPDESC", "UNITID", "OPEID6", "INSTNM", "CONTROL", "MAIN", "CIPCODE", "CREDLEV"]
    )
)

print(calpoly_df["Major"].unique())

calpoly_df = calpoly_df[
    ["Major"] + [col for col in calpoly_df.columns if col != "Major"]
]


calpoly_df.to_csv("Steel Thread/for_analysis/calpoly_scorecard.csv", index=False)