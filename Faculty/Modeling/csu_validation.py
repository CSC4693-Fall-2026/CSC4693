"""Focused validation helpers for csu-model-validation.ipynb.

The held-out fit uses the original model and priors, with no test outcomes used
for training. Names are a conservative grouping proxy, not verified person IDs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
from scipy.special import logsumexp, ndtr

from csu_model import DEFAULT_DATA, HERE, PARAMETERS, build_model, fit_model, load_data

OUTPUT = HERE / 'results-validation'
SAMPLING = dict(draws=2000, tune=2000, chains=4, cores=2, seed=4694, target_accept=.95)


def observed_comparisons(data, estimates):
    """Observed descriptive statistics versus fitted distribution statistics."""
    rows = []
    for _, row in estimates.iterrows():
        mask = data.department.eq(row.bucket)
        if row.university != 'CSU-wide':
            mask &= data.school.eq(row.university)
        y = data.loc[mask, 'totalpay'].to_numpy()
        stats = [y.mean(), np.median(y), y.var(ddof=0)] if len(y) else [np.nan]*3
        for stat, observed in zip(['mean', 'median', 'variance'], stats):
            estimate = row[f'{stat}_estimate']
            rows.append(dict(university=row.university, bucket=row.bucket, n_records=len(y),
                             statistic=stat, observed=observed, estimate=estimate,
                             lower_95=row[f'{stat}_lower_95'], upper_95=row[f'{stat}_upper_95'],
                             difference=estimate-observed,
                             relative_difference=(estimate-observed)/observed if observed > 0 else np.nan,
                             extrapolated=row.extrapolated))
    return pd.DataFrame(rows)


def predictive_parameters(posterior, data, n_draws=500, seed=4693):
    """Evaluate the existing linear predictor at records, selecting joint draws."""
    p = posterior.stack(sample=('chain', 'draw'))
    rng = np.random.default_rng(seed)
    selection = rng.choice(p.sizes['sample'], size=min(n_draws, p.sizes['sample']), replace=False)

    def values(name, *dims):
        return p[name].transpose('sample', *dims).values[selection]

    indexes = []
    for col, dim in [('school', 'university'), ('department', 'bucket'), ('job', 'job')]:
        idx = pd.Categorical(data[col], categories=posterior.coords[dim].values).codes
        if (idx < 0).any():
            raise ValueError(f'Unknown prediction category in {col}')
        indexes.append(idx)
    u, b, j = indexes
    mu = (values('intercept')[:, None] + values('job_effect', 'job')[:, j]
          + values('university_effect', 'university')[:, u]
          + values('bucket_effect', 'bucket')[:, b]
          + values('interaction', 'university', 'bucket')[:, u, b])
    return mu, values('sigma')[:, None]


def predictive_draws(posterior, data, n_draws=500, seed=4693):
    mu, sigma = predictive_parameters(posterior, data, n_draws, seed)
    return np.random.default_rng(seed+1).lognormal(mu, sigma)


def predictive_checks(data, replicated, low_pay_threshold=20000):
    """Finite-sample predictive intervals; no claims of classical significance."""
    if replicated.ndim != 2 or replicated.shape[1] != len(data):
        raise ValueError('Predictive draws must have shape (draw, record).')

    def stats(x):
        return dict(mean=x.mean(axis=-1), median=np.median(x, axis=-1),
                    variance=x.var(axis=-1, ddof=0), q05=np.quantile(x, .05, axis=-1),
                    q95=np.quantile(x, .95, axis=-1), q99=np.quantile(x, .99, axis=-1),
                    low_pay_fraction=(x < low_pay_threshold).mean(axis=-1))

    rows = []
    groups = [('CSU-wide', bucket, data.department.eq(bucket).to_numpy())
              for bucket in sorted(data.department.unique())]
    groups += [(school, bucket, (data.school.eq(school) & data.department.eq(bucket)).to_numpy())
               for school, bucket in data.groupby(['school', 'department']).groups]
    for school, bucket, mask in groups:
        actual = stats(data.loc[mask, 'totalpay'].to_numpy())
        simulated = stats(replicated[:, mask])
        for stat in actual:
            lo, hi = np.quantile(simulated[stat], [.025, .975])
            rows.append(dict(university=school, bucket=bucket, n_records=int(mask.sum()),
                             statistic=stat, observed=float(actual[stat]),
                             replicated_mean=float(simulated[stat].mean()),
                             replicated_lower_95=float(lo), replicated_upper_95=float(hi),
                             observed_outside_95=bool(actual[stat] < lo or actual[stat] > hi)))
    return pd.DataFrame(rows)


def bucket_contrasts(aggregate_draws, bucket_a='Engineering',
                     bucket_b='Humanities & Languages', university='CSU-wide'):
    """Paired posterior differences retain correlation between group estimates."""
    a = aggregate_draws.aggregate_statistic.sel(group=f'{university} | {bucket_a}')
    b = aggregate_draws.aggregate_statistic.sel(group=f'{university} | {bucket_b}')
    rows = []
    for stat in ['mean', 'median', 'variance']:
        difference = (a-b).sel(statistic=stat).values.ravel()
        lo, hi = np.quantile(difference, [.025, .975])
        rows.append(dict(university=university, bucket_a=bucket_a, bucket_b=bucket_b,
                         statistic=stat, posterior_mean_difference=float(difference.mean()),
                         lower_95=float(lo), upper_95=float(hi),
                         probability_a_greater_b=float((difference > 0).mean())))
    return pd.DataFrame(rows)


def split_records(data, test_fraction=.2, seed=4694):
    """Split normalized names globally; keep every predictor level in training."""
    if not 0 < test_fraction < 1:
        raise ValueError('test_fraction must be between zero and one.')
    if data.name.isna().any():
        raise ValueError('Holdout grouping requires nonmissing names.')
    keys = data.name.astype(str).str.strip().str.casefold()
    if keys.eq('').any():
        raise ValueError('Holdout grouping requires nonempty names.')
    unique = np.sort(keys.unique())
    if len(unique) < 2:
        raise ValueError('At least two name groups are required.')
    rng = np.random.default_rng(seed)
    n_test = min(len(unique)-1, max(1, round(test_fraction*len(unique))))
    test_keys = set(rng.choice(unique, size=n_test, replace=False))
    pinned = []
    for col in ['school', 'department', 'job']:
        for level in sorted(data[col].unique()):
            level_keys = set(keys[data[col].eq(level)])
            if level_keys.issubset(test_keys):
                key = sorted(level_keys)[0]
                test_keys.remove(key)
                pinned.append(dict(column=col, level=level))
    test_mask = keys.isin(test_keys)
    train, test = data.loc[~test_mask].copy(), data.loc[test_mask].copy()
    if train.empty or test.empty:
        raise ValueError('The constrained split left an empty training or test set.')
    assert not set(keys.loc[train.index]) & set(keys.loc[test.index])
    assignment = pd.DataFrame({'source_index':data.index,
                               'name_group_sha256':[hashlib.sha256(k.encode()).hexdigest() for k in keys],
                               'split':np.where(test_mask, 'test', 'train')})
    info = dict(seed=seed, requested_test_fraction=test_fraction,
                actual_test_fraction=len(test)/len(data), train_records=len(train), test_records=len(test),
                train_name_groups=int(keys.loc[train.index].nunique()),
                test_name_groups=int(keys.loc[test.index].nunique()),
                categories_pinned_to_training=pinned,
                grouping='Globally normalized name; proxy identity. No normalized name overlaps splits.')
    return train, test, assignment, info


def parameter_diagnostics(idata):
    summary = az.summary(idata, var_names=PARAMETERS, kind='diagnostics', round_to='none')
    finite = np.isfinite(summary[['r_hat', 'ess_bulk', 'ess_tail']]).all().all()
    result = dict(divergences=int(idata.sample_stats.diverging.sum()),
                  max_rhat=float(summary.r_hat.max()),
                  min_bulk_ess=float(summary.ess_bulk.min()), min_tail_ess=float(summary.ess_tail.min()))
    result['passed'] = bool(finite and result['divergences'] == 0 and result['max_rhat'] <= 1.01
                            and min(result['min_bulk_ess'], result['min_tail_ess']) >= 400)
    return summary, result


def heldout_fit(data_path=DEFAULT_DATA, output=OUTPUT, **sampling):
    """Separate training-only fit; existing full-data posterior is never replaced."""
    sampling = SAMPLING | sampling
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data, coords, _ = load_data(data_path)
    train, test, assignment, split_info = split_records(data)
    assignment.to_csv(output/'holdout_split.csv', index=False)
    idata = fit_model(build_model(train, coords), **sampling)
    idata.to_netcdf(output/'holdout_posterior.nc', engine='h5netcdf')
    summary, convergence = parameter_diagnostics(idata)
    summary.to_csv(output/'holdout_parameter_diagnostics.csv')
    metadata = dict(sampling=sampling, split=split_info, convergence=convergence,
                    input_sha256=hashlib.sha256(Path(data_path).read_bytes()).hexdigest())
    (output/'holdout_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata, indent=2), flush=True)
    return idata, train, test, metadata


def heldout_metrics(posterior, test, n_draws=2000, seed=4695):
    """Per-record posterior predictive coverage and proper log score in dollars."""
    mu, sigma = predictive_parameters(posterior, test, n_draws, seed)
    y = test.totalpay.to_numpy()
    log_y = np.log(y)
    log_density = (-log_y[None, :] - np.log(sigma) - .5*np.log(2*np.pi)
                   - .5*((log_y[None, :]-mu)/sigma)**2)
    log_score = logsumexp(log_density, axis=0)-np.log(len(mu))

    def quantile(prob):
        # Invert the posterior predictive mixture CDF, including parameter uncertainty.
        lo, hi = (mu-12*sigma).min(axis=0), (mu+12*sigma).max(axis=0)
        for _ in range(48):
            mid = (lo+hi)/2
            cdf = ndtr((mid[None, :]-mu)/sigma).mean(axis=0)
            lo, hi = np.where(cdf < prob, mid, lo), np.where(cdf < prob, hi, mid)
        return np.exp((lo+hi)/2)

    median, lo50, hi50, lo95, hi95 = [quantile(q) for q in [.5, .25, .75, .025, .975]]
    records = pd.DataFrame(dict(source_index=test.index, university=test.school.to_numpy(),
                                bucket=test.department.to_numpy(), observed=y,
                                predictive_median=median, predictive_lower_50=lo50,
                                predictive_upper_50=hi50, predictive_lower_95=lo95,
                                predictive_upper_95=hi95, log_predictive_density=log_score))
    def summarize(frame):
        return dict(n_records=len(frame),
                    mae_predictive_median_dollars=float(np.abs(frame.observed-frame.predictive_median).mean()),
                    mean_log_predictive_density=float(frame.log_predictive_density.mean()),
                    coverage_50=float(frame.observed.between(frame.predictive_lower_50, frame.predictive_upper_50).mean()),
                    coverage_95=float(frame.observed.between(frame.predictive_lower_95, frame.predictive_upper_95).mean()),
                    mean_95_interval_width=float((frame.predictive_upper_95-frame.predictive_lower_95).mean()))
    rows = [dict(group='Overall', **summarize(records))]
    rows += [dict(group=b, **summarize(g)) for b, g in records.groupby('bucket')]
    return pd.DataFrame(rows), records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fit the validation training split only.')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    heldout_fit(output=args.output)
