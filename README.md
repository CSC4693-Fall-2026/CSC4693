# CSC 4693 — Student Pay Project

> **Hook:** *"DID YOUR PROFESSORS TEACH YOU TO OUT-EARN THEM?"*  
> **Title:** **An Investigation into the Income Disparities Between New-Grads and Faculty**

Our goal is to analyze and compare faculty compensation against post-graduation student earnings across academic departments in California public universities (UC and CSU systems).

---

## Quick Links

* **Wiki & Policies:** [[How to Use the Wiki|Using-Wiki]] | [[AI Policy|AI-Policy]] | [[Meeting Minutes|Meeting-Minutes]]
* **Project Deliverables:** [Living Project Outline (SharePoint)](https://cpslo-my.sharepoint.com/:w:/g/personal/rbaweja_calpoly_edu/IQAs57NSzPAiSridoCDHpF6UAfZFq6WHwLPHHkIT3_tG0N4?e=sH9bFZ)
* **Design & Roadmap:** [[Project Roadmap & Research Questions|Project-Roadmap]] | [[Data Journalism & Viz Research|Report-and-Viz-Research]]

---

## Repository Structure

```text
.
├── data/
│   └── scrapes/
│       └── Raw downloaded and scraped source data
│
├── processing/
│   ├── join/
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
