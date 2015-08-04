import abc
import copy
import inspect
import numpy as np
import itertools as it
from collections import Counter
from random import sample
from sklearn.cross_validation import _PartitionIterator
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score
from sklearn.metrics import f1_score
from sklearn.metrics import precision_recall_curve

class _BaseSubsetIter(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, y):
        self._y = y
    
    @abc.abstractmethod
    def __iter__(self):
        yield (np.array([], dtype=int), {})

    @abc.abstractmethod
    def __repr__(self):
        return 'BaseSubsetIter()'

class SubsetNoSubset(_BaseSubsetIter):
    def __iter__(self):
        yield (np.arange(self._y.shape[0]), {})

    def __repr__(self):
        return 'SubsetNoSubset()'

class SubsetRandomRowsActualDistribution(_BaseSubsetIter):
        
    def __init__(self, y, subset_size, n_subsets=3):
        super(SubsetRandomRowsActualDistribution, self).__init__(y)
        self.__subset_size = subset_size
        self.__n_subsets = n_subsets

    def __iter__(self):
        y = self._y
        subset_size = self.__subset_size
        n_subsets = self.__n_subsets
        count = Counter(y)
        size_space = float(sum(count.values()))
        proportions = {key: count[key] / size_space for key in count}
        n_choices = {key: int(proportions[key] * subset_size) for 
                     key in proportions}
        indices = {key: np.where(y == key)[0] for key in count}
        for i in xrange(n_subsets):
            samples = {key: sample(indices[key], n_choices[key]) for key in count}
            all_indices = np.sort(np.concatenate(samples.values()))
            yield (all_indices, {'sample_num': i})

    def __repr__(self):
        return 'SubsetRandomRowsActualDistribution(subset_size={}, n_subsets={})'.format(
                self.__subset_size,
                self.__n_subsets)

class SubsetRandomRowsEvenDistribution(_BaseSubsetIter):
        
    def __init__(self, y, subset_size, n_subsets=3):
        super(SubsetRandomRowsEvenDistribution, self).__init__(y)
        self.__subset_size = subset_size
        self.__n_subsets = n_subsets

    def __iter__(self):
        y = self._y
        subset_size = self.__subset_size
        n_subsets = self.__n_subsets
        count = Counter(y)
        n_categories = len(count)
        proportions = {key: 1.0 / n_categories for key in count}
        n_choices = {key: int(proportions[key] * subset_size) for 
                     key in proportions}
        indices = {key: np.where(y == key)[0] for key in count}
        for i in xrange(n_subsets):
            samples = {key: sample(indices[key], n_choices[key]) for key in count}
            all_indices = np.sort(np.concatenate(samples.values()))
            yield (all_indices, {'sample_num': i})

    def __repr__(self):
        return 'SubsetRandomRowsEvenDistribution(subset_size={}, n_subsets={})'.format(
                self.__subset_size,
                self.__n_subsets)

class SubsetSweepNumRows(_BaseSubsetIter):
        
    def __init__(self, y, num_rows):
        super(SubsetSweepNumRows, self).__init__(y)
        self.__num_rows = num_rows

    def __iter__(self):
        y = self._y
        num_rows = self.__num_rows
        for rows in num_rows:
            all_indices = np.sort(sample(np.arange(0, y.shape[0]), rows))
            yield (all_indices, {'rows': rows})

    def __repr__(self):
        return 'SubsetSweepNumRows(num_rows={})'.format(
                self.__num_rows)

