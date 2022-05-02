import argparse
import yaml
from easydict import EasyDict

import time

# from learning.environment import Environment
from learning.environment_v2 import Environmentv2 as Environment
from learning.v2 import v2 as Node
from learning.client import Client

global nodes, message_buffer

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Simulate Leader Election')
    parser.add_argument(
        '-c',
        '--config',
        help='Path to config file'
        )
    parser.add_argument(
        '-t',
        '--type',
        help='<env|node_id|client>'
    )
    parser.add_argument(
        '-d',
        '--duration',
        type=int,
        default=500,
        help='Duration to keep env and nodes running'
    )
    parser.add_argument(
        '-e',
        '--exp_name',
        type=str,
        help='Name of experiment'
    )
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)
    config = EasyDict(config)

    type = args.type
    if type == 'env':
        env = Environment(config.num_nodes, config, args.exp_name)
        env.run_threads()
        # time.sleep(args.duration)
        # env.stop_threads()

    elif type.startswith('node'):
        node_id = type.split("_")[1]
        node = Node(int(node_id), config.num_nodes, config, args.exp_name)
        node.run_node()
        # time.sleep(args.duration)
        # node.stop_node()

    elif type == 'client':
        client = Client(-1, config.num_nodes, config, args.exp_name)
        client.run_node()
