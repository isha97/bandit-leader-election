import argparse
from turtle import clear
import numpy as np
import matplotlib
# switch to pgf backend
matplotlib.use('pgf')
# import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from os.path import join
import numpy as np

import bz2
import pickle
import _pickle as cPickle
import glob

plt.rcParams['xtick.direction'] = 'out'
plt.rcParams['ytick.direction'] = 'out'
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
plt.rc('axes', titlesize=BIGGER_SIZE)

plt.rcParams.update({
    "text.usetex": True,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica"]
})
matplotlib.rcParams['hatch.color'] = 'white'


def decompress_pickle(file):
    data = bz2.BZ2File(file, 'rb')
    data = cPickle.load(data)
    return data


def plot_leader_elections(path, nodes_cnt, fmt='png'):
    data = decompress_pickle(path)
    client_log = decompress_pickle(join(args.path, 'leader_log.pbz2'))
    failed_election_idxs = np.where(client_log[:, -1] == 1)[0]

    fig, ax = plt.subplots(dpi=200)
    ax.scatter(data[:, 0] - data[0, 0], data[:, 1], marker='o', s=50, c='Green', label='Successful LE Round')
    ax.scatter(client_log[failed_election_idxs, 0] - client_log[0, 0], client_log[failed_election_idxs, 1], marker='*', s=40, c='Red', label='Unsuccessful LE Round')

    # ax.set_title("Leader Elections")
    ax.set_xlabel('Time')
    ax.set_ylabel('Node ID')
    ax.set_yticks(np.arange(nodes_cnt))
    ax.set_yticklabels(np.arange(nodes_cnt)+1)
    fig.tight_layout()
    ax.legend()
    fig.savefig(join(args.path, 'client_le.{}'.format(fmt)), format=fmt)


def plot_fail_est(path, node_id, true_vals=None, fmt='png'):
    data_stamp, data = decompress_pickle(path)
    fig, ax = plt.subplots(dpi=200)
    clrs = sns.color_palette("husl", data.shape[-1])
    for idx, val in enumerate(range(data.shape[-1])):
        ax.plot(np.arange(data.shape[0]), data[:, idx], label='Node {}'.format(idx), c=clrs[idx])
        if true_vals is not None:
            ax.hlines(true_vals[idx]+np.random.normal(0.05, 0.05), xmin=0, xmax=data.shape[0], linestyles='dashed', linewidth=1, color=clrs[idx])
    ax.legend()
    ax.set_title("Failure Estimates (Node {})".format(node_id))
    ax.set_xlabel('Time')
    ax.set_ylabel(r'$p(f_i)$')
    fig.tight_layout()
    fig.savefig(join(args.path, 'fest_{}.{}'.format(node_id, fmt)), format=fmt)


