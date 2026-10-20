"""Compare summaries of program medians; none is an exact pooled student median.

Run: python compare_methods.py student_input_snapshot.csv --output results.csv
Uses only Python's standard library for CSV input. Parquet input requires pandas
and pyarrow: pip install pandas pyarrow. Outputs stay stratified by school,
credential level, bucket, and years since graduation. Source files are unchanged.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        bucket = (row.get('department') or '').strip()
        if not bucket:
            continue
        bucket = bucket.replace('Medicine & Heath Sciences', 'Medicine & Health Sciences')
        for horizon in ('1yr', '4yr', '5yr'):
            key = (row['unitid'], row['institution'], row['credlev'], bucket, horizon)
            groups[key].append(row)
    results = []
    for key, members in sorted(groups.items()):
        horizon = key[-1]
        available = [(number(r.get('earn_mdn_' + horizon)), number(r.get('earn_count_' + horizon))) for r in members]
        values = [v for v, n in available if v is not None]
        paired = [(v, n) for v, n in available if v is not None and n is not None and n > 0]
        if not values:
            continue
        weighted = sum(v*n for v, n in paired)/sum(n for v, n in paired) if paired else None
        paired_mean = mean(v for v, n in paired) if paired else None
        results.append(dict(zip(('unitid','institution','credlev','department','horizon'), key),
            total_program_rows=len(members), usable_median_rows=len(values),
            rows_with_positive_earnings_count=len(paired),
            sum_reported_earnings_counts=sum(n for v,n in paired),
            mean_of_program_medians=mean(values),
            median_of_program_medians=median(values),
            mean_of_program_medians_same_weighted_rows=paired_mean,
            earnings_count_weighted_mean_of_program_medians=weighted,
            weighting_difference_same_rows=weighted-paired_mean if paired else None))
    return results


def counterexample():
    worlds = [([30000,30000,130000], [40000]*5),
              ([30000,30000,31000], [30000,30000,40000,40000,40000])]
    for a,b in worlds:
        assert [median(a), median(b)] == [30000,40000]
        assert [len(a),len(b)] == [3,5]
    assert median(worlds[0][0]+worlds[0][1]) == 40000
    assert median(worlds[1][0]+worlds[1][1]) == 30500
    print('Counterexample passed: identical program medians/counts, pooled medians $40,000 vs $30,500.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, default=Path('results.csv'))
    args=parser.parse_args()
    counterexample()
    if args.input.suffix == '.parquet':
        import pandas as pd
        rows=pd.read_parquet(args.input).to_dict('records')
        rows=[{k: (None if isinstance(v,float) and math.isnan(v) else v) for k,v in r.items()} for r in rows]
    else:
        with args.input.open(newline='') as f:
            rows=list(csv.DictReader(f))
    results=summarize(rows)
    if not results:
        raise ValueError('No usable grouped records found')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]))
        writer.writeheader(); writer.writerows(results)
    print(f'Wrote {len(results)} school/credential/bucket/horizon comparisons to {args.output}')
    print('Weights are supplied earn_count columns; verify their source cohort definitions before final use.')

if __name__=='__main__':
    main()
