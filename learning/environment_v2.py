import numpy as np
import time
from _thread import *
import threading
from sklearn.model_selection import train_test_split
import logging
import socket
from .message import *
from .environment import Environment

lock = threading.Lock()

class Environmentv2(Environment):
    def __init__(self, n, config):
        """Initialize environment

            n: total number of nodes
            fail_nodes_update: Sleep time between updating failure probability
            nodes: List of node objects
            config: config parameters
        """
        super().__init__(n, config=config)
        self.run = False
        self.machine_dist = config.cluster_configuration.num_nodes
        self.machine_dist/=(np.sum(self.machine_dist))
        self.base_failure_prob = config.cluster_configuration.base
        print("base_failure_prob", self.base_failure_prob)
        self.scaling_constant = config.cluster_configuration.scaling_constant

        self.machine_ids = np.arange(self.total_nodes)
        self.machine_types = np.argmax(np.random.multinomial(1, self.machine_dist, size=self.total_nodes), axis=-1)
        self.machine_status = np.array([1 for _ in range(self.total_nodes)]) # 0 is dead, 1 is alive
        self.repair_time_mean = config.cluster_configuration.repair_time_mean
        self.repair_time_sigma = config.cluster_configuration.repair_time_stdev
        self.repair_scale_factor = config.cluster_configuration.scaling_repair_time_constant
        print(self.machine_types)

        self.set_probability()

    def sleep_for_repair(self, node_id):
        repair_duration = np.random.lognormal(self.repair_time_mean, self.repair_time_sigma) # sample from repair_distribution
        repair_duration *= self.repair_scale_factor
        logging.info("Failing node {} for {} secs.".format(node_id, repair_duration))
        time.sleep(repair_duration)
        lock.acquire()
        self.machine_status[node_id] = 1
        lock.release()


    def set_probability(self):
        """Set failure probability of each node"""
        for i in range(self.total_nodes):
            self.failure_probability[i] = self.base_failure_prob[self.machine_types[i]]*self.scaling_constant
        logging.info("Initial failure probability {}".format(
            np.array2string(self.failure_probability)
            ))


    def fail_nodes(self):
        """Fail up to f nodes"""
        while self.run:
            # Sample from binomial dist. (p = node failure prob.)
            alive_nodes = np.where(self.machine_status == 1) # returns indices of all alive nodes
            indices = []

            # we should fail atleast some nodes
            while len(indices) + (self.total_nodes - np.sum(self.machine_status)) < self.min_fail_fraction*self.max_failed_nodes:

                # Decide to fail or not
                for idx, val in enumerate(self.failure_probability):
                    # select a new node (hasn't been selected before) which is alive
                    if idx not in indices and self.machine_status[idx] == 1 and np.random.binomial(1, val) == 1:
                        indices.append(idx)

            # Random sample to limit nodes failed to self.max_failed_nodes
            if len(indices) + (self.total_nodes - np.sum(self.machine_status)) > self.max_failed_nodes:
                indices = np.random.choice(
                    indices,
                    self.max_failed_nodes - (self.total_nodes - np.sum(self.machine_status)),
                    replace=False
                )

            # send the failure values to the respective nodes
            logging.info("failed nodes {}".format(indices))
            host = '127.0.0.1'
            for port in self.ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    if port - self.replica_base_port in indices:
                        node_id = port - self.replica_base_port
                        failVal = "True"
                        self.machine_status[node_id] = 0
                        # thread to sleep for repair period and then change machine_status to alive
                        start_new_thread(self.sleep_for_repair, (node_id, ))
                    else:
                        failVal = "True" if self.machine_status[port - self.replica_base_port] == 0 else "False"
                    message = str(FailureMessage(-2, 0, time.time()*100, failVal))
                    s.connect((host, port))
                    s.send(message.encode('ascii'))
                    s.close()
                except Exception as msg:
                    logging.error(str(msg) + " while connecting to {}".format(port))
                    s.close()
            time.sleep(self.fail_nodes_update)
