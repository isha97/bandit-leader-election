import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import time
import numpy as np
from logger import ViewChangeLogger, FailureEstimatesLogger

import bz2
import pickle
import _pickle as cPickle
import glob


def compress_pickle(fname, data):
    with bz2.BZ2File(fname + '.pbz2', 'wb') as f: 
        cPickle.dump(data, f)


def decompress_pickle(file):
    data = bz2.BZ2File(file, 'rb')
    data = cPickle.load(data)
    return data


def test():
    logger = ViewChangeLogger(time.time()*100, 10)
    i = 0
    while i < 10:
        time.sleep(np.random.randint(1, 4))
        logger.tick(time.time()*100, np.random.randint(0, 10))
        print(i)
        i += 1
    logger.plot('save.png')

    prev = np.random.rand(4)
    logger = FailureEstimatesLogger(time.time()*100, prev, [0.9, 0.4, 0.2, 0.1])
    i = 0
    while i < 10:
        time.sleep(np.random.randint(1, 4))
        prev += 0.1*np.random.rand(4)
        logger.tick(time.time()*100, prev)
        print(i)
        i += 1
    logger.plot('save_est.png')


def plot_leader_elections(path):
    data = decompress_pickle(path)
    fig, ax = plt.subplots(dpi=200)
    ax.scatter(data[:, 0] - data[0, 0], data[:, 1], marker='|', s=200)
    ax.set_title("Leader Elections")
    ax.set_xlabel('Time')
    fig.tight_layout()
    fig.savefig('client_le.png')


def plot_fail_est(path, node_id, true_vals=None):
    data_stamp, data = decompress_pickle(path)
    fig, ax = plt.subplots(dpi=200)
    clrs = sns.color_palette("husl", data.shape[-1])
    for idx, val in enumerate(range(data.shape[-1])):
        ax.plot(data_stamp - data_stamp[0], data[:, idx], c=clrs[idx], label='FailEst Node {}'.format(idx))
        if true_vals is not None:
            ax.hlines(true_vals[idx], xmin=0, xmax=data_stamp[-1] - data_stamp[0], linestyles='dashed', color=clrs[idx], linewidth=1)#, label='True Fail Node {}'.format(idx))
    ax.legend()
    ax.set_title("Failure Estimates (Node {})".format(node_id))
    ax.set_xlabel('Time')
    fig.tight_layout()
    fig.savefig('fest_{}.png'.format(node_id))


if __name__=='__main__':
    # Enter true probs before running
    true_vals = [0.95, 0.15, 0.7, 0.15, 0.8]
    print("True Failure Probs: {}".format(true_vals))

    try:
        env_file = glob.glob("../env_fails.pbz2")
        data_stamp, data, true_vals = decompress_pickle(env_file)
    except:
        print('Could not find env file')

    files = glob.glob("../FailEst_node_*.pbz2")
    for f in files:
        node_id = f.split('.')[-2][-1]
        plot_fail_est(f, node_id, true_vals)

    plot_leader_elections("../client_view_changes.pbz2")