import os
import shutil
import StringIO
import cgi
import uuid
import abc
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pylab import boxplot 


from sklearn.grid_search import GridSearchCV
from sklearn.neighbors.kde import KernelDensity
import pdfkit

from sklearn.metrics import roc_curve
from sklearn.metrics import precision_recall_curve
from ..perambulate import Experiment
from ..utils import is_sa, cast_np_sa_to_nd, convert_to_sa
from ..utils import cast_list_of_list_to_sa
from communicate_helper import *
from communicate_helper import _feature_pair_report


def print_matrix_row_col(M, row_labels=None, col_labels=None):
    M = convert_to_sa(M, col_names=col_labels)
    if row_labels is None:
        row_labels = xrange(M.shape[0])
    col_labels = M.dtype.names
    # From http://stackoverflow.com/questions/9535954/python-printing-lists-as-tabular-data
    row_format ="{:>15}" * (len(col_labels) + 1)
    print row_format.format("", *col_labels)
    for row_name, row in zip(row_labels, M):
        print row_format.format(row_name, *row)

def plot_simple_histogram(col, verbose=True):
    hist, bins = np.histogram(col, bins=50)
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:]) / 2
    f = plt.figure()
    plt.bar(center, hist, align='center', width=width)
    if verbose:
        plt.show()
    return f

# all of the below take output from any func in perambulate or operate


def plot_prec_recall(labels, score, title='Prec/Recall', verbose=True):
    # adapted from Rayid's prec/recall code
    y_true = labels
    y_score = score
    precision_curve, recall_curve, pr_thresholds = precision_recall_curve(
        y_true, 
        y_score)
    precision_curve = precision_curve[:-1]
    recall_curve = recall_curve[:-1]
    pct_above_per_thresh = []
    number_scored = len(y_score)
    for value in pr_thresholds:
        num_above_thresh = len(y_score[y_score>=value])
        pct_above_thresh = num_above_thresh / float(number_scored)
        pct_above_per_thresh.append(pct_above_thresh)
    pct_above_per_thresh = np.array(pct_above_per_thresh)
    fig = plt.figure()
    ax1 = plt.gca()
    ax1.plot(pct_above_per_thresh, precision_curve, 'b')
    ax1.set_xlabel('percent of population')
    ax1.set_ylabel('precision', color='b')
    ax2 = ax1.twinx()
    ax2.plot(pct_above_per_thresh, recall_curve, 'r')
    ax2.set_ylabel('recall', color='r')
    plt.title(title)
    if verbose:
        fig.show()
    return fig

def plot_roc(labels, score, title='ROC', verbose=True):
    # adapted from Rayid's prec/recall code
    fpr, tpr, thresholds = roc_curve(labels, score)
    fpr = fpr
    tpr = tpr
    pct_above_per_thresh = []
    number_scored = len(score)
    for value in thresholds:
        num_above_thresh = len(score[score>=value])
        pct_above_thresh = num_above_thresh / float(number_scored)
        pct_above_per_thresh.append(pct_above_thresh)
    pct_above_per_thresh = np.array(pct_above_per_thresh)

    fig = plt.figure()
    ax1 = plt.gca()
    ax1.plot(pct_above_per_thresh, fpr, 'b')
    ax1.set_xlabel('percent of population')
    ax1.set_ylabel('fpr', color='b')
    ax2 = ax1.twinx()
    ax2.plot(pct_above_per_thresh, tpr, 'r')
    ax2.set_ylabel('tpr', color='r')
    plt.title(title)
    if verbose:
        fig.show()
    return fig

def plot_box_plot(col, col_name=None, verbose=True):
    """Makes a box plot for a feature
    comment
    
    Parameters
    ----------
    col : np.array
    
    Returns
    -------
    matplotlib.figure.Figure
    
    """

    fig = plt.figure()
    boxplot(col)
    if col_name:
        plt.title(col_name)
    #add col_name to graphn
    if verbose:
        plt.show()
    return fig

def get_top_features(clf, M=None, col_names=None, n=10, verbose=True):
    scores = clf.feature_importances_
    if col_names is None:
        if is_sa(M):
            col_names = M.dtype.names
        else:
            col_names = ['f{}'.format(i) for i in xrange(len(scores))]
    ranked_name_and_score = [(col_names[x], scores[x]) for x in 
                             scores.argsort()[::-1]]
    ranked_name_and_score = ranked_name_and_score[:n]
    if verbose:
        print_matrix_row_col(ranked_name_and_score)
    return ranked_name_and_score


