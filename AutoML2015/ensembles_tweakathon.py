'''
Created on Jan 7, 2015

@author: Aaron Klein
'''

import os
import sys
import glob
import cPickle
import numpy as np

from AutoSklearn.autosklearn import AutoSklearnClassifier

from HPOlibConfigSpace import configuration_space

from data.data_manager import DataManager
from ensembles import weighted_ensemble, ensemble_prediction
from util.get_dataset_info import getInfoFromFile
from models import evaluate


def load_predictions(dirs):
    pred = []
    pred_valid = []
    pred_test = []
    for d in dirs:
        dir_test = os.path.join(d, "predictions_test/")
        dir_valid = os.path.join(d, "predictions_valid/")
        dir_ensemble = os.path.join(d, "predictions_ensemble/")
        for f in os.listdir(dir_ensemble):
            p = np.load(os.path.join(dir_ensemble, f))
            if not np.isfinite(p).all():
                continue
            pred.append(p)

            p = np.load(os.path.join(dir_valid, f.replace("ensemble", "valid")))
            pred_valid.append(p)

            p = np.load(os.path.join(dir_test, f.replace("ensemble", "test")))
            pred_test.append(p)

    assert len(pred) > 0

    return np.array(pred), np.array(pred_valid), np.array(pred_test)


def load_predictions_of_nbest(dirs, nbest, labels, task_type, metric, load_all_predictions=False):

    # Initialize variables
    pred = []
    dirs_nbest = []
    for i in range(0, nbest):
        pred.append(0)
        dirs_nbest.append("")

    if load_all_predictions:
        pred_valid = []
        pred_test = []
        for i in range(0, nbest):
            pred_valid.append(0)
            pred_test.append(0)

    indices_nbest = np.zeros([nbest])
    performance_nbest = np.ones([nbest]) * sys.float_info.max

    for d in dirs:

        dir_ensemble = os.path.join(d, "predictions_ensemble/")
        if load_all_predictions:
            dir_test = os.path.join(d, "predictions_test/")
            dir_valid = os.path.join(d, "predictions_valid/")

        for m, f in enumerate(os.listdir(dir_ensemble)):
            p = np.load(os.path.join(dir_ensemble, f))
            if not np.isfinite(p).all():
                continue

            # Compute performance of current model
            performance = 1 - evaluate.calculate_score(labels, p, task_type, metric)

            # Keep performance of current model if it is better than the worst model in performance_nbest
            idx = np.argmax(performance_nbest)

            if(performance_nbest[idx] > performance):

                performance_nbest[idx] = performance
                indices_nbest[idx] = m
                dirs_nbest[idx] = d
                pred[idx] = p

                if load_all_predictions:
                    p = np.load(os.path.join(dir_valid, f.replace("ensemble", "valid")))
                    pred_valid[idx] = p
                    p = np.load(os.path.join(dir_test, f.replace("ensemble", "test")))
                    pred_test[idx] = p

    assert len(pred) > 0

    if load_all_predictions:
        return np.array(pred), np.array(pred_valid), np.array(pred_test), indices_nbest, dirs_nbest
    else:
        return np.array(pred), indices_nbest, dirs_nbest


def pick_nbest_models(pred, labels, task_type, metric, n_best=10):
    perf = np.zeros([pred.shape[0]])
    for i in range(0, pred.shape[0]):
        perf[i] = 1 - evaluate.calculate_score(labels, pred[i], task_type, metric)
    idx = np.argsort(perf)[:n_best]
    return idx


def pick_best_models(pred, labels, task_type, metric):
    best = []
    perf = np.zeros([pred.shape[0]])
    for i in range(0, pred.shape[0]):
        perf[i] = 1 - evaluate.calculate_score(labels, pred[i], task_type, metric)
        if perf[i] < 1.0:
            best.append(i)
    return np.array(best)


def train_models_on_complete_data(indices_nbest, dirs_nbest, X_train, Y_train, X_valid, X_test, task_type):
    params = []
    for i, d in enumerate(dirs_nbest):
        p = load_configuration(os.path.join(d, "smac_2_08_00-master.pkl"), indices_nbest[i])
        params.append(p)

    predictions_valid = []
    predictions_test = []
    for p in params:
        Y_valid, Y_test = train_model(p, X_train, Y_train, X_valid, X_test, task_type)
        predictions_valid.append(Y_valid)
        predictions_test.append(Y_test)

    return np.array(predictions_valid), np.array(predictions_test)


def train_model(params, X_train, Y_train, X_valid, X_test, task_type):
    for key in params:
        try:
            params[key] = float(params[key])
        except:
            pass
    cs = AutoSklearnClassifier.get_hyperparameter_search_space()
    configuration = configuration_space.Configuration(cs, **params)

    model = AutoSklearnClassifier(configuration, random_state=42)
    model.fit(X_train, Y_train)
    Y_valid = evaluate.predict_proba(X_valid, model, task_type)
    Y_test = evaluate.predict_proba(X_test, model, task_type)

    return Y_valid, Y_test


def load_configuration(pkl_file, index):
    fh = open(pkl_file, "rb")
    data_run = cPickle.load(fh)
    param = data_run['trials'][int(index)]['params']
    return param


def main(dataset):

    print "Use data set: " + str(dataset)
    path = "/home/feurerm/projects/automl_competition_2015/code/benchmarks/" + dataset + "/"

    # Debug
    #dirs = ["/home/feurerm/projects/automl_competition_2015/code/benchmarks/digits/smac_2_08_00-master_1000_2015-1-9--14-4-13-351537/"]
    dirs = glob.glob(path + "smac_2_08_00-*0_2015-1-9*")
    output_dir = "predictions_tweakathon/"
    data_dir = "/data/aad/automl_data/"
    n_best = 10

    print "Load labels from " + str(os.path.join(path, dataset + ".npy"))
    true_labels = np.load(os.path.join(path, dataset + ".npy"))

    print "Load predictions from " + path + " and determine the " + str(n_best) + " models"
    info = getInfoFromFile(data_dir, dataset)
    predictions, indices_nbest, dirs_nbest = load_predictions_of_nbest(dirs, n_best, true_labels, info['task'], info['metric'])

    print "Start optimization"
    weights = weighted_ensemble(predictions, true_labels, info['task'], info['metric'])
    print "Best weights found by CMA-ES: " + str(weights)

    print "Re-train models with the whole data set"
    D = DataManager(dataset, data_dir, verbose=True)
    predictions_valid, predictions_test = train_models_on_complete_data(indices_nbest, dirs_nbest, D.data['X_train'], D.data['Y_train'], D.data['X_valid'], D.data['X_test'], info['task'])

    print "Compute ensembles predictions for valid data"
    Y_valid = ensemble_prediction(predictions_valid, weights)

    print "Compute ensembles predictions for test data"
    Y_test = ensemble_prediction(predictions_test, weights)

    print "Save predictions in: " + output_dir

    np.savetxt(output_dir + dataset + "_valid_000.predict", Y_valid, delimiter=' ')
    np.savetxt(output_dir + dataset + "_test_000.predict", Y_test, delimiter=' ')

if __name__ == '__main__':
    #dataset = ["adult", "digits", "newsgroups", "dorothea", "cadata"]
    dataset = ["digits"]
    for d in dataset:
        main(d)
