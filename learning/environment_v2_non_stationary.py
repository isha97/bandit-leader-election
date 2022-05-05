import numpy as np
from os.path import join
import time
from _thread import *
import threading
from numpy.random import default_rng
import logging
import socket
from .message import *
from utils.logger import FailureLogger, make_dirs
from .environment import Environment


lock = threading.Lock()

class Environmentv2(Environment):
    def __init__(self, n, config, exp_name):
        """Initialize environment

            n: total number of nodes
            fail_nodes_update: Sleep time between updating failure probability
            nodes: List of node objects
            config: config parameters
        """
        super().__init__(n, config, exp_name)
        self.seed = config.random_seed

        self.rng = default_rng(self.seed)
        self.run = False
        self.machine_dist = config.cluster_configuration.num_nodes
        self.machine_dist/=(np.sum(self.machine_dist))
        self.base_failure_prob = config.cluster_configuration.base
        self.scaling_constant = config.cluster_configuration.scaling_constant

        self.machine_ids = np.arange(self.total_nodes)
        # for nodes 11 : [0.95, 0.7, 0.15 , 0.15, 0.15, ]
        self.machine_status = np.array([1 for _ in range(self.total_nodes)]) # 0 is dead, 1 is alive
        self.repair_time_mean = config.cluster_configuration.repair_time_mean
        self.repair_time_sigma = config.cluster_configuration.repair_time_stdev
        self.repair_scale_factor = config.cluster_configuration.scaling_repair_time_constant

        self.set_probability()

    def sleep_for_repair(self, node_id):
        try:
            repair_duration = self.rng.lognormal(self.repair_time_mean, self.repair_time_sigma) # sample from repair_distribution
            repair_duration *= self.repair_scale_factor
            repair_duration = min(repair_duration, 30)
            repair_duration = max(repair_duration, 7)
            logging.info("[Status] Node {} for {} secs.".format(node_id, repair_duration))
            time.sleep(repair_duration)
            lock.acquire()
            self.machine_status[node_id] = 1
            lock.release()
        except KeyboardInterrupt:
            print('Evironment is shutting down!')
            self.logger.save('env_fails_{}_{}'.format(self.total_nodes, self.config.mab.algo))


    def set_probability(self):
        """Set failure probability of each node"""
        # change the seed
        self.machine_types = np.argmax(self.rng.multinomial(1, self.machine_dist, size=self.total_nodes), axis=-1)
        for i in range(self.total_nodes):
            self.failure_probability[i] = self.base_failure_prob[self.machine_types[i]]*self.scaling_constant
        temp = self.failure_probability[0]
        self.failure_probability[0] = self.failure_probability[1]
        self.failure_probability[1] = temp
        # update the log
        logging.info("[FailEst] Init. Failure probability {}".format(
            np.array2string(self.failure_probability)
        ))


    def fail_nodes(self):
        """Fail up to f nodes"""
        self.logger = FailureLogger(time.time()*100, self.total_nodes, self.failure_probability)
        try:
            while self.run:
                # Sample from binomial dist. (p = node failure prob.)
                alive_nodes = np.where(self.machine_status == 1) # returns indices of all alive nodes
                indices = []

                # we should fail atleast some nodes
                while len(indices) + (self.total_nodes - np.sum(self.machine_status)) < self.min_fail_fraction*self.max_failed_nodes:

                    # Decide to fail or not
                    for idx, val in enumerate(self.failure_probability):
                        # select a new node (hasn't been selected before) which is alive
                        if idx not in indices and self.machine_status[idx] == 1 and self.rng.binomial(1, val) == 1:
                            indices.append(idx)

                # Random sample to limit nodes failed to self.max_failed_nodes
                if len(indices) + (self.total_nodes - np.sum(self.machine_status)) > self.max_failed_nodes:
                    indices = self.rng.choice(
                        indices,
                        self.max_failed_nodes - (self.total_nodes - np.sum(self.machine_status)),
                        replace=False
                    )

                # Only if there is a node to fail, send a message
                if len(indices) != 0:
                    b = np.zeros(self.total_nodes)
                    b[indices] = 1
                    self.logger.tick(time.time()*100, b)
                    # send the failure values to the respective nodes
                    logging.info("[Status] Failed nodes {}".format(indices))
                    host = '127.0.0.1'
                    for port in self.ports:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            node_id = port - self.replica_base_port
                            if port - self.replica_base_port in indices:
                                failVal = "True"
                                self.machine_status[node_id] = 0
                                # thread to sleep for repair period and then change machine_status to alive
                                start_new_thread(self.sleep_for_repair, (node_id, ))
                            else:
                                failVal = "True" if self.machine_status[port - self.replica_base_port] == 0 else "False"
                            logging.info("[SEND] FailureMsg to: {}".format(node_id))
                            message = str(FailureMessage(-2, 0, time.time()*100, failVal))
                            s.connect((host, port))
                            s.send(message.encode('ascii'))
                            s.close()
                        except Exception as msg:
                            logging.error(str(msg) + " while connecting to {}".format(port))
                            s.close()
                time.sleep(self.fail_nodes_update)
        except KeyboardInterrupt:
            print('Evironment is shutting down!')
            make_dirs(join(self.exp_name))
            self.logger.save(join(self.exp_name, 'env_failures.pbz2'))
