import os
import sys
import itertools as it
import numpy as np
import string
import eights.utils
from numpy.random import rand, seed
from contextlib import contextmanager
from StringIO import StringIO

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
    seed(0)
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

@contextmanager
def rerout_stdout():
    """
    print statements within the context are rerouted to a StringIO, which
    can be examined with the method that is yielded here.

    Examples
    --------
    >>> print 'This text appears in the console'
    This text appears in the console
    >>> with rerout_stdout() as get_rerouted_stdout:
    ...    print 'This text does not appear in the console'
    ...     # get_rerouted_stdout is a function that gets our rerouted output
    ...     assert(get_rerouted_stdout().strip() == 'This text does not appear in the console')
    >>> print 'This text also appears in the console'
    This text also appears in the console
    """
    # based on http://stackoverflow.com/questions/4219717/how-to-assert-output-with-nosetest-unittest-in-python
    saved_stdout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        yield out.getvalue
    finally:
        sys.stdout = saved_stdout
