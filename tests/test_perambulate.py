import unittest

from sklearn import datasets

import utils_for_tests as utils
utils.add_to_python_path()

from eights.perambulate.perambulate import *

class TestPerambulate(unittest.TestCase):

    def test_run_experiment(self):
        iris = datasets.load_iris()
        y = iris.target
        M = iris.data
        clfs = {RF: {}}
        subsets = {SWEEP_TRAINING_SIZE: {'subset_size': [20, 40, 60, 80, 100]}}
        cvs = {STRAT_ACTUAL_K_FOLD: {}}
        exp = Experiment(M, y, clfs, subsets, cvs)
        print exp.average_score()

    def test_slice_on_dimension(self):
        iris = datasets.load_iris()
        y = iris.target
        M = iris.data
        clfs = {RF: {'n_estimators': [10, 100], 'max_depth': [1, 10]}, 
                SVC: {'kernel': ['linear', 'rbf']}}        
        subsets = {SWEEP_TRAINING_SIZE: {'subset_size': [20, 40, 60, 80, 100]}}
        cvs = {STRAT_ACTUAL_K_FOLD: {}}
        exp = Experiment(M, y, clfs, subsets, cvs)
        for trial in exp.slice_on_dimension(CLF_ID, RF):
            print trial
        print
        for trial in exp.slice_on_dimension(SUBSET_PARAMS, {'subset_size': 60}):
            print trial

    def test_slice_by_best_score(self):
        iris = datasets.load_iris()
        y = iris.target
        M = iris.data
        clfs = {RF: {'n_estimators': [10, 100], 'max_depth': [1, 10]}, 
                SVC: {'kernel': ['linear', 'rbf']}}        
        subsets = {SWEEP_TRAINING_SIZE: {'subset_size': [20, 40, 60, 80, 100]}}
        cvs = {STRAT_ACTUAL_K_FOLD: {}}
        exp = Experiment(M, y, clfs, subsets, cvs)
        for trial in exp.run():
            print trial, trial.average_score()
        print
        for trial in exp.slice_by_best_score(CLF_PARAMS):
            print trial, trial.average_score()

if __name__ == '__main__':
    unittest.main()
	

