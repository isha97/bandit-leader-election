import numpy as np
import time
import threading
from sklearn.model_selection import train_test_split

lock = threading.Lock()

class Environment:
    def __init__(self, n, sleep_sec, nodes, config):
        """Initialize environment

            n: total number of nodes
            sleep_sec: Sleep time between updating failure probability
            nodes: List of node objects
            config: config parameters
        """
        self.total_nodes = n
        self.failure_probability = np.zeros(n)
        self.max_failed_nodes = int((n - 1)/3)
        self.sleep_sec = sleep_sec
        self.nodes = nodes
        self.stationary = config.stationary
        self.init_prob = config.fail_prob.init
        self.update_prob = config.fail_prob.update

        self.run = False
        self.set_probability()


    def set_probability(self):
        """Set failure probability of each node"""
        self.failure_probability = np.random.normal(
            self.init_prob.mean,
            self.init_prob.std,
            self.total_nodes
        )


    def fail_nodes(self):
        """Fail up to f nodes"""
        while self.run:
            # Sample from binomial dist. (p = node failure prob.)
            indices = []
            for idx, val in enumerate(self.failure_probability):
                if np.random.binomial(1, val) == 1:
                    indices.append(idx)
            # Random sample to limit nodes failed to self.max_failed_nodes
            if len(indices) > self.max_failed_nodes:
                indices = np.random.choice(
                    indices,
                    self.max_failed_nodes,
                    replace=False
                )
            # Acquire lock and update all node status
            lock.acquire()
            for i in range(len(self.nodes)):
                self.nodes[i].is_failed = False
            for f in indices:
                self.nodes[f].is_failed = True
            lock.release()
            time.sleep(self.sleep_sec)


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

                time.sleep(self.sleep_sec*1)
        else:
            # Do not change failure prob in stationary case
            pass


    def run_threads(self):
        """Run threads to fail_nodes and update_probability"""
        self.run = True
        generate_failure = threading.Thread(target=self.fail_nodes)
        generate_failure.start()
        generate_failure1 = threading.Thread(target=self.update_probability)
        generate_failure1.start()


    def stop_threads(self):
        """Terminate threads"""
        self.run = False
