import csv
import urllib2

import numpy as np
import sklearn.datasets

from eights.investigate import (cast_np_nd_to_sa, describe_cols,)
from eights.communicate import (plot_correlation_scatter_plot,
                               plot_correlation_matrix, 
                               plot_kernel_density,
                               plot_box_plot)




url = 'http://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-white.csv'
response = urllib2.urlopen(url)
cr = csv.reader(response, delimiter=';')

data = list(cr)
col_names = data[0]
labels = np.array([int(x[-1]) for x in data[1:]])
#make this problem binary
av = np.average(labels)
labels = np.array([0 if x < av else 1 for x in labels])




nd = np.array([[1, 2, 3], [4, 5, 6]], dtype=int)
dtype2 = np.dtype({'names': map('f{}'.format, xrange(3)), 'formats': [int] * 3})
control = np.array([(1, 2, 3), (4, 5, 6)], dtype=dtype2)
result = cast_np_nd_to_sa(nd, dtype2)

dtype = np.dtype({'names':  col_names,'formats': [float] * len(col_names)})
tmp = np.array([x[:-1] for x in data[1:]],dtype='float')
M = cast_np_nd_to_sa(tmp, dtype)
import pdb; pdb.set_trace()



import pdb; pdb.set_trace()

if False:
    for x in describe_cols(M):
        print x

if False:
   plot_correlation_scatter_plot(M) 
   plot_correlation_matrix(M)
   plot_kernel_density(M['f0']) #no designation of col name
   plot_box_plot(M['f0']) #no designation of col name

from eights.operate import run_std_classifiers, run_alt_classifiers #run_alt_classifiers not working yet
exp = run_std_classifiers(M,labels)
exp.make_csv()
import pdb; pdb.set_trace()