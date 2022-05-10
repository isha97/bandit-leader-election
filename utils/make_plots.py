import argparse
import numpy as np
import matplotlib
# switch to pgf backend
matplotlib.use('pgf')
# import matplotlib
import matplotlib.pyplot as plt

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


def decompress_pickle(file):
    data = bz2.BZ2File(file, 'rb')
    data = cPickle.load(data)
    return data


def plot_leader_elections(path, fmt='png'):
    data = decompress_pickle(path)
    data1 = decompress_pickle(join(args.path, 'leader_log.pbz2'))
    failed_election_idxs = np.where(data1[:, -1] == 1)[0]

    fig, ax = plt.subplots(dpi=200)
    ax.scatter(data[:, 0] - data[0, 0], data[:, 1], marker='o', s=50, c='Green')
    ax.scatter(data1[failed_election_idxs, 0] - data1[0, 0], data1[failed_election_idxs, 1], marker='*', s=50, c='Red')

    # for fail_idx in failed_election_idxs:
    #     plt.axvspan(a, b, color='y', alpha=0.5, lw=0)

    # ax.set_title("Leader Elections")
    ax.set_xlabel('Time')
    ax.set_ylabel('Node ID')
    ax.set_yticks(np.arange(23))
    ax.set_yticklabels(np.arange(23)+1)
    fig.tight_layout()
    fig.savefig(join(args.path, 'client_le.{}'.format(fmt)), format=fmt)


def plot_fail_est(path, node_id, true_vals=None, fmt='png'):
    data_stamp, data = decompress_pickle(path)
    fig, ax = plt.subplots(dpi=200)
    for idx, val in enumerate(range(data.shape[-1])):
        ax.plot(np.arange(data.shape[0]), data[:, idx], label='Node {}'.format(idx))
        if true_vals is not None:
            ax.hlines(true_vals[idx], xmin=0, xmax=data.shape[0], linestyles='dashed', linewidth=1)
    ax.legend()
    ax.set_title("Failure Estimates (Node {})".format(node_id))
    ax.set_xlabel('Time')
    ax.set_ylabel(r'$\displaystylep(f_i)')
    fig.tight_layout()
    fig.savefig(join(args.path, 'fest_{}.{}'.format(node_id, fmt)), format=fmt)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Plot Leader Election')
    parser.add_argument(
        '-p',
        '--path',
        help='Path to experiment dir'
        )
    args = parser.parse_args()

    # Enter true probs before running
    true_vals = [0.15, 0.7, 0.15, 0.95, 0.7]
    # true_vals = [0.95, 0.15, 0.15, 0.7,  0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15]

    print("Using True Failure Probs: {}".format(true_vals))

    try:
        env_file = glob.glob(join(args.path, "env_fails.pbz2"))
        data_stamp, data, true_vals = decompress_pickle(env_file)
    except:
        print('Could not find env file!')

    # files = glob.glob(join(args.path, "failEst_*.pbz2"))
    # for f in files:
    #     node_id = f.split('/')[-1].split('_')[1].split('.')[0]
    #     plot_fail_est(f, node_id, true_vals)

    plot_leader_elections(join(args.path, "client_view_changes.pbz2"))