class SubsetSweepVaryStratification(_BaseSubsetIter):
        
    def __init__(self, y, proportions_positive, subset_size):
        super(SubsetSweepVaryStratification, self).__init__(y)
        self.__proportions_positive = proportions_positive
        self.__subset_size = subset_size

    def __iter__(self):
        y = self._y
        subset_size = self.__subset_size
        positive_cases = np.where(y)[0]
        negative_cases = np.where(np.logical_not(y))[0]
        for prop_pos in self.__proportions_positive:
            positive_sample = sample(positive_cases, int(subset_size * prop_pos))
            negative_sample = sample(negative_cases, int(subset_size * (1 - prop_pos)))
            # If one of these sets is empty, concatentating them casts to float, so we have
            # to cast it back (hence the astype)
            all_indices = np.sort(np.concatenate([positive_sample, negative_sample])).astype(int)
            yield (all_indices, 'prop_positive={}'.format(prop_pos))

    def __repr__(self):
        return 'SubsetSweepVaryStratification(proportions_positive={}, subset_size={})'.format(
                self.__proportions_positive,
                self.__subset_size)

class SubsetSweepExcludeColumns(_BaseSubsetIter):
    """
    
    Analyze feature importance when each of a specified set of columns are
    excluded. 
    
    Parameters
    ----------
    M : Numpy structured array
    cols_to_exclude : list of str or None
         List of names of columns to exclude one at a time. If None, tries
         all columns
         
    Returns
    -------
    Numpy Structured array
        First col
            Excluded col name
        Second col
            Accuracy score
        Third col
            Feature importances
    """
    # not providing cv because it's always Kfold
    # returns fitted classifers along a bunch of metadata
    #Why don't we use this as buildinger for slices. AKA the way the cl
    # 
    def __init__(self, M, cols_to_exclude=None):
        raise NotImplementedError

class SubsetSweepLeaveOneColOut(_BaseSubsetIter):
    # TODO
    #returns list of list eachone missing a value in order.  
    #needs to be tested
    pass


# TODO By and large, we shouldn't be using SKLearn's internal classes.
class NoCV(_PartitionIterator):
    """Cross validator that just returns the entire set as the training set
    to begin with

    Parameters
    ----------
    n : int
        The number of rows in the data
    """
    def _iter_test_indices(self):
        yield np.array([], dtype=int)

class SlidingWindowIdx(_PartitionIterator):

    def __init__(self, n, train_start, train_window_size, test_start, 
                 test_window_size, inc_value, expanding_train=False):
       super(SlidingWindowIdx, self).__init__(n)
       self.__n = n
       self.__train_start = train_start
       self.__train_window_size = train_window_size
       self.__train_end = train_start + train_window_size - 1
       self.__test_start = test_start
       self.__test_window_size = test_window_size
       self.__test_end = test_start + test_window_size - 1
       self.__inc_value = inc_value
       self.__expanding_train = expanding_train

    def cv_note(self):
        return {'train_start': self.__train_start,
                'train_end': self.__train_end,
                'test_start': self.__test_start,
                'test_end': self.__test_end}
                
    def _iter_test_indices(self):
        inc_value = self.__inc_value
        while self.__test_end < self.__n:
            yield np.arange(self.__test_start, self.__test_end + 1)
            if not self.__expanding_train:
                self.__train_start += inc_value
            self.__train_end += inc_value
            self.__test_start += inc_value
            self.__test_end += inc_value

    def __iter__(self):
        # _PartitionIterator assumes we're training on everything we're not
        # testing. We have to patch it's __iter__ so that isn't the case
        for train_index, test_index in super(
            SlidingWindowIdx, self).__iter__():
            yield (np.arange(self.__train_start, self.__train_end + 1), 
                   test_index)

