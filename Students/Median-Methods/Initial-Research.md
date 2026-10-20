# Research notes on combining student salary medians

## What I worked on

I looked at three ways to combine the student salary medians into department buckets. I wanted to see how much the method changes the result and which one makes the most sense for the project.

I used the student earnings file Kaitlyn shared, which had 4,407 rows. I kept schools, degree levels, and years after graduation separate so I would not mix different groups together. I also fixed the extra spaces in bucket names and the spelling of Medicine and Health Sciences. I left missing salaries out of the calculations instead of counting them as zero.

## The three methods

| Method | How it works | What is useful about it | What to watch for |
| --- | --- | --- | --- |
| Mean of medians | Add the program medians and divide by the number of programs. | Easy to calculate and compare. | A program with very high or low earnings can pull the result up or down. Small and large programs count equally. |
| Median of medians | Put the program medians in order and take the middle value. | Less affected by unusually high or low program medians. | It treats small and large programs equally, so it describes the middle program rather than the middle student. |
| Weighted mean of medians | Give programs more weight when more people are included in their reported earnings count. | Takes the size of the earnings groups into account. | Large groups have more influence. It still does not give the exact median salary across individual graduates. |

For weighting, I matched the salary and count columns for the same time period. For example, four-year salaries use four-year earnings counts. I also compared the weighted and unweighted averages on the same records so the difference would come from the weighting itself.

## What changed in my tests

The code produced 1,395 comparisons, each for one school, degree level, bucket, and time after graduation. Of those, 601 had at least three salary records with usable earnings counts.

Some examples with large differences were:

| School and group | Time after graduation | Program records | Mean of medians | Weighted mean |
| --- | --- | ---: | ---: | ---: |
| CSU Fullerton, master's, Medicine and Health Sciences | 1 year | 4 | $96,491 | $126,207 |
| CSU Long Beach, master's, Medicine and Health Sciences | 5 years | 5 | $98,189 | $120,402 |
| San Diego State, bachelor's, Medicine and Health Sciences | 1 year | 6 | $44,114 | $65,619 |

I picked these examples because the methods gave noticeably different results. They show why the choice matters; not every bucket changes this much.

These are from my school-by-school tests. Yahir's chart combines UC and CSU bachelor's programs and looks at four-year earnings, so it uses a different grouping.

## What I recommend

I think median of medians is a reasonable choice if the report is describing a typical program in each bucket. It is less affected by programs with unusually high or low salary medians. I would still show the weighted mean as a comparison because it accounts for differences in group size.

The main thing is to label the result clearly. A median of program medians is not the same as the median salary of all students in that bucket. We only have the program summaries, not every student's salary. I also added a small made-up example to the code that shows why program medians and counts alone are not enough to work out that exact combined median.

Before using the numbers in the final report, I would confirm the data version and make sure both sets of tests use the same degree filters and duplicate-removal rules.

## Sources I looked at

- [Statistics Canada: Median definition](https://www150.statcan.gc.ca/n1/pub/81-004-x/def/4068724-eng.htm). Explains how the median is found from the middle of an ordered list of values.
- [McGrath et al., 2019: One-sample aggregate data meta-analysis of medians](https://pubmed.ncbi.nlm.nih.gov/30460713/). I read the abstract, which compares approaches for combining studies that report medians. It also discusses how skewed data and differences between groups affect the results.
- [McGrath et al., 2020: Estimating the sample mean and standard deviation from commonly reported quantiles in meta-analysis](https://pubmed.ncbi.nlm.nih.gov/32292115/). I read the abstract. The methods use medians along with other information, such as quartiles or ranges, to estimate means and standard deviations. They do not directly solve the problem of finding our exact combined student median.

## Running the code

From this folder, run:

```bash
python compare_methods.py student_input_snapshot.csv --output results.csv
```

The input CSV contains the columns used in my tests. `results.csv` has all the comparisons. `largest_weighting_changes.csv` lists the twenty largest weighting differences among groups with at least three usable weighted records.

I used ChatGPT to help with the comparison code.