# TODO features form top % of clfs

def get_roc_auc(labels, score):
    raise NotImplementedError

def plot_correlation_matrix(M, verbose=True):
    """Plot correlation between variables in M
    
    Parameters
    ----------
    M : numpy structured array
    Returns
    -------
    matplotlib.figure.Figure
    
    """
    # http://glowingpython.blogspot.com/2012/10/visualizing-correlation-matrices.html
    # TODO work on structured arrays or not
    # TODO ticks are col names
    if is_sa(M):
        names = M.dtype.names
        M = cast_np_sa_to_nd(M)
    else: 
        if is_nd(M):
            n_cols = M.shape[1]
        else: # list of arrays
            n_cols = len(M)
        names = ['f{}'.format(i) for i in xrange(n_cols)]
    
    #set rowvar =0 for rows are items, cols are features
    cc = np.corrcoef(M, rowvar=0)
    
    fig = plt.figure()
    plt.pcolor(cc)
    plt.colorbar()
    plt.yticks(np.arange(0.5, M.shape[1] + 0.5), range(0, M.shape[1]))
    plt.xticks(np.arange(0.5, M.shape[1] + 0.5), range(0, M.shape[1]))
    if verbose:
        plt.show()
    return fig

def plot_correlation_scatter_plot(M, verbose=True):
    """Makes a grid of scatter plots representing relationship between variables
    
    Each scatter plot is one variable plotted against another variable
    
    Parameters
    ----------
    M : numpy structured array
    
    Returns
    -------
    matplotlib.figure.Figure
    
    """
    # TODO work for all three types that M might be
    # TODO ignore classification variables
    # adapted from the excellent 
    # http://stackoverflow.com/questions/7941207/is-there-a-function-to-make-scatterplot-matrices-in-matplotlib
    
    M = convert_to_sa(M)

    numdata = M.shape[0]
    numvars = len(M.dtype)
    names = M.dtype.names
    fig, axes = plt.subplots(numvars, numvars)
    fig.subplots_adjust(hspace=0.05, wspace=0.05)

    for ax in axes.flat:
        # Hide all ticks and labels
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)

        # Set up ticks only on one side for the "edge" subplots...
        if ax.is_first_col():
            ax.yaxis.set_ticks_position('left')
        if ax.is_last_col():
            ax.yaxis.set_ticks_position('right')
        if ax.is_first_row():
            ax.xaxis.set_ticks_position('top')
        if ax.is_last_row():
            ax.xaxis.set_ticks_position('bottom')

    # Plot the M.
    for i, j in zip(*np.triu_indices_from(axes, k=1)):
        for x, y in [(i,j), (j,i)]: 
            axes[x,y].plot(M[M.dtype.names[x]], M[M.dtype.names[y]], '.')

    # Label the diagonal subplots...
    for i, label in enumerate(names):
        axes[i,i].annotate(label, (0.5, 0.5), xycoords='axes fraction',
                ha='center', va='center')

    # Turn on the proper x or y axes ticks.
    for i, j in zip(range(numvars), it.cycle((-1, 0))):
        axes[j,i].xaxis.set_visible(True)
        axes[i,j].yaxis.set_visible(True)
    if verbose:
        plt.show()
    return fig

def plot_kernel_density(col, n=None, missing_val=np.nan, verbose=True): 
    #address pass entire matrix
    x_grid = np.linspace(min(col), max(col), 1000)

    grid = GridSearchCV(KernelDensity(), {'bandwidth': np.linspace(0.1,1.0,30)}, cv=20) # 20-fold cross-validation
    grid.fit(col[:, None])

    kde = grid.best_estimator_
    pdf = np.exp(kde.score_samples(x_grid[:, None]))

    fig, ax = plt.subplots()
    #fig = plt.figure()
    ax.plot(x_grid, pdf, linewidth=3, alpha=0.5, label='bw=%.2f' % kde.bandwidth)
    ax.hist(col, 30, fc='gray', histtype='stepfilled', alpha=0.3, normed=True)
    ax.legend(loc='upper left')
    ax.set_xlim(min(col), max(col))
    if verbose:
        plt.show()
    return fig

def plot_on_map(lat_col, lng_col):
    """Plots points on a map
    
    Parameters
    ----------
    lat_col : np.array
    lng_col : np.array
    
    Returns
    -------
    matplotlib.figure.Figure
    
    """
    raise NotImplementedError

def plot_on_timeline(col):
    """Plots points on a timeline
    
    Parameters
    ----------
    col : np.array
    
    Returns
    -------
    matplotlib.figure.Figure
    """
    raise NotImplementedError

