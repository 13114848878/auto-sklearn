'''
Created on Dec 18, 2014

@author: Aaron Klein
'''
import copy
import functools
import unittest
import os
import shutil

import numpy as np

from autosklearn.data.data_converter import convert_to_bin
from autosklearn.models.evaluator import predict_proba
from autosklearn.models.holdout_evaluator import HoldoutEvaluator
from autosklearn.models.paramsklearn import get_configuration_space
from autosklearn.data.split_data import split_data
from ParamSklearn.util import get_dataset
from HPOlibConfigSpace.random_sampler import RandomSampler

N_TEST_RUNS = 10


class Dummy(object):
    pass


class HoldoutEvaluator_Test(unittest.TestCase):
    def test_evaluate_multiclass_classification(self):
        X_train, Y_train, X_test, Y_test = get_dataset('iris')
        X_valid = X_test[:25,]
        Y_valid = Y_test[:25,]
        X_test = X_test[25:,]
        Y_test = Y_test[25:,]

        D = Dummy()
        D.info = {'metric': 'bac_metric', 'task': 'multiclass.classification',
                  'is_sparse': False}
        D.data = {'X_train': X_train, 'Y_train': Y_train,
                  'X_valid': X_valid, 'X_test': X_test}
        D.feat_type = ['numerical', 'Numerical', 'numerical', 'numerical']

        configuration_space = get_configuration_space(D.info)
        sampler = RandomSampler(configuration_space, 1)

        err = np.zeros([N_TEST_RUNS])
        for i in range(N_TEST_RUNS):
            print "Evaluate configuration: %d; result:" % i,
            configuration = sampler.sample_configuration()
            D_ = copy.deepcopy(D)
            evaluator = HoldoutEvaluator(D_, configuration)

            if not self._fit(evaluator):
                print
                continue
            err[i] = evaluator.predict()
            print err[i]

            self.assertTrue(np.isfinite(err[i]))
            self.assertGreaterEqual(err[i], 0.0)

        print "Number of times it was worse than random guessing:" + str(np.sum(err > 1))

    def test_evaluate_multiclass_classification_all_metrics(self):
        X_train, Y_train, X_test, Y_test = get_dataset('iris')
        X_valid = X_test[:25, ]
        Y_valid = Y_test[:25, ]
        X_test = X_test[25:, ]
        Y_test = Y_test[25:, ]

        D = Dummy()
        D.info = {'metric': 'bac_metric', 'task': 'multiclass.classification',
                  'is_sparse': False}
        D.data = {'X_train': X_train, 'Y_train': Y_train,
                  'X_valid': X_valid, 'X_test': X_test}
        D.feat_type = ['numerical', 'Numerical', 'numerical', 'numerical']

        configuration_space = get_configuration_space(D.info)
        sampler = RandomSampler(configuration_space, 1)

        # Test all scoring functions
        err = []
        for i in range(N_TEST_RUNS):
            print "Evaluate configuration: %d; result:" % i,
            configuration = sampler.sample_configuration()
            D_ = copy.deepcopy(D)
            evaluator = HoldoutEvaluator(D_, configuration,
                                         all_scoring_functions=True)
            if not self._fit(evaluator):
                print
                continue

            err.append(evaluator.predict())
            print err[-1]

            self.assertIsInstance(err[-1], dict)
            for key in err[-1]:
                self.assertEqual(len(err[-1]), 5)
                self.assertTrue(np.isfinite(err[-1][key]))
                self.assertGreaterEqual(err[-1][key], 0.0)

        print "Number of times it was worse than random guessing:" + str(
            np.sum(err > 1))


    def test_evaluate_multilabel_classification(self):
        X_train, Y_train, X_test, Y_test = get_dataset('iris')
        Y_train = np.array(convert_to_bin(Y_train, 3))
        Y_test = np.array(convert_to_bin(Y_test, 3))

        X_valid = X_test[:25, ]
        Y_valid = Y_test[:25, ]
        X_test = X_test[25:, ]
        Y_test = Y_test[25:, ]

        D = Dummy()
        D.info = {'metric': 'f1_metric', 'task': 'multilabel.classification',
                  'is_sparse': False}
        D.data = {'X_train': X_train, 'Y_train': Y_train,
                  'X_valid': X_valid, 'X_test': X_test}
        D.feat_type = ['numerical', 'Numerical', 'numerical', 'numerical']

        configuration_space = get_configuration_space(D.info)
        sampler = RandomSampler(configuration_space, 1)

        err = np.zeros([N_TEST_RUNS])
        for i in range(N_TEST_RUNS):
            print "Evaluate configuration: %d; result:" % i,
            configuration = sampler.sample_configuration()
            D_ = copy.deepcopy(D)
            evaluator = HoldoutEvaluator(D_, configuration)
            if not self._fit(evaluator):
                print
                continue
            err[i] = evaluator.predict()
            print err[i]

            self.assertTrue(np.isfinite(err[i]))
            self.assertGreaterEqual(err[i], 0.0)

        print "Number of times it was worse than random guessing:" + str(
            np.sum(err > 1))

    def test_evaluate_binary_classification(self):
        X_train, Y_train, X_test, Y_test = get_dataset('iris')

        eliminate_class_two = Y_train != 2
        X_train = X_train[eliminate_class_two]
        Y_train = Y_train[eliminate_class_two]

        eliminate_class_two = Y_test != 2
        X_test = X_test[eliminate_class_two]
        Y_test = Y_test[eliminate_class_two]

        X_valid = X_test[:25, ]
        Y_valid = Y_test[:25, ]
        X_test = X_test[25:, ]
        Y_test = Y_test[25:, ]

        D = Dummy()
        D.info = {'metric': 'auc_metric', 'task': 'binary.classification',
                  'is_sparse': False}
        D.data = {'X_train': X_train, 'Y_train': Y_train,
                  'X_valid': X_valid, 'X_test': X_test}
        D.feat_type = ['numerical', 'Numerical', 'numerical', 'numerical']

        configuration_space = get_configuration_space(D.info)
        sampler = RandomSampler(configuration_space, 1)

        err = np.zeros([N_TEST_RUNS])
        for i in range(N_TEST_RUNS):
            print "Evaluate configuration: %d; result:" % i,
            configuration = sampler.sample_configuration()
            D_ = copy.deepcopy(D)
            evaluator = HoldoutEvaluator(D_, configuration)

            if not self._fit(evaluator):
                print
                continue
            err[i] = evaluator.predict()
            self.assertTrue(np.isfinite(err[i]))
            print err[i]

            self.assertGreaterEqual(err[i], 0.0)

        print "Number of times it was worse than random guessing:" + str(
            np.sum(err > 1))

    def test_evaluate_regression(self):
        X_train, Y_train, X_test, Y_test = get_dataset('boston')

        X_valid = X_test[:200, ]
        Y_valid = Y_test[:200, ]
        X_test = X_test[200:, ]
        Y_test = Y_test[200:, ]

        D = Dummy()
        D.info = {'metric': 'r2_metric', 'task': 'regression',
                  'is_sparse': False}
        D.data = {'X_train': X_train, 'Y_train': Y_train,
                  'X_valid': X_valid, 'X_test': X_test}
        D.feat_type = ['numerical', 'Numerical', 'numerical', 'numerical',
                       'numerical', 'numerical', 'numerical', 'numerical',
                       'numerical', 'numerical', 'numerical']

        configuration_space = get_configuration_space(D.info)
        sampler = RandomSampler(configuration_space, 1)

        err = np.zeros([N_TEST_RUNS])
        for i in range(N_TEST_RUNS):
            print "Evaluate configuration: %d; result:" % i,
            configuration = sampler.sample_configuration()
            D_ = copy.deepcopy(D)
            evaluator = HoldoutEvaluator(D_, configuration)
            if not self._fit(evaluator):
                print
                continue
            err[i] = evaluator.predict()
            self.assertTrue(np.isfinite(err[i]))
            print err[i]

            self.assertGreaterEqual(err[i], 0.0)

        print "Number of times it was worse than random guessing:" + str(
            np.sum(err > 1))

    def _fit(self, evaluator):
        """Allow us to catch known and valid exceptions for all evaluate
        scripts."""
        try:
            evaluator.fit()
            return True
        except ValueError as e:
            if "Floating-point under-/overflow occurred at epoch" in e.message:
                return False
            else:
                raise e

    def test_file_output(self):
        output_dir = os.path.join(os.getcwd(), ".test")

        try:
            shutil.rmtree(output_dir)
        except:
            pass

        X_train, Y_train, X_test, Y_test = get_dataset('iris')
        X_valid = X_test[:25, ]
        Y_valid = Y_test[:25, ]
        X_test = X_test[25:, ]
        Y_test = Y_test[25:, ]

        D = Dummy()
        D.info = {'metric': 'bac_metric', 'task': 'multiclass.classification',
                  'is_sparse': False}
        D.data = {'X_train': X_train, 'Y_train': Y_train,
                  'X_valid': X_valid, 'X_test': X_test}
        D.feat_type = ['numerical', 'Numerical', 'numerical', 'numerical']
        D.basename = "test"


        configuration_space = get_configuration_space(D.info)
        sampler = RandomSampler(configuration_space, 1)

        while True:
            configuration = sampler.sample_configuration()
            evaluator = HoldoutEvaluator(D, configuration,
                                         with_predictions=True,
                                         all_scoring_functions=True,
                                         output_dir=output_dir,
                                         output_y_test=True)

            if not self._fit(evaluator):
                print
                continue
            evaluator.predict()
            evaluator.file_output()

            self.assertTrue(os.path.exists(os.path.join(output_dir,
                                                        "y_optimization.npy")))
            break


    def test_predict_proba_binary_classification(self):
        class Dummy(object):
            def predict_proba(self, y, batch_size=200):
                return np.array([[0.1, 0.9], [0.7, 0.3]])

        model = Dummy()
        task_type = "binary.classification"

        pred = predict_proba(None, model, task_type)
        expected = [[0.9], [0.3]]
        for i in range(len(expected)):
            self.assertEqual(expected[i], pred[i])



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_evaluate']
    unittest.main()
