# CSC 4693 — Student Pay Project

Our goal is to analyze and compare faculty compensation against post-graduation student earnings across academic departments in California public universities (UC and CSU systems).

## Data Sources

This project uses publicly available data, including:

- U.S. Department of Education College Scorecard data
- Transparent California employee salary data
- California State University data
- University of California data
- California Community College data
- Institution crosswalk and metadata files

## Repository Structure

```text
.
├── data/
│   └── scrapes/
│       └── Raw downloaded and scraped source data
│
├── processing/
│   ├── join/
│   │   ├── parquet_improvements.py
│   │   └── Scripts for joining datasets together
│   │
│   ├── student/
│   │   └── Data processing for student-related datasets
│   │
│   └── faculty/
│       ├── csu/
│       │   └── CSU-specific processing files
│       │
│       └── uc/
│           └── UC-specific processing files
│
├── exploration/
│   ├── student/
│   │   ├── Exploratory analysis of student data
│   │   └── output/
│   │       └── Student exploration outputs
│   │
│   └── faculty/
│       ├── Exploratory analysis of faculty data
│       └── output/
│           └── Faculty exploration outputs
│
├── viz/
│   ├── output/
│   │   └── Generated charts, figures, and visual outputs
│   │
│   └── scripts/
│       └── Visualization scripts
│
└── README.md

## Documentation

For full project details, visit our [Project Wiki](https://github.com/CSC4693-Fall-2026/CSC4693/wiki).