def feature_pairs_in_rf(rf, weight_by_depth=None, verbose=True, n=10):
    """Describes the frequency of features appearing subsequently in each tree
    in a random forest"""
    # weight be depth is a vector. The 0th entry is the weight of being at
    # depth 0; the 1st entry is the weight of being at depth 1, etc.
    # If not provided, weights are linear with negative depth. If 
    # the provided vector is not as long as the number of depths, then 
    # remaining depths are weighted with 0
    # If verbose, will only print the first n results


    pairs_by_est = [feature_pairs_in_tree(est) for est in rf.estimators_]
    pairs_by_depth = [list(it.chain(*pair_list)) for pair_list in 
                      list(it.izip_longest(*pairs_by_est, fillvalue=[]))]
    pairs_flat = list(it.chain(*pairs_by_depth))
    depths_by_pair = {}
    for depth, pairs in enumerate(pairs_by_depth):
        for pair in pairs:
            try:
                depths_by_pair[pair] += [depth]
            except KeyError:
                depths_by_pair[pair] = [depth]
    counts_by_pair=Counter(pairs_flat)
    count_pairs_by_depth = [Counter(pairs) for pairs in pairs_by_depth]

    depth_len = len(pairs_by_depth)
    if weight_by_depth is None:
        weight_by_depth = [(depth_len - float(depth)) / depth_len for depth in
                           xrange(depth_len)]
    weight_filler = it.repeat(0.0, depth_len - len(weight_by_depth))
    weights = list(it.chain(weight_by_depth, weight_filler))
    
    average_depth_by_pair = {pair: float(sum(depths)) / len(depths) for 
                             pair, depths in depths_by_pair.iteritems()}

    weighted = {pair: sum([weights[depth] for depth in depths])
                for pair, depths in depths_by_pair.iteritems()}

    if verbose:
        print '=' * 80
        print 'RF Subsequent Pair Analysis'
        print '=' * 80
        print
        _feature_pair_report(
                counts_by_pair.most_common(), 
                'Overall Occurrences', 
                'occurrences',
                n=n)
        _feature_pair_report(
                sorted([item for item in average_depth_by_pair.iteritems()], 
                       key=lambda item: item[1]),
                'Average depth',
                'average depth',
                'Max depth was {}'.format(depth_len - 1),
                n=n)
        _feature_pair_report(
                sorted([item for item in weighted.iteritems()], 
                       key=lambda item: item[1]),
                'Occurrences weighted by depth',
                'sum weight',
                'Weights for depth 0, 1, 2, ... were: {}'.format(weights),
                n=n)

        for depth, pairs in enumerate(count_pairs_by_depth):
            _feature_pair_report(
                    pairs.most_common(), 
                    'Occurrences at depth {}'.format(depth), 
                    'occurrences',
                    n=n)


    return (counts_by_pair, count_pairs_by_depth, average_depth_by_pair, 
            weighted)

def html_escape(s):
    """Returns a string with all its html-averse characters html escaped"""
    return cgi.escape(s).encode('ascii', 'xmlcharrefreplace')

def html_format(fmt, *args, **kwargs):
    clean_args = [html_escape(str(arg)) for arg in args]
    clean_kwargs = {key: html_escape(str(kwargs[key])) for 
                    key in kwargs}
    return fmt.format(*clean_args, **clean_kwargs)

def np_to_html_table(sa, fout, show_shape=False):
    if show_shape:
        fout.write('<p>table of shape: ({},{})</p>'.format(
            len(sa),
            len(sa.dtype)))
    fout.write('<p><table>\n')
    header = '<tr>{}</tr>\n'.format(
        ''.join(
                [html_format(
                    '<th>{}</th>',
                    name) for 
                 name in sa.dtype.names]))
    fout.write(header)
    data = '\n'.join(
        ['<tr>{}</tr>'.format(
            ''.join(
                [html_format(
                    '<td>{}</td>',
                    cell) for
                 cell in row])) for
         row in sa])
    fout.write(data)
    fout.write('\n')
    fout.write('</table></p>')

class ReportError(Exception):
    pass

