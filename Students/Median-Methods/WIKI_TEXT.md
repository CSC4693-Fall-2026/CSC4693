## Student earnings aggregation methods

I worked with Yahir to compare the mean of program medians, median of program medians, and earnings-count-weighted mean of program medians. The goal was to see how the method changes bucket-level earnings summaries.

| Method | Advantage | Limitation |
| --- | --- | --- |
| Mean of program medians | Simple and uses every available program value | Gives small and large programs equal weight; sensitive to extreme program medians |
| Median of program medians | Less affected by extreme program medians; describes a typical program | Ignores program size and is not the median salary of individual graduates |
| Earnings-count-weighted mean of program medians | Gives larger reported earnings cohorts more influence | Requires matching cohort counts and does not recover the exact pooled student median or mean |

### Proposed recommendation

For describing a typical program, use **median of program median earnings** and show the other methods for comparison. If the goal is to give larger cohorts more influence, show the earnings-count-weighted summary under its explicit name. Do not call any of these the exact median earnings of all graduates in a bucket.

Yahir's supplied chart compares bachelor's programs at four years after graduation across UC and CSU schools. It shows that some buckets change more than others depending on the method. Before report integration, document the input version, how bachelor’s records were selected, which duplicates were removed, and the matching four-year earnings counts. The current student pipeline removes credential identifiers during final cleanup, so filtering must use a stage with those identifiers retained.

The initial Python tests also include a constructed example showing that identical program medians and counts can correspond to different combined student medians. This explains why the true pooled median cannot be reconstructed from those summaries alone.

Report, code, initial results, and sources: repository branch `student-median-methods`, folder `Students/Median-Methods` (available after the branch is pushed).

Sources: [Statistics Canada median definition](https://www150.statcan.gc.ca/n1/pub/81-004-x/def/4068724-eng.htm); [McGrath et al., 2019](https://pubmed.ncbi.nlm.nih.gov/30460713/) (abstract reviewed).

I used ChatGPT to help with the comparison code. Yahir made the comparison chart.