# TODO should take col name, not col idx
class SlidingWindowValue(_PartitionIterator):
    def __init__(self, M, col_idx, train_start, train_window_size, test_start, 
                 test_window_size, inc_value, expanding_train=False):
        y = M[:,col_idx]
        n = y.shape[0] 
        super(SlidingWindowValue, self).__init__(n)
        self.__y = y
        self.__n = n
        self.__train_start = train_start
        self.__train_window_size = train_window_size
        self.__train_end = train_start + train_window_size - 1
        self.__test_start = test_start
        self.__test_window_size = test_window_size
        self.__test_end = test_start + test_window_size - 1
        self.__inc_value = inc_value
        self.__expanding_train = expanding_train

    def cv_note(self):
        return {'train_start': self.__train_start,
                'train_end': self.__train_end,
                'test_start': self.__test_start,
                'test_end': self.__test_end}
                
    def _iter_test_indices(self):
        inc_value = self.__inc_value
        y = self.__y
        self.__test_mask = np.logical_and(
            y >= self.__test_start,
            y <= self.__test_end)
        self.__train_mask = np.logical_and(
            y >= self.__train_start,
            y <= self.__train_end)
        while np.any(self.__test_mask):
            yield self.__test_mask.nonzero()[0]
            if not self.__expanding_train:
                self.__train_start += inc_value
            self.__train_end += inc_value
            self.__test_start += inc_value
            self.__test_end += inc_value
            self.__test_mask = np.logical_and(
                y >= self.__test_start,
                y <= self.__test_end)
            self.__train_mask = np.logical_and(
                y >= self.__train_start,
                y <= self.__train_end)

    def __iter__(self):
        # _PartitionIterator assumes we're training on everything we're not
        # testing. We have to patch it's __iter__ so that isn't the case
        for train_index, test_index in super(
            SlidingWindowValue, self).__iter__():
            yield (self.__train_mask.nonzero()[0], test_index)


CLF, CLF_PARAMS, SUBSET, SUBSET_PARAMS, CV, CV_PARAMS = range(6)
dimensions = (CLF, CLF_PARAMS, SUBSET, SUBSET_PARAMS, CV, CV_PARAMS)
dimension_descr = {CLF: 'classifier',
                   CLF_PARAMS: 'classifier parameters',
                   SUBSET: 'subset type',
                   SUBSET_PARAMS: 'subset parameters',
                   CV: 'cross-validation method',
                   CV_PARAMS: 'cross-validation parameters'}
    
all_subset_notes = sorted(['sample_num', 'rows', 'prop_positive', 
                           'excluded_col',])

all_subset_notes_backindex = {name: i for i, name in 
                              enumerate(all_subset_notes)}

all_cv_notes = sorted(['train_start', 'train_end', 'test_start', 
                        'test_end', 'fold']) 

all_cv_notes_backindex = {name: i for i, name in 
                              enumerate(all_cv_notes)}

