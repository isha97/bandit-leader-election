import numpy as np
import time
import threading
from sklearn.model_selection import train_test_split

class Environment:
    def __init__(self, n, sleep_sec):
        self.total_nodes = n
        self.failure_probability = np.zeros(n)
        self.max_failed_nodes = int((n -1)/3)
        self.failed_nodes = set()
        self.run = False
        self.sleep_sec = sleep_sec

    def set_probability(self):
        self.failure_probability = np.random.normal(0.2, 0.01, self.total_nodes)

    def fail_nodes(self):
        while self.run:
            indices = np.argpartition(self.failure_probability, -self.max_failed_nodes)[-self.max_failed_nodes:]
            self.failed_nodes.clear()
            for f in indices:
                self.failed_nodes.add(f)
            time.sleep(self.sleep_sec)

    def update_probability(self):
        decrease, increase = train_test_split(np.arange(self.total_nodes), test_size=0.5)
        for i in range(self.total_nodes):
            if i in decrease:
                self.failure_probability -= abs(np.random.normal(0.3, 0.1, 1))
                self.failure_probability = max(0, self.failure_probability)
            else:
                self.failure_probability += abs(np.random.normal(0.3, 0.1, 1))
                self.failure_probability = min(1, self.failure_probability)

    def run_threads(self):
        self.run = True
        generate_failure = threading.Thread(target=self.fail_nodes, daemon=True)
        generate_failure.start()

    def stop_threads(self):
        self.run = False

