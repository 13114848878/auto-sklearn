import unittest

from AutoSklearn.components.classification.gradient_boosting import \
    GradientBoostingClassifier
from AutoSklearn.util import _test_classifier_with_iris

import sklearn.metrics


class GradientBoostingComponentTest(unittest.TestCase):
    def test_default_configuration(self):
        for i in range(10):
            predictions, targets = \
                _test_classifier_with_iris(GradientBoostingClassifier)
            self.assertAlmostEqual(0.92,
                sklearn.metrics.accuracy_score(predictions, targets))