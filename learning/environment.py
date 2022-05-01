import numpy as np
import time
import threading
from sklearn.model_selection import train_test_split
import logging
import socket
from .message import *

lock = threading.Lock()

class Environment:
    def __init__(self, n, config):
        """Initialize environment

            n: total number of nodes
            fail_nodes_update: Sleep time between updating failure probability
            nodes: List of node objects
            config: config parameters
        """
        self.total_nodes = n
        self.failure_probability = np.zeros(n)
        self.max_failed_nodes = int((n - 1)/2)
        self.fail_nodes_update = config.fail_nodes_update
        self.failure_update = config.failure_update
        self.stationary = config.stationary
        self.init_prob = config.fail_prob.init
        self.update_prob = config.fail_prob.update
        self.min_fail_fraction = config.min_fail_fraction
        self.replica_base_port = config.port.replica_base_port

        self.run = False
        self.ports = [int(self.replica_base_port) + i for i in range(n)]

        logging.basicConfig(level=logging.INFO,
            format='[%(asctime)s %(levelname)-8s [ENV] %(funcName)s() %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                logging.FileHandler("logs/env_{}_{}.log".format(self.total_nodes, config.mab.algo)),
                logging.StreamHandler()
                ]
        )


    def set_probability(self):
        """Set failure probability of each node"""
        self.failure_probability = np.random.normal(
            self.init_prob.mean,
            self.init_prob.std,
            self.total_nodes
        )
        self.failure_probability = abs(self.failure_probability)
        self.failure_probability[1] = 0.6
        logging.info("Initial failure probability {}".format(
            np.array2string(self.failure_probability)
            ))


    def fail_nodes(self):
        """Fail up to f nodes"""
        while self.run:
            # Sample from binomial dist. (p = node failure prob.)
            indices = []
            while len(indices) < self.min_fail_fraction*self.max_failed_nodes:
                for idx, val in enumerate(self.failure_probability):
                    if idx not in indices and np.random.binomial(1, val) == 1:
                        indices.append(idx)
            # Random sample to limit nodes failed to self.max_failed_nodes
            if len(indices) > self.max_failed_nodes:
                indices = np.random.choice(
                    indices,
                    self.max_failed_nodes,
                    replace=False
                )

            # send the failure values to the respective nodes
            logging.info("failed nodes {}".format(indices))
            host = '127.0.0.1'
            for port in self.ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    if port - self.replica_base_port in indices:
                        failVal = "True"
                    else:
                        failVal = "False"
                    message = str(FailureMessage(-2, 0, time.time()*100, failVal))
                    s.connect((host, port))
                    s.send(message.encode('ascii'))
                    s.close()
                except Exception as msg:
                    logging.error(str(msg) + " while connecting to {}".format(port))
                    s.close()
            time.sleep(self.fail_nodes_update)


    def update_probability(self):
        """Update failure probability in case of non-stationary failure prob"""
        if not self.stationary:
            while self.run:
                # Sample nodes to increase and decrease
                increase, decrease = train_test_split(
                                        np.arange(self.total_nodes),
                                        test_size=self.update_prob.inc_split
                                    )

                # Decrease
                self.failure_probability[decrease] -= abs(np.random.normal(
                                        self.update_prob.mean,
                                        self.update_prob.std,
                                        len(decrease)))
                self.failure_probability[decrease] = np.maximum(
                                                [0]*len(decrease),
                                                self.failure_probability[decrease]
                                                )

                # Increase
                self.failure_probability[increase] += abs(np.random.normal(
                                        self.update_prob.mean,
                                        self.update_prob.std,
                                        len(increase)))
                self.failure_probability[increase] = np.minimum(
                                                [1]*len(increase),
                                                self.failure_probability[increase]
                                                )

                time.sleep(self.failure_update)
        else:
            # Do not change failure prob in stationary case
            pass


    def run_threads(self):
        """Run threads to fail_nodes and update_probability"""
        self.run = True
        generate_failure = threading.Thread(target=self.fail_nodes)
        generate_failure.start()
        update_failure_probability = threading.Thread(target=self.update_probability)
        update_failure_probability.start()


    def stop_threads(self):
        """Terminate threads"""
        self.run = False
