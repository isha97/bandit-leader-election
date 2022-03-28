import numpy as np

class Environment:
    def __init__(self, n):
        self.total_nodes = n
        self.failure_probability = np.zeros(n)

    def set_probability(self):
        return 0

    def update_probability(self):
        return 0

