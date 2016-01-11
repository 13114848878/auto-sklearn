import unittest

from autosklearn.pipeline.components.classification.decision_tree import DecisionTree
from autosklearn.pipeline.util import _test_classifier, _test_classifier_predict_proba

import sklearn.metrics


class DecisionTreetComponentTest(unittest.TestCase):
    def test_default_configuration(self):
        for i in range(10):
            predictions, targets = _test_classifier(DecisionTree)
            self.assertAlmostEqual(0.92,
                                   sklearn.metrics.accuracy_score(predictions,
                                                                  targets))

    def test_default_configuration_sparse(self):
        for i in range(10):
            predictions, targets = _test_classifier(DecisionTree, sparse=True)
            self.assertAlmostEqual(0.69999999999999996,
                                   sklearn.metrics.accuracy_score(predictions,
                                                              targets))

    def test_default_configuration_predict_proba(self):
        for i in range(10):
            predictions, targets = _test_classifier_predict_proba(
                DecisionTree)
            self.assertAlmostEqual(0.28069887755912964,
                sklearn.metrics.log_loss(targets, predictions))

    def test_default_configuration_binary(self):
        for i in range(10):
            predictions, targets = _test_classifier(
                DecisionTree, make_binary=True)
            self.assertAlmostEqual(1.0,
                                   sklearn.metrics.accuracy_score(
                                       targets, predictions))

    def test_default_configuration_multilabel(self):
        for i in range(10):
            predictions, targets = _test_classifier(
                DecisionTree, make_multilabel=True)
            self.assertAlmostEqual(0.94120857699805072,
                                   sklearn.metrics.average_precision_score(
                                       targets, predictions))