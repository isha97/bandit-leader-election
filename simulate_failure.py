import numpy as np
import threading
import time
from sklearn.model_selection import train_test_split

max_failed_nodes = 3
total_nodes = 3*max_failed_nodes + 1
nodes = np.zeros(shape=total_nodes)
view_changes = 0
current_leader = 0
run = True
lock = threading.Lock()

def select_leader():
    global current_leader
    global view_changes
    global run
    while run:
        if nodes[current_leader] == 1:
            current_leader = (current_leader + 1)%total_nodes
            view_changes = view_changes + 1

def fail_nodes():
    while run:
        all_nodes = np.arange(total_nodes)
        lock.acquire()
        not_failed, failed = train_test_split(all_nodes, test_size=max_failed_nodes)
        for i in range(total_nodes):
            if i in failed:
                nodes[i] = 1
            else:
                nodes[i] = 0
        lock.release()
        time.sleep(2)


if __name__ == "__main__":
    generate_failure = threading.Thread(target=fail_nodes, daemon=True)
    generate_failure.start()
    leader_election = threading.Thread(target=select_leader, daemon=True)
    leader_election.start()
    time.sleep(30)
    run = False
    print(view_changes)