def plot_comparative_le(files, labels, fmt='png'):
    data, client_log, failed_election_idxs = {}, {}, {}
    for idx, f in enumerate(files):
        data[labels[idx]] = decompress_pickle(join(f, "client_view_changes.pbz2"))
        client_log[labels[idx]] = decompress_pickle(join(f, 'leader_log.pbz2'))
        failed_election_idxs[labels[idx]] = np.where(client_log[labels[idx]][:, -1] == 1)[0]

    # Histogram plotting the frequency of delay between failure and electing a
    # successful leader
    fig, ax = plt.subplots(dpi=200)
    for idx, key in enumerate(labels):
        arr = []
        for i in range(client_log[key].shape[0]-1):
            if client_log[key][i, -1] == 1:
                cnt = 0
                for j in range(i+1, client_log[key].shape[0]-1):
                    if client_log[key][j, -1] == 0:
                        break
                    elif client_log[key][j, -1] == 1:
                        cnt += 1
                arr.append(cnt)
        arr = np.bincount(arr)
        if key == 'Randomized' or key == 'Deterministic':
            ax.bar(np.arange(1, len(arr)+1) + (idx*0.2), arr, 0.2, label=key)
        else:
            ax.bar(np.arange(1, len(arr)+1) + (idx*0.2), arr, 0.2, label=key, hatch='///')
    ax.set_xlabel('Unit Delay')
    ax.set_ylabel('Frequency')
    ax.legend()
    fig.tight_layout()
    fig.savefig(join(args.path, 'le_delay_le.{}'.format(fmt)), format=fmt)

    # Sliding window to plot frequency of successful leader election rounds
    import skimage

    fig, ax = plt.subplots(dpi=200)
    for idx, key in enumerate(labels):
        a = np.zeros((int(data[key][-1, 0] - data[key][0, 0] + 1)))
        a[np.int64(data[key][:, 0] - data[key][0, 0])] = 1
        b = np.sum(skimage.util.view_as_windows(a, 100000, step=10000), axis=-1)

        # ax.scatter(np.arange(b.shape[0]), b, marker='x', alpha=0.2)
        p = np.polyfit(np.arange(b.shape[0]), b, 1)
        # plt.annotate('$c = {:.2f}$'.format(p[0]), xy=(0.9, 0.9), xycoords='axes fraction', fontsize=SMALL_SIZE)
        if key == 'Randomized' or key == 'Deterministic':
            plt.plot(np.arange(b.shape[0]), np.poly1d(p)(np.arange(b.shape[0])), '--', label=key)
        else:
            plt.plot(np.arange(b.shape[0]), np.poly1d(p)(np.arange(b.shape[0])), '-', label=key)

    ax.set_ylabel(r'\# LE rounds')
    ax.set_xlabel('Window Step')
    ax.set_yticks(np.arange(12))
    ax.set_yticklabels(np.arange(12))
    ax.legend()
    fig.tight_layout()
    fig.savefig(join(args.path, 'window_le.{}'.format(fmt)), format=fmt)

    fig, ax = plt.subplots(dpi=200)
    for idx, key in enumerate(labels):
        # Sliding window to plot frequency of unsuccessful leader election rounds
        a = np.zeros((int(client_log[key][-1, 0] - client_log[key][0, 0] + 1)))
        a[np.int64(client_log[key][failed_election_idxs[key], 0] - client_log[key][0, 0])] = 1
        b = np.sum(skimage.util.view_as_windows(a, 500000, step=100000), axis=-1)

        # ax.scatter(np.arange(b.shape[0]), b, marker='x', label=key)
        p = np.polyfit(np.arange(b.shape[0]), b, 1)
        # plt.annotate('$c = {:.2f}$'.format(p[0]), xy=(0.9, 0.9), xycoords='axes fraction', fontsize = 14)
        if key == 'Randomized' or key == 'Deterministic':
            plt.plot(np.arange(b.shape[0]), np.poly1d(p)(np.arange(b.shape[0])), '--', label=key)
        else:
            plt.plot(np.arange(b.shape[0]), np.poly1d(p)(np.arange(b.shape[0])), '-', label=key)

    ax.set_ylabel(r'\# Failed LE rounds')
    ax.set_xlabel('Window Step')
    ax.set_yticks(np.arange(20))
    ax.set_yticklabels(np.arange(20))
    fig.tight_layout()
    ax.legend()
    fig.savefig(join(args.path, 'failed_window_le.{}'.format(fmt)), format=fmt)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Plot Leader Election')
    parser.add_argument(
        '-p',
        '--path',
        help='Path to experiment dir',
        required=True
        )
    parser.add_argument(
        '-l',
        '--le',
        help='plot LE plots',
        default=False,
        required=False
        )
    parser.add_argument(
        '-b',
        '--bandit',
        help='plot bandit plots',
        default=False,
        required=False
        )
    parser.add_argument(
        '-f',
        '--fmt',
        help='plot format',
        default='png',
        required=False
        )
    args = parser.parse_args()

    if args.bandit:
        # Enter true probs before running

        true_vals = [0.95, 0.15, 0.15, 0.95, 0.7]
        # true_vals = [0.95, 0.15, 0.15, 0.7,  0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15]

        print("Using True Failure Probs: {}".format(true_vals))

        files = glob.glob(join(args.path, "failEst_*.pbz2"))
        for f in files:
            node_id = f.split('/')[-1].split('_')[1].split('.')[0]
            plot_fail_est(f, node_id, true_vals, fmt=args.fmt)

    if args.le:

        # plot_leader_elections(join(args.path, "client_view_changes.pbz2"), len(true_vals), fmt=args.fmt)

        EXPS = ['../rand_5000_11', '../det_5000_11', '../11_egreedy_5000_2', '../ucb_5000_11']
        LABELS = ['Randomized', 'Deterministic', 'EGreedy', 'UCB']
        plot_comparative_le(EXPS, LABELS, fmt=args.fmt)