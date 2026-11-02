"""2024 CSU lognormal model; estimates describe sampled annual-pay records.

Run: python Faculty/Modeling/csu_model.py
Install: python -m pip install -r Faculty/Modeling/requirements-modeling.txt
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm
import pytensor
import xarray as xr
from scipy.special import ndtr

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parent / 'content/model_csu_depbucket_cleaned_joined_pay_2013-2024.parquet'
BUCKETS = sorted([
    'Agriculture, Food & Animal', 'Architecture & Environmental Design',
    'Business, Economics & Finance', 'Computer Science',
    'Education & Public Administration', 'Engineering', 'Humanities & Languages',
    'Medicine & Health Sciences', 'Science & Mathematics',
    'Social Sciences & Communication',
])
PARAMETERS = ['intercept', 'job_effect', 'university_effect', 'bucket_effect',
              'interaction', 'tau_university', 'tau_bucket', 'tau_interaction', 'sigma']


def load_data(path=DEFAULT_DATA):
    """Audit before filtering. Invalid targets require an explicit upstream decision."""
    raw = pd.read_parquet(path).rename(columns={'total_pay': 'totalpay'})
    required = ['totalpay', 'school', 'department', 'job', 'year_transparentCA']
    missing = set(required) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    data = raw.loc[raw.year_transparentCA.eq(2024)].copy()
    y = pd.to_numeric(data.totalpay, errors='coerce')
    audit = dict(input_rows=len(raw), year=2024, year_rows=len(data),
                 zero_pay=int(y.eq(0).sum()), negative_pay=int(y.lt(0).sum()),
                 missing_or_nonnumeric_pay=int(y.isna().sum()),
                 infinite_pay=int(np.isinf(y).sum()),
                 excluded_other=int(data.department.eq('Other').sum()))
    print(json.dumps(audit, indent=2), flush=True)
    if not len(data) or not np.isfinite(y).all() or y.le(0).any():
        raise ValueError('Lognormal fitting requires finite positive pay. Audit above; no invalid records were silently removed.')
    for col in ['school', 'department', 'job']:
        if data[col].isna().any() or data[col].astype(str).str.strip().eq('').any():
            raise ValueError(f'Missing/empty predictor: {col}')
    unknown = set(data.department) - set(BUCKETS) - {'Other'}
    if unknown:
        raise ValueError(f'Unexpected buckets: {sorted(unknown)}')
    data = data.loc[data.department.ne('Other')].copy()
    data['totalpay'] = y.loc[data.index].astype(float)
    if set(data.department) != set(BUCKETS):
        raise ValueError('All ten buckets must have observations.')
    coords = dict(university=sorted(data.school.unique()), bucket=BUCKETS,
                  job=sorted(data.job.unique()))
    for col, dim in [('school', 'university'), ('department', 'bucket'), ('job', 'job')]:
        data[f'{dim}_idx'] = pd.Categorical(data[col], categories=coords[dim]).codes
    audit.update(fitting_rows=len(data), universities=len(coords['university']),
                 buckets=len(BUCKETS), jobs=len(coords['job']),
                 repeated_name_campus_year_keys=int(data.duplicated(['name', 'school', 'year_transparentCA']).sum()),
                 empty_cells=len(coords['university'])*len(BUCKETS)-data.groupby(['school', 'department']).ngroups)
    print(json.dumps(audit, indent=2), flush=True)
    return data, coords, audit


def build_model(data, coords):
    with pm.Model(coords=coords) as model:
        intercept = pm.Normal('intercept', mu=np.log(80000), sigma=1.5)
        job = pm.ZeroSumNormal('job_effect', sigma=1, dims='job')
        effects = {}
        for label, dims in [('university', ('university',)), ('bucket', ('bucket',)),
                            ('interaction', ('university', 'bucket'))]:
            tau = pm.HalfNormal(f'tau_{label}', sigma=0.5)
            z = pm.ZeroSumNormal(f'z_{label}', sigma=1, dims=dims,
                                 n_zerosum_axes=len(dims))
            name = 'interaction' if label == 'interaction' else f'{label}_effect'
            effects[label] = pm.Deterministic(name, tau*z, dims=dims)
        sigma = pm.HalfNormal('sigma', sigma=1)
        u, b, j = (data[f'{dim}_idx'].to_numpy() for dim in ('university', 'bucket', 'job'))
        mu = intercept + job[j] + effects['university'][u] + effects['bucket'][b] + effects['interaction'][u, b]
        pm.LogNormal('pay', mu=mu, sigma=sigma, observed=data.totalpay.to_numpy())
    return model


def fit_model(model, draws=2000, tune=2000, chains=4, cores=2, seed=4693, target_accept=0.95):
    # Numba compiles the same PyMC NUTS log density on machines without g++.
    compile_kwargs = {'mode': 'NUMBA'} if not pytensor.config.cxx else {}
    with model:
        return pm.sample(draws=draws, tune=tune, chains=chains, cores=cores,
                         random_seed=seed, target_accept=target_accept,
                         nuts_sampler='pymc', compile_kwargs=compile_kwargs,
                         idata_kwargs={'log_likelihood': False})


def mixture_statistics(mu, sigma, weights):
    """Last axis is components; leading axes retain posterior chain/draw shape."""
    mu, sigma, weights = np.asarray(mu), np.asarray(sigma), np.asarray(weights)
    if np.any(weights < 0) or not np.isclose(weights.sum(), 1):
        raise ValueError('Mixture weights must be nonnegative and sum to one.')
    keep = weights > 0
    mu, weights = mu[..., keep], weights[keep]
    s2 = np.square(sigma)[..., None]
    component_means = np.exp(mu + s2/2)
    mean = np.sum(weights*component_means, axis=-1)
    # Law of total variance, numerically more stable than E[T^2] - E[T]^2.
    variance = np.sum(weights*(np.expm1(s2)*component_means**2
                              + (component_means-mean[..., None])**2), axis=-1)
    # Mixture log median lies between minimum and maximum component log medians.
    lo, hi = mu.min(axis=-1), mu.max(axis=-1)
    for _ in range(48):
        mid = (lo+hi)/2
        cdf = np.sum(weights*ndtr((mid[..., None]-mu)/sigma[..., None]), axis=-1)
        lo, hi = np.where(cdf < 0.5, mid, lo), np.where(cdf < 0.5, hi, mid)
    return mean, np.exp((lo+hi)/2), variance


def aggregate_estimates(idata, data, coords):
    p = idata.posterior
    intercept = p.intercept.values
    job = p.job_effect.transpose('chain', 'draw', 'job').values
    university = p.university_effect.transpose('chain', 'draw', 'university').values
    bucket = p.bucket_effect.transpose('chain', 'draw', 'bucket').values
    interaction = p.interaction.transpose('chain', 'draw', 'university', 'bucket').values
    sigma = p.sigma.values
    counts = np.zeros((len(coords['university']), len(BUCKETS), len(coords['job'])), dtype=int)
    np.add.at(counts, (data.university_idx, data.bucket_idx, data.job_idx), 1)
    rows, draws = [], []

    def add(mu, w, school, b, n, source, extrapolated):
        stats = np.stack(mixture_statistics(mu, sigma, w), axis=-1)
        if not np.isfinite(stats).all():
            raise ValueError('Nonfinite aggregate statistics; inspect posterior draws.')
        draws.append(stats)
        row = dict(university=school, bucket=BUCKETS[b], year=2024, n_records=int(n),
                   weight_source=source, extrapolated=extrapolated,
                   estimand='sample_composition_annual_pay', population_representative=False)
        for i, name in enumerate(['mean', 'median', 'variance']):
            values = stats[..., i]
            row.update({f'{name}_estimate':float(values.mean()),
                        f'{name}_lower_95':float(np.quantile(values, .025)),
                        f'{name}_upper_95':float(np.quantile(values, .975))})
        rows.append(row)

    for u, school in enumerate(coords['university']):
        for b in range(len(BUCKETS)):
            n = counts[u, b].sum()
            weights = counts[u, b] if n else counts[:, b].sum(axis=0)
            mu = (intercept+university[..., u]+bucket[..., b]+interaction[..., u, b])[..., None]+job
            add(mu, weights/weights.sum(), school, b, n,
                'observed_cell_jobs' if n else 'observed_bucket_jobs_fallback', not bool(n))
    for b in range(len(BUCKETS)):
        mu = (intercept[..., None]+university+bucket[..., b, None]+interaction[..., b])[..., None]+job[..., None, :]
        weights = counts[:, b].ravel()
        add(mu.reshape(*mu.shape[:2], -1), weights/weights.sum(), 'CSU-wide', b,
            weights.sum(), 'observed_joint_university_job', False)
    samples = xr.Dataset({'aggregate_statistic':(
        ('chain', 'draw', 'group', 'statistic'), np.stack(draws, axis=2))},
        coords={'chain':p.chain.values, 'draw':p.draw.values,
                'group':[f'{r["university"]} | {r["bucket"]}' for r in rows],
                'statistic':['mean', 'median', 'variance']})
    return pd.DataFrame(rows), samples


def diagnostics(idata, aggregate_draws):
    parameter_summary = az.summary(idata, var_names=PARAMETERS, kind='diagnostics', round_to='none')
    aggregate_summary = az.summary(az.InferenceData(posterior=aggregate_draws),
                                   kind='diagnostics', round_to='none')
    combined = pd.concat([parameter_summary, aggregate_summary])
    rhat = combined.r_hat.to_numpy()
    ess = combined[['ess_bulk', 'ess_tail']].to_numpy()
    result = dict(divergences=int(idata.sample_stats.diverging.sum()),
                  max_rhat=float(np.nanmax(rhat)), min_bulk_ess=float(combined.ess_bulk.min()),
                  min_tail_ess=float(combined.ess_tail.min()))
    result['passed'] = bool(np.isfinite(rhat).all() and np.isfinite(ess).all()
                            and result['divergences'] == 0 and (rhat <= 1.01).all()
                            and (ess >= 400).all())
    return parameter_summary, aggregate_summary, result


def run(data_path=DEFAULT_DATA, output=HERE/'results', **sampling):
    sampling = dict(draws=2000, tune=2000, chains=4, cores=2, seed=4693,
                    target_accept=.95) | sampling
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data, coords, audit = load_data(data_path)
    # Save the audit before expensive fitting, even if sampling fails later.
    (output/'data_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    model = build_model(data, coords)
    idata = fit_model(model, **sampling)
    idata.to_netcdf(output/'posterior.nc', engine='h5netcdf')
    estimates, aggregate_draws = aggregate_estimates(idata, data, coords)
    aggregate_draws.to_netcdf(output/'aggregate_draws.nc', engine='h5netcdf')
    params, aggregates, convergence = diagnostics(idata, aggregate_draws)
    estimates['convergence_passed'] = convergence['passed']
    estimates.loc[estimates.university.ne('CSU-wide')].to_csv(output/'university_bucket_estimates.csv', index=False)
    estimates.loc[estimates.university.eq('CSU-wide')].to_csv(output/'csu_bucket_estimates.csv', index=False)
    params.to_csv(output/'parameter_diagnostics.csv')
    aggregates.to_csv(output/'aggregate_diagnostics.csv')
    metadata = dict(data_audit=audit, sampling=sampling, convergence=convergence,
                    compiler='NUMBA' if not pytensor.config.cxx else 'default',
                    input_path=str(Path(data_path).resolve()),
                    input_sha256=hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
                    versions={pkg:importlib.metadata.version(pkg) for pkg in
                              ['pymc', 'arviz', 'numpy', 'pandas', 'scipy', 'pytensor', 'h5netcdf', 'pyarrow', 'xarray']},
                    interpretation='2024 nominal annual pay per sampled record, excluding benefits; fixed empirical weights, not population weights. Variance is distribution variance in dollars squared; intervals are posterior equal-tail credible intervals, not prediction intervals. Empty cells use bucket-wide jobs. Records retained without deduplication.')
    (output/'run_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(convergence, indent=2), flush=True)
    print(f'Results: {output.resolve()}', flush=True)
    return idata, estimates, metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--output', type=Path, default=HERE/'results')
    parser.add_argument('--draws', type=int, default=2000)
    parser.add_argument('--tune', type=int, default=2000)
    parser.add_argument('--chains', type=int, default=4)
    parser.add_argument('--cores', type=int, default=2)
    parser.add_argument('--seed', type=int, default=4693)
    parser.add_argument('--target-accept', type=float, default=.95)
    args = vars(parser.parse_args())
    args['data_path'] = args.pop('data')
    run(**args)
