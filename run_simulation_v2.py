import argparse
import sys
import yaml
from easydict import EasyDict

import os.path as osp
from os import listdir
from os.path import isfile, join

import threading
import time

from learning.environment import Environment
#from learning.node import Node
from learning.v2 import v2 as Node

global nodes, message_buffer

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Simulate Leader Election')
    parser.add_argument(
        '-c',
        '--config',
        help='Path to config file'
        )
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)
    config = EasyDict(config)

    if len(sys.argv) < 3:
        print("Usage : <env|node_id>")
        exit(1)

    type = sys.argv[2]
    if type == 'env':
        env = Environment(config.num_nodes, config.sleep_sec, config)
        env.run_threads()
        time.sleep(500)
        env.stop_threads()

    if type.startswith('node'):
        node_id = type.split("_")[1]
        node = Node(node_id, config.num_nodes, config)
        node.run_node()
        time.sleep(500)
        node.stop_node()
