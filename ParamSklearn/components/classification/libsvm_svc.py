import resource

import sklearn.svm

from HPOlibConfigSpace.configuration_space import ConfigurationSpace
from HPOlibConfigSpace.conditions import EqualsCondition, InCondition
from HPOlibConfigSpace.hyperparameters import UniformFloatHyperparameter, \
    UniformIntegerHyperparameter, CategoricalHyperparameter, \
    UnParametrizedHyperparameter

from ParamSklearn.components.base import ParamSklearnClassificationAlgorithm
from ParamSklearn.constants import *
from ParamSklearn.implementations.util import softmax


class LibSVM_SVC(ParamSklearnClassificationAlgorithm):
    def __init__(self, C, kernel, gamma, shrinking, tol, max_iter,
                 class_weight=None, degree=3, coef0=0, random_state=None):
        self.C = C
        self.kernel = kernel
        self.degree = degree
        self.gamma = gamma
        self.coef0 = coef0
        self.shrinking = shrinking
        self.tol = tol
        self.class_weight = class_weight
        self.max_iter = max_iter
        self.random_state = random_state
        self.estimator = None

    def fit(self, X, Y):
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            soft /= 1024 * 1024
            print(soft,)
            maxrss = resource.getrusage(resource.RUSAGE_SELF)[2] / 1024
            cache_size = (soft - maxrss) / 1.5
        except Exception:
            cache_size = 200

        self.C = float(self.C)
        if self.degree is None:
            self.degree = 3
        else:
            self.degree = int(self.degree)
        if self.gamma is None:
            self.gamma = 0.0
        else:
            self.gamma = float(self.gamma)
        if self.coef0 is None:
            self.coef0 = 0.0
        else:
            self.coef0 = float(self.coef0)
        self.tol = float(self.tol)
        self.max_iter = float(self.max_iter)
        self.shrinking = self.shrinking == 'True'

        if self.class_weight == "None":
            self.class_weight = None

        self.estimator = sklearn.svm.SVC(C=self.C,
                                         kernel=self.kernel,
                                         degree=self.degree,
                                         gamma=self.gamma,
                                         coef0=self.coef0,
                                         shrinking=self.shrinking,
                                         tol=self.tol,
                                         class_weight=self.class_weight,
                                         max_iter=self.max_iter,
                                         random_state=self.random_state,
                                         cache_size=cache_size)
                                         # probability=True)
        self.estimator.fit(X, Y)
        return self

    def predict(self, X):
        if self.estimator is None:
            raise NotImplementedError
        return self.estimator.predict(X)

    def predict_proba(self, X):
        if self.estimator is None:
            raise NotImplementedError()
        # return self.estimator.predict_proba(X)
        decision = self.estimator.decision_function(X)
        return softmax(decision)


    @staticmethod
    def get_properties(dataset_properties=None):
        return {'shortname': 'LibSVM-SVC',
            'name': 'LibSVM Support Vector Classification',
            'handles_missing_values': False,
            'handles_nominal_values': False,
            'handles_numerical_features': True,
            'prefers_data_scaled': True,
            # TODO find out if this is good because of sparsity...
            'prefers_data_normalized': False,
            'handles_regression': False,
            'handles_classification': True,
            'handles_multiclass': True,
            'handles_multilabel': False,
            'is_deterministic': True,
            # TODO find out of this is right!
            # this here suggests so http://scikit-learn.org/stable/modules/svm.html#tips-on-practical-use
            'handles_sparse': True,
            'input': (DENSE, SPARSE, UNSIGNED_DATA),
            'output': (PREDICTIONS,),
            # TODO find out what is best used here!
            # C-continouos and double precision...
            'preferred_dtype': None}

    @staticmethod
    def get_hyperparameter_search_space(dataset_properties=None):
        C = UniformFloatHyperparameter("C", 0.03125, 32768, log=True,
                                       default=1.0)
        # No linear kernel here, because we have liblinear
        kernel = CategoricalHyperparameter(name="kernel",
                                           choices=["rbf", "poly", "sigmoid"],
                                           default="rbf")
        degree = UniformIntegerHyperparameter("degree", 1, 5, default=3)
        gamma = UniformFloatHyperparameter("gamma", 3.0517578125e-05, 8,
                                           log=True, default=0.1)
        # TODO this is totally ad-hoc
        coef0 = UniformFloatHyperparameter("coef0", -1, 1, default=0)
        # probability is no hyperparameter, but an argument to the SVM algo
        shrinking = CategoricalHyperparameter("shrinking", ["True", "False"],
                                              default="True")
        tol = UniformFloatHyperparameter("tol", 1e-5, 1e-1, default=1e-4,
                                         log=True)
        # cache size is not a hyperparameter, but an argument to the program!
        max_iter = UnParametrizedHyperparameter("max_iter", -1)

        cs = ConfigurationSpace()
        cs.add_hyperparameter(C)
        cs.add_hyperparameter(kernel)
        cs.add_hyperparameter(degree)
        cs.add_hyperparameter(gamma)
        cs.add_hyperparameter(coef0)
        cs.add_hyperparameter(shrinking)
        cs.add_hyperparameter(tol)
        cs.add_hyperparameter(max_iter)

        degree_depends_on_poly = EqualsCondition(degree, kernel, "poly")
        coef0_condition = InCondition(coef0, kernel, ["poly", "sigmoid"])
        cs.add_condition(degree_depends_on_poly)
        cs.add_condition(coef0_condition)

        return cs