class Run(object):
    def __init__(
        self,
        M,
        y,
        clf,
        train_indices,
        test_indices,
        subset_note,
        cv_note):
        self.M = M
        self.y = y
        self.clf = clf
        self.test_indices = test_indices
        self.train_indices = train_indices
        self.subset_note = subset_note
        self.cv_note = cv_note

    def __repr__(self):
        return 'Run(clf={}, subset_note={}, cv_note={})'.format(
                self.clf, self.subset_note, self.cv_note)

    def __test_M(self):
        return self.M[self.test_indices]

    def __test_y(self):
        return self.y[self.test_indices]

    def __pred_proba(self):
        return self.clf.predict_proba(self.__test_M())[:,1]

    def __predict(self):
        return self.clf.predict(self.__test_M())

    @staticmethod
    def csv_header():
        return (['subset_note_' + name for name in all_subset_notes] + 
                ['cv_note_' + name for name in all_cv_notes] + 
                ['f1_score', 'prec@1%', 'prec@2%', 'prec@5%', 
                 'prec@10%', 'prec@20%'])

    def __subset_note_list(self):
        notes = [''] * len(all_subset_notes)
        for name, val in self.subset_note.iteritems():
            notes[all_subset_notes_backindex[name]] = str(val)
        return notes

    def __cv_note_list(self):
        notes = [''] * len(all_cv_notes)
        for name, val in self.cv_note.iteritems():
            notes[all_cv_notes_backindex[name]] = str(val)
        return notes

    def csv_row(self):
        return (self.__subset_note_list() +
                self.__cv_note_list() + 
                [self.f1_score()] + 
                self.precision_at_thresholds([.01, .02, .05, .10,
                                              .20]).tolist())

    def score(self):
        return self.clf.score(self.__test_M(), self.__test_y())

    def roc_curve(self):
        from ..communicate import plot_roc
        return plot_roc(self.__test_y(), self.__pred_proba(), verbose=False)

    def prec_recall_curve(self):
        from ..communicate import plot_prec_recall
        return plot_prec_recall(self.__test_y(), self.__pred_proba(), 
                                verbose=False)
   
    def sorted_top_feat_importance(self, n):
        feat_imp = self.clf.feature_importances_
        ind = np.argpartition(feat_imp, -n)[-n:]
        top_cols = ind[np.argsort(feat_imp[ind])][::-1]
        top_vals = feat_imp[top_cols]
        return [top_cols, top_vals]

    def f1_score(self):
        return f1_score(self.__test_y(), self.__predict())

    def precision_at_thresholds(self, query_thresholds):
        """
        Parameters
        query_thresholds : float
            0 <= thresh <= 1
        """
        y_true = self.__test_y()
        y_score = self.__pred_proba()
        prec, _, thresh = precision_recall_curve(
                y_true, 
                y_score)

        # Adopted from Rayid's code
        precision_curve = prec[:-1]
        pct_above_per_thresh = []
        number_scored = len(y_score)
        for value in thresh:
            num_above_thresh = len(y_score[y_score>=value])
            pct_above_thresh = num_above_thresh / float(number_scored)
            pct_above_per_thresh.append(pct_above_thresh)
        pct_above_per_thresh = np.array(pct_above_per_thresh)
        # Add point at 0% above thresh, 1, precision
        pct_above_per_thresh = np.append(pct_above_per_thresh, 0)
        precision_curve = np.append(precision_curve, 1)

        # TODO something better than linear interpolation
        return np.interp(
                query_thresholds, 
                pct_above_per_thresh[::-1],
                precision_curve[::-1])

    def roc_auc(self):
        return roc_auc_score(self.__test_y(), self.__pred_proba())


# TODO other clfs
all_clf_params = sorted(
        list(
            frozenset(
                it.chain(
                    *[clf().get_params().keys() for clf in 
                      (AdaBoostClassifier,
                       RandomForestClassifier,
                       LogisticRegression,
                       DecisionTreeClassifier,
                       SVC,
                       DummyClassifier)]))))
                                        
all_clf_params_backindex = {param: i for i, param in enumerate(all_clf_params)}

all_subset_params = sorted(['subset_size', 'n_subsets', 'num_rows', 
                            'proportions_positive', 'cols_to_exclude'])

all_subset_params_backindex = {param: i for i, param in 
                               enumerate(all_subset_params)}

# TODO others?
all_cv_params = sorted(['n_folds', 'indices', 'shuffle', 'random_state',
                        'train_start', 'train_window_size',
                        'test_start', 'test_window_size', 
                        'inc_value', 'expanding_train', 'col_name',
                        'col_idx'])
                        
all_cv_params_backindex = {param: i for i, param in 
                           enumerate(all_cv_params)}

