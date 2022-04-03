import threading
from learning.environment import Environment
import time

def run_environment():
    pass

def stop_environment():
    pass

def run_nodes():
    return 0

if __name__ == "__main__":
    generate_failure = threading.Thread(target=run_environment, daemon=True)
    generate_failure.start()
    leader_election = threading.Thread(target=run_nodes, daemon=True)
    leader_election.start()
