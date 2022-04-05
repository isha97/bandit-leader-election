import argparse
import yaml
from easydict import EasyDict

import os.path as osp
from os import listdir
from os.path import isfile, join

import threading
import time

from learning.environment import Environment
#from learning.node import Node
from learning.v1 import v1 as Node

global nodes, message_buffer


def run_nodes(config, message_buffer):
    """Run nodes for config.step steps.

        config: config parameters
        message_buffer: shared message buffer
    """
    step = 0
    while step < config.steps:
        # Read messages that all nodes want to send out
        for i in range(len(nodes)):
            message_buffer = nodes[i].send(message_buffer)

        # Send out messages to all nodes
        for i in range(len(nodes)):
            message_buffer[i] = nodes[i].recieve(message_buffer[i], step)
        step += 1
        time.sleep(config.node_sleep)

    for i in range(len(nodes)):
        print(nodes[i].failure_estimates)

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

    # Initialize global variables: Nodes and message buffer
    nodes = [Node(i, config.num_nodes, config) for i in range(config.num_nodes)]

    # NOTE: Message buffer: key = idx of receiver, value = message
    message_buffer = {i: [] for i in range(config.num_nodes)}

    # Initialize the environment and run
    env = Environment(config.num_nodes, config.sleep_sec, nodes, config)
    print(env.failure_probability)
    env.run_threads()

    # Run nodes
    simulate_nodes = threading.Thread(
        target=run_nodes,
        args=(config,message_buffer,)
    )
    simulate_nodes.start()
