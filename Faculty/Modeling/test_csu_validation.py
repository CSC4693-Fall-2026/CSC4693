"""Focused checks for validation alignment, grouping, and predictive intervals."""
import unittest

import numpy as np
import pandas as pd
import xarray as xr
from scipy.special import ndtri
from scipy.stats import lognorm

from csu_validation import (predictive_parameters, predictive_checks, split_records,
                            bucket_contrasts, heldout_metrics)


def posterior():
    return xr.Dataset({
        'intercept':(('chain', 'draw'), np.full((2, 3), np.log(100.))),
        'sigma':(('chain', 'draw'), np.full((2, 3), .2)),
        'job_effect':(('chain', 'draw', 'job'), np.zeros((2, 3, 2))),
        'university_effect':(('chain', 'draw', 'university'), np.zeros((2, 3, 2))),
        'bucket_effect':(('chain', 'draw', 'bucket'), np.zeros((2, 3, 2))),
        'interaction':(('chain', 'draw', 'university', 'bucket'), np.zeros((2, 3, 2, 2))),
    }, coords={'chain':[0, 1], 'draw':[0, 1, 2], 'job':['J1', 'J2'],
               'university':['U1', 'U2'], 'bucket':['B1', 'B2']})


class ValidationChecks(unittest.TestCase):
    def test_predictor_category_alignment(self):
        p = posterior()
        p.job_effect.values[..., 1] = .1
        p.university_effect.values[..., 1] = .2
        p.bucket_effect.values[..., 1] = .3
        p.interaction.values[..., 1, 1] = .05
        data = pd.DataFrame(dict(school=['U2', 'U1'], department=['B2', 'B1'], job=['J2', 'J1']))
        mu, sigma = predictive_parameters(p, data, n_draws=6)
        np.testing.assert_allclose(mu, np.tile([np.log(100)+.65, np.log(100)], (6, 1)))
        np.testing.assert_allclose(sigma, .2)
        with self.assertRaises(ValueError):
            predictive_parameters(p, data.assign(job='unknown'))

    def test_predictive_intervals_and_density(self):
        data = pd.DataFrame(dict(school=['U1', 'U2'], department=['B1', 'B2'],
                                 job=['J1', 'J2'], totalpay=[80., 120.]))
        summary, records = heldout_metrics(posterior(), data, n_draws=6)
        np.testing.assert_allclose(records.predictive_median, 100.)
        np.testing.assert_allclose(records.predictive_lower_95, 100*np.exp(.2*ndtri(.025)))
        np.testing.assert_allclose(records.predictive_upper_95, 100*np.exp(.2*ndtri(.975)))
        np.testing.assert_allclose(records.log_predictive_density, lognorm.logpdf(data.totalpay, s=.2, scale=100))
        self.assertEqual(summary.iloc[0].mae_predictive_median_dollars, 20.)

    def test_name_group_split(self):
        data = pd.DataFrame(dict(name=['Alice', ' alice ', 'Bob', 'Cara', 'Dan', 'Eve', 'Fay', 'Gus', 'Hal', 'Ivy'],
                                 school=['U1']*5+['U2']*5,
                                 department=['B1', 'B2']*5,
                                 job=['rare']+['common']*9))
        train, test, assignment, _ = split_records(data, test_fraction=.4)
        self.assertEqual(set(train.job), set(data.job))
        self.assertEqual(set(train.school), set(data.school))
        self.assertEqual(set(train.department), set(data.department))
        self.assertFalse(set(train.name.str.strip().str.casefold()) & set(test.name.str.strip().str.casefold()))
        self.assertEqual(assignment.loc[0, 'split'], assignment.loc[1, 'split'])
        self.assertEqual(len(train)+len(test), len(data))
        pd.testing.assert_frame_equal(assignment, split_records(data, test_fraction=.4)[2])

    def test_replicate_statistics(self):
        data = pd.DataFrame(dict(school=['U1', 'U1'], department=['B1', 'B1'], totalpay=[10., 30.]))
        table = predictive_checks(data, np.tile(data.totalpay.to_numpy(), (5, 1)))
        self.assertFalse(table.observed_outside_95.any())
        np.testing.assert_allclose(table.observed, table.replicated_mean)
        self.assertEqual(table.loc[table.statistic.eq('variance'), 'observed'].iloc[0], 100.)

    def test_paired_contrast(self):
        samples = xr.Dataset({'aggregate_statistic':(
            ('chain', 'draw', 'group', 'statistic'),
            np.array([[[[10., 9., 5.], [3., 4., 2.]],
                       [[20., 19., 8.], [13., 14., 5.]]]]))},
            coords={'group':['CSU-wide | A', 'CSU-wide | B'], 'statistic':['mean', 'median', 'variance']})
        contrasts = bucket_contrasts(samples, 'A', 'B')
        np.testing.assert_allclose(contrasts.posterior_mean_difference, [7, 5, 3])
        np.testing.assert_allclose(contrasts.lower_95, contrasts.upper_95)
        self.assertTrue(contrasts.probability_a_greater_b.eq(1).all())


if __name__ == '__main__':
    unittest.main()
