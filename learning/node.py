import numpy as np

class Node:
    def __init__(self, id, p_success, n, mean_estimates):
        self.id = id
        self.p_success = p_success
        self.p_failure = 1 - p_success
        self.is_failed = False
        self.total_nodes = n
        self.mean_estimates  = mean_estimates


    def step(self, id, fail):
        #update the failure/success probability
        return 0

    def select_leader(self):
        #return the id/id's of the next leader
        return 0