class Trial(object):
    def __init__(
        self, 
        M,
        y,
        clf=RandomForestClassifier,
        clf_params={},
        subset=SubsetNoSubset,
        subset_params={},
        cv=NoCV,
        cv_params={}):
        self.M = M
        self.y = y
        self.runs = None
        self.clf = clf
        self.clf_params = clf_params
        self.subset = subset
        self.subset_params = subset_params
        self.cv = cv
        self.cv_params = cv_params
        self.__by_dimension = {CLF: self.clf,
                               CLF_PARAMS: self.clf_params,
                               SUBSET: self.subset,
                               SUBSET_PARAMS: self.subset_params,
                               CV: self.cv,
                               CV_PARAMS: self.cv_params}
        self.__cached_ave_score = None
        self.repr = ('Trial(clf={}, clf_params={}, subset={}, '
                     'subset_params={}, cv={}, cv_params={})').format(
                        self.clf,
                        self.clf_params,
                        self.subset,
                        self.subset_params,
                        self.cv,
                        self.cv_params)
        self.hash = hash(self.repr)


    def __hash__(self):
        return self.hash

    def __repr__(self):
        return self.repr
    def __getitem__(self, arg):
        return self.__by_dimension[arg]

    def has_run(self):
        return self.runs is not None

    def run(self):
        if self.has_run():
            return self.runs
        runs = []
        for subset, subset_note in self.subset(self.y, **self.subset_params):
            runs_this_subset = []
            y_sub = self.y[subset]
            M_sub = self.M[subset]
            cv_cls = self.cv
            cv_kwargs = copy.deepcopy(self.cv_params)
            expected_cv_kwargs = inspect.getargspec(cv_cls.__init__).args
            if 'n' in expected_cv_kwargs:
                cv_kwargs['n'] = y_sub.shape[0]
            if 'y' in expected_cv_kwargs:
                cv_kwargs['y'] = y_sub
            if 'M' in expected_cv_kwargs:
                cv_kwargs['M'] = M_sub
            cv_inst = cv_cls(**cv_kwargs)
            for fold_idx, (train, test) in enumerate(cv_inst):
                if hasattr(cv_inst, 'cv_note'):
                    cv_note = cv_inst.cv_note()
                else:
                    cv_note = {'fold': fold_idx}
                clf_inst = self.clf(**self.clf_params)
                clf_inst.fit(M_sub[train], y_sub[train])
                test_indices = subset[test]
                train_indices = subset[train]
                runs_this_subset.append(Run(self.M, self.y, clf_inst, 
                                            train_indices, test_indices,
                                            subset_note, cv_note))
            runs.append(runs_this_subset)    
        self.runs = runs
        return self

    @staticmethod
    def csv_header():
        return (['clf'] + ['clf_' + name for name in all_clf_params] +  
                ['subset'] + ['subset_' + name for name in all_subset_params] +
                ['cv'] + ['cv_' + name for name in all_cv_params] +
                Run.csv_header())

    def __clf_param_list(self):
        param_vals = [''] * len(all_clf_params)
        for name, val in self.clf_params.iteritems():
            param_vals[all_clf_params_backindex[name]] = str(val)
        return param_vals

    def __subset_param_list(self):
        param_vals = [''] * len(all_subset_params)
        for name, val in self.subset_params.iteritems():
            param_vals[all_subset_params_backindex[name]] = str(val)
        return param_vals

    def __cv_param_list(self):
        param_vals = [''] * len(all_cv_params)
        for name, val in self.cv_params.iteritems():
            param_vals[all_cv_params_backindex[name]] = str(val)
        return param_vals

    def csv_rows(self):
        return [[str(self.clf)] + self.__clf_param_list() + 
                [str(self.subset)] + self.__subset_param_list() + 
                [str(self.cv)] + self.__cv_param_list() + 
                 run.csv_row() for run in self.runs_flattened()]

    def average_score(self):
        if self.__cached_ave_score is not None:
            return self.__cached_ave_score
        self.run()
        M = self.M
        y = self.y
        ave_score = np.mean([run.score() for run in self.runs_flattened()])
        self.__cached_ave_score = ave_score
        return ave_score
    
    def median_run(self):
        # Give or take
        #runs_with_score = [(run.score(), run) for run in self.runs]
        runs_with_score = [(run.score(), run) for run in it.chain(*self.runs)]
        runs_with_score.sort(key=lambda t: t[0])
        return runs_with_score[len(runs_with_score) / 2][1]

    def runs_flattened(self):
        return [run for run in it.chain(*self.runs)]

    # TODO These should all be average across runs rather than picking the 
    # median

    def roc_curve(self):
        return self.median_run().roc_curve()

    def roc_auc(self):
        return self.median_run().roc_auc()

    def prec_recall_curve(self):
        return self.median_run().prec_recall_curve()
