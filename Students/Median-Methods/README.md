# Comparing student earnings methods

I looked at three ways to combine the program salary medians into department buckets: the mean of medians, median of medians, and a mean weighted by the earnings counts. I tested how the results changed and put together the method comparison and recommendation. Yahir made the bucket comparison chart, which I included in the report.

## What is in this folder

- [Report with the comparison table, chart, and recommendation](Student-Earnings-Methods.pdf)
- [Editable Word version](Student-Earnings-Methods.docx)
- [Research notes and sources](Initial-Research.md)
- [Comparison code](compare_methods.py)
- [Student data used for my initial tests](student_input_snapshot.csv)
- [Full results from my initial tests](results.csv)
- [Twenty largest weighting differences among groups with at least three weighted records](largest_weighting_changes.csv)
- [Summary to add to the Wiki](WIKI_TEXT.md)

## What I found

The method can change the salary shown for a bucket quite a bit. I recommend the median of program medians when the goal is to describe a typical program, since extreme program values affect it less. The weighted average is useful for comparison because it gives larger reported earnings cohorts more influence.

Neither one gives the exact median salary across individual graduates. The data contains program medians, not each graduate's salary, so I kept that distinction in the recommendation.

My initial tests keep each school, degree level, bucket, and time after graduation separate. Yahir's chart combines UC and CSU bachelor's programs and focuses on four-year earnings. The CSV results here are from my tests, so they are not the exact numbers in his chart.

## Run my comparison

From this folder:

```bash
python compare_methods.py student_input_snapshot.csv --output results.csv
```

The CSV version only needs Python's standard library. It leaves the input unchanged. It also checks a small made-up example showing how the same program medians and counts can lead to different combined student medians.

## Data and remaining checks

I used the 4,407-row student file Kaitlyn shared earlier. There is a student file modified October 17 in the Drive's `USE THIS DATA` folder, so the input version should be confirmed before using the results in the final report.

I included Yahir's chart from the screenshot he sent. I still need his code and results table to check the bachelor's filter, duplicate removal, and which earnings counts were used. The current student pipeline drops the degree-level column during cleanup, so that filter needs to happen while the identifier is still available.

I used ChatGPT to help with the comparison code.
