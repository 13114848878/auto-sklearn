import numpy as np

from HPOlibConfigSpace.configuration_space import ConfigurationSpace
from HPOlibConfigSpace.hyperparameters import CategoricalHyperparameter

from ParamSklearn.components.preprocessor_base import \
    ParamSklearnPreprocessingAlgorithm
from ParamSklearn.util import DENSE, SPARSE, INPUT


class Balancing(ParamSklearnPreprocessingAlgorithm):
    def __init__(self, strategy, random_state=None):
        self.strategy = strategy

    def fit(self, X, y=None):
        raise NotImplementedError()

    def transform(self, X):
        raise NotImplementedError()

    def get_weights(self, Y, classifier, preprocessor, init_params, fit_params):
        if init_params is None:
            init_params = {}

        if fit_params is None:
            fit_params = {}

        # Classifiers which require sample weights:
        # We can have adaboost in here, because in the fit method,
        # the sample weights are normalized:
        # https://github.com/scikit-learn/scikit-learn/blob/0.15.X/sklearn/ensemble/weight_boosting.py#L121
        clf_ = ['adaboost', 'decision_tree', 'extra_trees', 'random_forest']
        pre_ = ['extra_trees_preproc_for_classification']
        if classifier in clf_ or preprocessor in pre_:
            if len(Y.shape) > 1:
                offsets = [2 ** i for i in range(Y.shape[1])]
                Y_ = np.sum(Y * offsets, axis=1)
            else:
                Y_ = Y

            unique, counts = np.unique(Y_, return_counts=True)
            cw = 1. / counts
            cw = cw / np.mean(cw)

            sample_weights = np.ones(Y_.shape)

            for i, ue in enumerate(unique):
                mask = Y_ == ue
                sample_weights[mask] *= cw[i]

            if classifier in clf_:
                fit_params['%s:sample_weight' % classifier] = sample_weights
            if preprocessor in pre_:
                fit_params['%s:sample_weight' % preprocessor] = sample_weights

        # Classifiers which can adjust sample weights themselves via the
        # argument `class_weight`
        clf_ = ['liblinear_svc', 'libsvm_svc', 'sgd']
        pre_ = ['liblinear_svc_preprocessor']
        if classifier in clf_:
            init_params['%s:class_weight' % classifier] = 'auto'
        if preprocessor in pre_:
            init_params['%s:class_weight' % preprocessor] = 'auto'

        clf_ = ['ridge']
        if classifier in clf_:
            class_weights = {}

            unique, counts = np.unique(Y, return_counts=True)
            cw = 1. / counts
            cw = cw / np.mean(cw)

            for i, ue in enumerate(unique):
                class_weights[ue] = cw[i]

            if classifier in clf_:
                init_params['%s:class_weight' % classifier] = class_weights

        return init_params, fit_params

    @staticmethod
    def get_properties():
        return {'shortname': 'Balancing',
                'name': 'Balancing Imbalanced Class Distributions',
                'handles_missing_values': True,
                'handles_nominal_values': True,
                'handles_numerical_features': True,
                'prefers_data_scaled': False,
                'prefers_data_normalized': False,
                'handles_regression': False,
                'handles_classification': True,
                'handles_multiclass': True,
                'handles_multilabel': True,
                'is_deterministic': True,
                'handles_sparse': True,
                'handles_dense': True,
                'input': (DENSE, SPARSE),
                'output': INPUT,
                'preferred_dtype': None}

    @staticmethod
    def get_hyperparameter_search_space(dataset_properties=None):
        # TODO add replace by zero!
        strategy = CategoricalHyperparameter(
            "strategy", ["none", "weighting"], default="none")
        cs = ConfigurationSpace()
        cs.add_hyperparameter(strategy)
        return cs

    def __str__(self):
        name = self.get_properties()['name']
        return "ParamSklearn %s" % name
