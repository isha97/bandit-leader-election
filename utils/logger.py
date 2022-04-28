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

    def plot(self, fname):
        fig, ax = plt.subplots()
        ax.scatter(self.data[:, 0] - self.start_stamp, self.data[:, 1], marker='|', s=200)
        ax.set_title("Leader Elections")
        ax.set_xlabel('Time')
        fig.tight_layout()
        fig.savefig('{}.png'.format(fname))
        compress_pickle(fname, self.data)


class FailureEstimatesLogger():
    def __init__(self, stamp, failure_estimates) -> None:
        self.start_stamp = stamp
        self.data_stamp = np.array([stamp])
        self.data = np.array([failure_estimates])

    def tick(self, stamp, failure_estimates):
        self.data_stamp = np.concatenate([self.data_stamp, np.array([stamp])])
        self.data = np.concatenate([self.data, np.array([failure_estimates])])

    def plot(self, fname):
        fig, ax = plt.subplots(dpi=200)

        clrs = sns.color_palette("husl", self.data.shape[-1])
        for idx, val in enumerate(range(self.data.shape[-1])):
            ax.plot(self.data_stamp - self.start_stamp, self.data[:, idx], c=clrs[idx], label='FailEst Node {}'.format(idx))
            # ax.hlines(val, xmin=0, xmax=self.data_stamp[-1] - self.start_stamp, linestyles='dashed', color=clrs[idx], linewidth=1, label='True Fail Node {}'.format(idx))

        ax.legend()
        ax.set_title("Failure Estimates")
        ax.set_xlabel('Time')
        fig.tight_layout()
        fig.savefig('{}.png'.format(fname))
        compress_pickle(fname, [self.data_stamp, self.data])