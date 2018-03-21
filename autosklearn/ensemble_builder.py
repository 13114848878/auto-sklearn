# -*- encoding: utf-8 -*-

import multiprocessing
import glob
import os
import re
import time
import traceback

import numpy as np
import pynisher

from autosklearn.util.backend import Backend
from autosklearn.constants import BINARY_CLASSIFICATION
from autosklearn.metrics import calculate_score
from autosklearn.ensembles.ensemble_selection import EnsembleSelection
from autosklearn.ensembles.abstract_ensemble import AbstractEnsemble
from autosklearn.util.logging_ import get_logger


class EnsembleBuilder(multiprocessing.Process):
    def __init__(
            self,
            backend: Backend,
            dataset_name: str,
            task_type: int,
            metric: str,
            limit: int,
            ensemble_size: int=10,
            ensemble_nbest: int=100,
            seed: int=1,
            shared_mode: bool=False,
            max_iterations: int=None,
            precision: str="32",
            sleep_duration: int=2,
            memory_limit: int=1000,
            read_at_most: int=5,
    ):
        """
            Constructor
            
            Parameters
            ----------
            backend: util.backend.Backend
                backend to write and read files
            dataset_name: str
                name of dataset
            task_type: int
                type of ML task
            metric: str
                name of metric to score predictions
            limit: int
                time limit in sec
            ensemble_size: int
                maximal size of ensemble (passed to autosklearn.ensemble.ensemble_selection)
            ensemble_nbest: int
                consider only the n best prediction (wrt validation predictions)
            seed: int
                random seed
                if set to -1, read files with any seed (e.g., for shared model mode)
            shared_model: bool
                auto-sklearn used shared model mode (aka pSMAC)
            max_iterations: int
                maximal number of iterations to run this script
                (default None --> deactivated)
            precision: ["16","32","64","128"]
                precision of floats to read the predictions 
            sleep_duration: int
                duration of sleeping time between two iterations of this script (in sec)
            memory_limit: int
                memory limit in mb
            read_at_most: int 
                read at most n new prediction files in each iteration
        """

        super(EnsembleBuilder, self).__init__()

        self.backend = backend  # communication with filesystem
        self.dataset_name = dataset_name
        self.task_type = task_type
        self.metric = metric
        self.time_limit = limit  # time limit
        self.ensemble_size = ensemble_size
        self.ensemble_nbest = ensemble_nbest  # max number of members that will be used for building the ensemble
        self.seed = seed
        self.shared_mode = shared_mode  # pSMAC?
        self.max_iterations = max_iterations
        self.precision = precision
        self.sleep_duration = sleep_duration
        self.memory_limit = memory_limit
        self.read_at_most = read_at_most
        
        # part of the original training set
        # used to build the ensemble
        self.dir_ensemble = os.path.join(
            self.backend.temporary_directory,
            '.auto-sklearn',
            'predictions_ensemble',
        )

        # validation set (public test set) -- y_true not known
        self.dir_valid = os.path.join(
            self.backend.temporary_directory,
            '.auto-sklearn',
            'predictions_valid',
        )
        # test set (private test set) -- y_true not known
        self.dir_test = os.path.join(
            self.backend.temporary_directory,
            '.auto-sklearn',
            'predictions_test',
        )

        logger_name = 'EnsembleBuilder(%d):%s' % (self.seed, self.dataset_name)
        self.logger = get_logger(logger_name)

        self.start_time = 0
        self.model_fn_re = re.compile(r'_([0-9]*)_([0-9]*)\.npy')
        
        # already read prediction files
        # {"file name": {
        #    "ens_score": float
        #    "mtime_ens": str,
        #    "mtime_valid": str,
        #    "mtime_test": str,
        #    "seed": int,
        #    "num_run": int,
        #    "y_ensemble": np.ndarray
        #    "y_valid": np.ndarray
        #    "y_test": np.ndarray
        # }
        self.read_preds = {}
        self.last_hash = None  # hash of ensemble training data
        self.y_true_ensemble = None
        self.SAVE2DISC = True

    def run(self):
        buffer_time = 5  # TODO: Buffer time should also be used in main!?
        while True:
            time_left = self.time_limit - buffer_time
            safe_ensemble_script = pynisher.enforce_limits(
                wall_time_in_s=int(time_left),
                mem_in_mb=self.memory_limit,
                logger=self.logger
            )(self.main)
            safe_ensemble_script()
            if safe_ensemble_script.exit_status is pynisher.MemorylimitException:
                # if ensemble script died because of memory error,
                # reduce nbest to reduce memory consumption and try it again
                if self.ensemble_nbest == 1:
                    self.logger.critical("Memory Exception -- Unable to escape from memory exception")
                else:
                    self.ensemble_nbest =  int(self.ensemble_nbest/2)
                    self.logger.warning("Memory Exception -- restart with less ensemle_nbest: %d" %(self.ensemble_nbest ))
                    # ATTENTION: main will start from scratch;
                    # all data structures are empty again
                    continue
            break

    def main(self):

        self.start_time = time.time()
        index_run = 0
        
        while True:

            #maximal number of iterations
            if (
                self.max_iterations is not None
                and self.max_iterations > 0
                and index_run >= self.max_iterations
            ):
                self.logger.info("Terminate ensemble building because of max iterations: %d of %d",
                                 self.max_iterations,
                                 index_run)
                break 
            
            used_time = time.time() - self.start_time
            self.logger.debug('Time left: %f', self.time_limit - used_time)
            
            # populates self.read_preds
            if not self.read_ensemble_preds():
                time.sleep(self.sleep_duration)
                continue
                
            selected_models = self.get_n_best_preds()
            if not selected_models: # nothing selected
                continue
            
            # populates predictions in self.read_preds
            # reduces selected models if file reading failed
            n_sel_valid, n_sel_test = self.\
                get_valid_test_preds(selected_keys=selected_models)
            
            selected_models_set = set(selected_models)
            if selected_models_set.intersection(n_sel_test):
                selected_models = list(selected_models_set.intersection(n_sel_test))
            elif selected_models_set.intersection(n_sel_valid):
                selected_models = list(selected_models_set.intersection(n_sel_valid))
            # else
                # use selected_models only defined by ensemble data set
            
            # train ensemble
            ensemble = self.fit_ensemble(selected_keys=selected_models)
            
            if ensemble is not None:
                
                self.predict(set_="valid", 
                             ensemble=ensemble, 
                             selected_keys=n_sel_valid, 
                             n_preds=len(selected_models), 
                             index_run=index_run)
                self.predict(set_="test", 
                             ensemble=ensemble, 
                             selected_keys=n_sel_test, 
                             n_preds=len(selected_models), 
                             index_run=index_run)
                index_run += 1
            else:
                time.sleep(self.sleep_duration)
            
    def read_ensemble_preds(self):
        """
            reading predictions on ensemble building data set; 
            populates self.read_preds
        """
        self.logger.debug("Read ensemble data set predictions")
        
        if self.y_true_ensemble is None:
            try:
                self.y_true_ensemble = self.backend.load_targets_ensemble()
            except FileNotFoundError:
                traceback.print_exc()
                self.logger.debug("Could not find true targets on ensemble dat"
                                  " set")
                return False
            
        # no validation predictions so far -- no dir
        if not os.path.isdir(self.dir_ensemble):
            self.logger.debug("No ensemble dataset prediction directory found")
            return False
        
        if self.seed > -1:
            pred_path = os.path.join(
                    self.dir_ensemble,
                    'predictions_ensemble_%s_*.npy' % self.seed)
        else:
            pred_path = os.path.join(
                    self.dir_ensemble,
                    'predictions_ensemble_*_*.npy')

        y_ens_files = glob.glob(pred_path)
        # no validation predictions so far -- no files
        if len(y_ens_files) == 0:
            self.logger.debug("Found no prediction files on ensemble data set:"
                              " %s" % pred_path)
            return False
        
        n_read_files = 0
        for y_ens_fn in y_ens_files:
            
            if self.read_at_most and n_read_files >= self.read_at_most:
                # limit the number of files that will be read 
                # to limit memory consumption
                break
            
            if not y_ens_fn.endswith(".npy"):
                self.logger.info('Error loading file (not .npy): %s', y_ens_fn)
                continue
            
            match = self.model_fn_re.search(y_ens_fn)
            _seed = int(match.group(1))
            _num_run = int(match.group(2))
            
            if not self.read_preds.get(y_ens_fn):
                self.read_preds[y_ens_fn] = {"ens_score": -1,
                                             "mtime_ens": 0,
                                             "mtime_valid": 0,
                                             "mtime_test": 0,
                                             "seed": _seed,
                                             "num_run": _num_run,
                                             "y_ensemble": None,
                                             "y_valid": None,
                                             "y_test": None}
                
            if self.read_preds[y_ens_fn]["mtime_ens"] == os.path.getmtime(y_ens_fn):
                # same time stamp; nothing changed;
                continue
            
            # actually read the predictions
            # and score them
            try:
                with open(y_ens_fn, 'rb') as fp:
                    y_ensemble = self._read_np_fn(fp=fp)
                    score = calculate_score(solution=self.y_true_ensemble,  # y_ensemble = y_true for ensemble set
                                            prediction=y_ensemble,
                                            task_type=self.task_type,
                                            metric=self.metric,
                                            all_scoring_functions=False)

                    self.read_preds[y_ens_fn]["ens_score"] = score
                    self.read_preds[y_ens_fn]["y_ensemble"] = y_ensemble
                    n_read_files += 1

            except:
                traceback.print_exc()
                self.logger.warning('Error loading %s', y_ens_fn)
                self.read_preds[y_ens_fn]["ens_score"] = -1
                
        return True
                
    def get_n_best_preds(self):
        """
            get best n predictions (i.e., keys of self.read_preds)
            according to score on "ensemble set" 
            n: self.ensemble_nbest
            
            Side effect: delete predictions of non-winning models
        """

        # Sort by score
        sorted_keys = sorted(
            [
                [k, v["ens_score"], v["num_run"]]
                for k, v in self.read_preds.items()
            ],
            key=lambda x: x[1],
        )
        # remove all that are at most as good as random (<0.001)
        sorted_keys = filter(lambda x: x[1] > 0.001, sorted_keys)
        # remove Dummy Classifier
        sorted_keys = list(filter(lambda x: x[2] > 1, sorted_keys))
        if not sorted_keys: 
            # no model left; try to use dummy classifier (num_run==0)
            self.logger.warning("No models better than random - using Dummy Classifier!")
            # TODO: Check if this works correctly?
            sorted_keys = [
                [k] for k, v in self.read_preds.items()
                if v["seed"] == self.seed and v["num_run"] == 1
            ]
        # reduce to keys
        sorted_keys = list(map(lambda x: x[0], sorted_keys))
        # remove loaded predictions for non-winning models
        for k in sorted_keys[self.ensemble_nbest:]:
            self.read_preds[k]["y_ensemble"] = None
            self.read_preds[k]["y_valid"] = None
            self.read_preds[k]["y_test"] = None
        # return best scored keys of self.read_preds
        return sorted_keys[:self.ensemble_nbest]

    def get_valid_test_preds(self, selected_keys: list):
        """
            get valid and test predictions from disc
            and store them in self.read_preds
            
            Parameters
            ---------
            selected_keys: list
                list of selected keys of self.read_preds
                
            Return
            ------
            success_keys:
                all keys in selected keys for which we could read the valid and test predictions
        """
        success_keys_valid = []
        success_keys_test = []
        
        for k in selected_keys:
            valid_fn = glob.glob(
                os.path.join(self.dir_valid, 'predictions_valid_%d_*0%d.npy'
                                    % (self.read_preds[k]["seed"],
                                       self.read_preds[k]["num_run"])))
            test_fn = glob.glob(
                os.path.join(self.dir_test, 'predictions_test_%d_*0%d.npy' %
                                   (self.read_preds[k]["seed"],
                                    self.read_preds[k]["num_run"])))
            
            # TODO don't read valid and test if not changed
            
            if len(valid_fn) == 0:
                self.logger.debug("Not found validation prediction file "
                                  "(although ensemble predictions available): "
                                  "%s" % valid_fn)
            else:
                valid_fn = valid_fn[0]
                if self.read_preds[k]["mtime_valid"] == os.path.getmtime(valid_fn) \
                        and self.read_preds[k]["y_valid"] is not None:
                    continue
                try:
                    with open(valid_fn, 'rb') as fp:
                        y_valid = self._read_np_fn(fp)
                        self.read_preds[k]["y_valid"] = y_valid
                        success_keys_valid.append(k)
                        self.read_preds[k]["mtime_valid"] = os.path.getmtime(valid_fn)
                except Exception as e:
                    traceback.print_exc()
                    self.logger.warning('Error loading %s: %s - %s',
                                        valid_fn, type(e), e)
        
            if len(test_fn) == 0:
                self.logger.debug("Not found test prediction file (although "
                                  "ensemble predictions available):%s" %
                                  test_fn)
            else:
                test_fn = test_fn[0]
                if self.read_preds[k]["mtime_test"] == \
                        os.path.getmtime(test_fn) \
                        and self.read_preds[k]["y_test"] is not None:
                    continue
                try:
                    with open(test_fn, 'rb') as fp:
                        y_test = self._read_np_fn(fp)
                        self.read_preds[k]["y_test"] = y_test
                        success_keys_test.append(k)
                        self.read_preds[k]["mtime_test"] = os.path.getmtime(test_fn)
                except Exception as e:
                    traceback.print_exc()
                    self.logger.warning('Error loading %s: %s - %s',
                                        test_fn, type(e), e)
                
        return success_keys_valid, success_keys_test
        
    def fit_ensemble(self, selected_keys:list):
        """
            fit ensemble 
            
            Parameters
            ---------
            selected_keys: list
                list of selected keys of self.read_preds
                
            Returns
            -------
            ensemble: EnsembleSelection
                trained Ensemble
        """
        
        predictions_train = np.array([self.read_preds[k]["y_ensemble"] for k in selected_keys])
        include_num_runs = [(self.read_preds[k]["seed"], self.read_preds[k]["num_run"]) for k in selected_keys]
        
        # check hash if ensemble training data changed
        current_hash = hash(predictions_train.data.tobytes())
        if self.last_hash == current_hash:
            self.logger.debug("No new model predictions selected -- skip ensemble building")
            return None
        self.last_hash = current_hash
        
        ensemble = EnsembleSelection(ensemble_size=self.ensemble_size,
                                     task_type=self.task_type,
                                     metric=self.metric)
        
        try:
            self.logger.debug("Fit Ensemble")
            ensemble.fit(predictions_train, self.y_true_ensemble,
                         include_num_runs)
            self.logger.info(ensemble)

        except ValueError as e:
            traceback.print_exc()
            self.logger.error('Caught ValueError: ' + str(e))
            time.sleep(self.sleep_duration)
            return None
        except IndexError as e:
            traceback.print_exc()
            self.logger.error('Caught IndexError: ' + str(e))
            time.sleep(self.sleep_duration)
            return None
        
        return ensemble
    
    def predict(self, set_: str,
                ensemble: AbstractEnsemble,
                selected_keys: list, 
                n_preds:int, 
                index_run:int):
        """
            save preditions on ensemble, validation and test data on disc
            
            Parameters
            ----------
            set_: ["valid","test"]
                data split name
            ensemble: EnsembleSelection
                trained Ensemble
            selected_keys: list
                list of selected keys of self.read_preds
            n_preds: int
                number of prediction models used for ensemble building
                same number of predictions on valid and test are necessary
            index_run: int
                n-th time that ensemble predictions are written to disc
                
            Return
            ------
            y: np.ndarray
        """
        self.logger.debug("Predict with Ensemble")
        
        # Save the ensemble for later use in the main auto-sklearn module!
        if self.SAVE2DISC:
            self.backend.save_ensemble(ensemble, index_run, self.seed)

        predictions_valid = np.array([self.read_preds[k]["y_%s" % set_] for k in selected_keys])
        
        if n_preds == predictions_valid.shape[0]:
            y = ensemble.predict(predictions_valid)
            if self.task_type == BINARY_CLASSIFICATION:
                y = y[:,1]
            if self.SAVE2DISC:
                self.backend.save_predictions_as_txt(y, set_, index_run, prefix=self.dataset_name)
            return y
        else:
            self.logger.debug("Less predictions on %s -- no ensemble predictions on %s" %(set_, set_))
            return None
        # TODO: ADD saving of predictions on "ensemble data"
    
    def _read_np_fn(self, fp):
        if self.precision is "16":
            predictions = np.load(fp).astype(dtype=np.float16)
        elif self.precision is "32":
            predictions = np.load(fp).astype(dtype=np.float32)
        elif self.precision is "64":
            predictions = np.load(fp).astype(dtype=np.float64)
        else:
            predictions = np.load(fp)
        return predictions