class Report(object):

    def __init__(self, exp=None, report_path='report.pdf'):
        self.__exp = exp
        if exp is not None:
            self.__back_indices = {trial: i for i, trial in enumerate(exp.trials)}
        self.__objects = []
        self.__tmp_folder = 'eights_temp'
        if not os.path.exists(self.__tmp_folder):
            os.mkdir(self.__tmp_folder)
        self.__html_src_path = os.path.join(self.__tmp_folder, 
                                            '{}.html'.format(uuid.uuid4()))
        self.__report_path = report_path

    def to_pdf(self):
        with open(self.__html_src_path, 'w') as html_out:
            html_out.write(self.__get_header())
            html_out.write('\n'.join(self.__objects))
            html_out.write(self.__get_footer())
        pdfkit.from_url(self.__html_src_path, self.__report_path)
        return self.get_report_path()

    def get_report_path(self):
        return os.path.abspath(self.__report_path)

    def __get_header(self):
        # Thanks to http://stackoverflow.com/questions/13516534/how-to-avoid-page-break-inside-table-row-for-wkhtmltopdf
        # For not page breaking in the middle of tables
        return ('<!DOCTYPE html>\n'
                '<html>\n'
                '<head>\n'
                '<style>\n'
                'table td, th {\n'
                '    border: 1px solid black;\n'
                '}\n'
                'table {\n'
                '    border-collapse: collapse;\n'
                '}\n'
                'tr:nth-child(even) {\n'
                '    background: #CCC\n'
                '}\n'
                'tr:nth-child(odd) {\n'
                '    background: white\n'
                '}\n'
                'table, tr, td, th, tbody, thead, tfoot {\n'
                '    page-break-inside: avoid !important;\n'
                '}\n' 
                '</style>\n'
                '</head>\n'
                '<body>\n')

    def add_subreport(self, subreport):    
        self.__objects += subreport.__objects

    def __get_footer(self):
        return '\n</body>\n</html>\n'

    def add_heading(self, heading, level=2):
        self.__objects.append(html_format(
            '<h{}>{}</h{}>',
            level,
            heading,
            level))

    def add_text(self, text):
         self.__objects.append(html_format(
                    '<p>{}</p>',
                    text))

    def add_table(self, M):
        sio = StringIO.StringIO()
        np_to_html_table(M, sio)
        self.__objects.append(sio.getvalue())

    def add_fig(self, fig):
        # So we don't get pages with nothing but one figure on them
        fig.set_figheight(5.0)
        filename = 'fig_{}.png'.format(str(uuid.uuid4()))
        path = os.path.join(self.__tmp_folder, filename)
        fig.savefig(path)
        self.__objects.append('<img src="{}">'.format(filename))

    def add_summary_graph(self, measure):
        if self.__exp is None:
            raise ReportError('No experiment provided for this report. '
                              'Cannot add summary graphs.')
        results = [(trial, score, self.__back_indices[trial]) for 
                   trial, score in getattr(self.__exp, measure)().iteritems()]
        results_sorted = sorted(
                results, 
                key=lambda result: result[1],
                reverse=True)
        y = [result[1] for result in results_sorted]
        x = xrange(len(results))
        fig = plt.figure()
        plt.bar(x, y)
        maxy = max(y)
        for rank, result in enumerate(results_sorted):
            plt.text(rank, result[1], '{}'.format(result[2]))
        plt.ylabel(measure)
        self.add_fig(fig)

    def add_summary_graph_roc_auc(self):
        self.add_summary_graph('roc_auc')

    def add_summary_graph_average_score(self):
        self.add_summary_graph('average_score')

    def add_graph_for_best(self, func_name):
        if self.__exp is None:
            raise ReportError('No experiment provided for this report. '
                              'Cannot add graph for best trial.')
        best_trial = max(
            self.__exp.trials, 
            key=lambda trial: trial.average_score())
        fig = getattr(best_trial, func_name)()
        self.add_fig(fig)
        self.add_text('Best trial is trial {} ({})]'.format(
            self.__back_indices[best_trial],
            best_trial))

    def add_graph_for_best_roc(self):
        self.add_graph_for_best('roc_curve')

    def add_graph_for_best_prec_recall(self):
        self.add_graph_for_best('prec_recall_curve')

    def add_legend(self):
        if self.__exp is None:
            raise ReportError('No experiment provided for this report. '
                              'Cannot add legend.')
        list_of_tuple = [(str(i), str(trial)) for i, trial in 
                         enumerate(self.__exp.trials)]
        table = cast_list_of_list_to_sa(list_of_tuple, col_names=('Id', 'Trial'))
        # display 10 at a time to give pdfkit an easier time with page breaks
        start_row = 0
        n_trials = len(list_of_tuple)
        while start_row < n_trials:
            self.add_table(table[start_row:start_row+9])
            start_row += 9 


