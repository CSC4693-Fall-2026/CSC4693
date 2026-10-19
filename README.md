# CSC4693
Official Repository for CSC4693 Fall Semester 2026

## Repository layout

```text
data/
  scrapes/       # raw collection sources and scrape inputs
  faculty/raw/   # local faculty source datasets
  student/       # local student source datasets
processing/
  faculty/
    csu/
    uc/
  student/
exploration/
  faculty/
viz/
  scripts/       # visualization source code
  output/        # generated visualizations (ignored)
tests/
  scripts/
```

Generated files belong in an `output/` directory. Output contents are ignored
by Git; the committed `.gitkeep` files retain the intended directory layout.
