import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import bz2
import pickle
import _pickle as cPickle

def compress_pickle(fname, data):
    with bz2.BZ2File(fname + '.pbz2', 'wb') as f: 
        cPickle.dump(data, f)


def decompress_pickle(file):
    data = bz2.BZ2File(file, 'rb')
    data = cPickle.load(data)
    return data


class ViewChangeLogger():
    def __init__(self, stamp, total_nodes) -> None:
        self.start_stamp = stamp
        self.total_nodes = total_nodes
        self.data = np.array([[self.start_stamp, 0]])

    def tick(self, stamp, value):
        self.data = np.concatenate([self.data, np.array([[stamp, value]])])

    def save(self, fname):
        compress_pickle(fname, self.data)


class FailureLogger():
    def __init__(self, stamp, total_nodes, true_probs) -> None:
        self.start_stamp = stamp
        self.total_nodes = total_nodes
        self.data_stamp = np.array([self.start_stamp])
        self.data = np.array([[0]*total_nodes])
        self.true = true_probs

    def tick(self, stamp, value):
        self.data_stamp = np.concatenate([self.data_stamp, np.array([stamp])])
        self.data = np.concatenate([self.data, np.array([value])])

    def save(self, fname):
        compress_pickle(fname, [self.data_stamp, self.data, self.true_probs])


class FailureEstimatesLogger():
    def __init__(self, stamp, failure_estimates) -> None:
        self.start_stamp = stamp
        self.data_stamp = np.array([stamp])
        self.data = np.array([failure_estimates])

    def tick(self, stamp, failure_estimates):
        self.data_stamp = np.concatenate([self.data_stamp, np.array([stamp])])
        self.data = np.concatenate([self.data, np.array([failure_estimates])])

    def save(self, fname):
        """For now, we just save. Matplotlib is not thread-safe :("""
        compress_pickle(fname, [self.data_stamp, self.data])