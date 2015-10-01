import unittest

import numpy as np
import sklearn.datasets

from ParamSklearn.components.preprocessing.rescaling import Rescaling
from ParamSklearn.util import _test_preprocessing, PreprocessingTestCase


class ScalingComponentTest(PreprocessingTestCase):
    def test_boston_is_not_scaled(self):
        data = sklearn.datasets.load_boston()['data']
        self.assertGreaterEqual(np.max(data), 100)

    def test_default_configuration(self):
        transformations = []
        for i in range(10):
            transformation, original = _test_preprocessing(Rescaling,
                                                           dataset='boston')
            # The maximum is around 1.95 for the transformed array...
            self.assertLessEqual(np.max(transformation), 2)
            self.assertFalse((original == transformation).all())
            transformations.append(transformation)
            if len(transformations) > 1:
                self.assertTrue(
                    (transformations[-1] == transformations[-2]).all())

    def test_default_configuration_with_sparse_data(self):
        preprocessing = _test_preprocessing(Rescaling, dataset='boston',
                                            make_sparse=True)
        transformation, original = preprocessing
        self.assertEqual(original.getnnz(), transformation.getnnz())
        self.assertAlmostEqual(1, transformation.max(), places=6)
        self.assertTrue(~np.allclose(original.data, transformation.data))

    def test_preprocessing_dtype(self):
        super(ScalingComponentTest, self)._test_preprocessing_dtype(Rescaling)
