import os
import sys
import itertools as it
import numpy as np
import string
import eights.utils
from numpy.random import rand

TESTS_PATH = os.path.dirname(os.path.realpath(sys.argv[0]))
DATA_PATH = os.path.join(TESTS_PATH, 'data')
EIGHTS_PATH = os.path.join(TESTS_PATH, '..')

def path_of_data(filename):
    return os.path.join(DATA_PATH, filename)

def generate_test_matrix(rows, cols, n_classes=2, types=[], random_state=None):
    full_types = list(it.chain(types, it.repeat(float, cols - len(types))))
    np.random.seed(random_state)
    cols = []
    for col_type in full_types:
        if col_type is int:
            col = np.random.randint(100, size=rows)
        elif issubclass(col_type, basestring):
            col = np.random.choice(list(string.uppercase), size=rows)
        else:
            col = np.random.random(size=rows)
        cols.append(col)
    labels = np.random.randint(n_classes, size=rows)
    M = eights.utils.sa_from_cols(cols)
    return M, labels

def generate_correlated_test_matrix(n_rows):
    M = rand(n_rows, 1)
    y = rand(n_rows) < M[:,0]
    return M, y

def array_equal(M1, M2, eps=1e-5):
    """
    unlike np.array_equal, works correctly for nan and ignores floating
    point errors up to eps
    """
    if M1.dtype != M2.dtype:
        return False
    for col_name, col_type in M1.dtype.descr:
        M1_col = M1[col_name]
        M2_col = M2[col_name]
        if 'f' not in col_type:
            if not(np.array_equal(M1_col, M2_col)):
                return False
        else:
            if not (np.all(np.logical_or(
                    abs(M1_col - M2_col) < eps,
                    np.logical_and(np.isnan(M1_col), np.isnan(M2_col))))):
                return False
    return True

