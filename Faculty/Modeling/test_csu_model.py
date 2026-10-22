"""Focused checks for mixture math, weighting, and model identifiability."""
import unittest
from unittest.mock import patch
import numpy as np
import arviz as az
import pymc as pm
from scipy.special import ndtr
from csu_model import (mixture_statistics, load_data, build_model,
                       aggregate_estimates, BUCKETS)


class ModelChecks(unittest.TestCase):
    def test_invalid_pay_is_rejected(self):
        data, _, _ = load_data()
        for value in [0, -10, np.nan, np.inf]:
            bad = data.head(2).copy()
            bad.iloc[0, bad.columns.get_loc('totalpay')] = value
            with patch('csu_model.pd.read_parquet', return_value=bad):
                with self.assertRaisesRegex(ValueError, 'finite positive pay'):
                    load_data('unused.parquet')

    def test_single_lognormal(self):
        mu, s = np.array([[[2.0]]]), np.array([[.4]])
        mean, median, variance = mixture_statistics(mu, s, [1.])
        np.testing.assert_allclose(mean, np.exp(2+.4**2/2))
        np.testing.assert_allclose(median, np.exp(2))
        np.testing.assert_allclose(variance, np.expm1(.4**2)*np.exp(4+.4**2))

    def test_mixture_median_and_variance(self):
        mu, s, w = np.array([[[0., 3.]]]), np.array([[.5]]), np.array([.25, .75])
        mean, median, variance = mixture_statistics(mu, s, w)
        np.testing.assert_allclose(np.sum(w*ndtr((np.log(median)[..., None]-mu)/s[..., None]), axis=-1), .5)
        second = np.sum(w*np.exp(2*mu+2*s[..., None]**2), axis=-1)
        np.testing.assert_allclose(variance, second-mean**2)
        self.assertGreater(abs(float(median.item())-np.sum(w*np.exp(mu))), .1)
        with self.assertRaises(ValueError):
            mixture_statistics(mu, s, [.1, .2])

    def test_data_constraints_and_aggregation(self):
        data, coords, audit = load_data()
        self.assertEqual(set(coords['bucket']), set(BUCKETS))
        self.assertTrue(data.totalpay.gt(0).all())
        model = build_model(data, coords)
        self.assertTrue(np.isfinite(model.compile_logp()(model.initial_point())))
        with model:
            prior = pm.sample_prior_predictive(draws=4, random_seed=13,
                var_names=['intercept', 'sigma', 'job_effect', 'university_effect', 'bucket_effect', 'interaction'])
        p = prior.prior
        for name in ['job_effect', 'university_effect', 'bucket_effect']:
            np.testing.assert_allclose(p[name].values.sum(axis=-1), 0, atol=1e-12)
        np.testing.assert_allclose(p.interaction.values.sum(axis=-1), 0, atol=1e-12)
        np.testing.assert_allclose(p.interaction.values.sum(axis=-2), 0, atol=1e-12)
        estimates, samples = aggregate_estimates(az.InferenceData(posterior=p), data, coords)
        self.assertEqual(len(estimates), len(coords['university'])*10+10)
        self.assertEqual(int(estimates.extrapolated.sum()), audit['empty_cells'])
        self.assertTrue(np.isfinite(samples.aggregate_statistic.values).all())
        # Independently reconstruct statewide joint campus/job weights.
        b = 0
        mu, counts = [], []
        for u, school in enumerate(coords['university']):
            for j, job in enumerate(coords['job']):
                mu.append(p.intercept.values + p.university_effect.values[..., u]
                          + p.bucket_effect.values[..., b] + p.interaction.values[..., u, b]
                          + p.job_effect.values[..., j])
                counts.append(int(((data.school == school) & (data.job == job)
                                   & (data.department == BUCKETS[b])).sum()))
        weights = np.array(counts)/sum(counts)
        expected = mixture_statistics(np.stack(mu, axis=-1), p.sigma.values, weights)
        actual = samples.aggregate_statistic.sel(group=f'CSU-wide | {BUCKETS[b]}').values
        np.testing.assert_allclose(actual, np.stack(expected, axis=-1))
        # Identical component locations/scales must produce identical group statistics.
        for name in ['job_effect', 'university_effect', 'bucket_effect', 'interaction']:
            p[name].values[...] = 0
        estimates, _ = aggregate_estimates(az.InferenceData(posterior=p), data, coords)
        for name in ['mean', 'median', 'variance']:
            np.testing.assert_allclose(estimates[f'{name}_estimate'], estimates[f'{name}_estimate'].iloc[0])


if __name__ == '__main__':
    unittest.main()
