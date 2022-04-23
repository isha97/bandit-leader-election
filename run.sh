#!/bin/bash

yaml() {
    /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 -c "import yaml;print(yaml.safe_load(open('$1'))$2)"
}

VALUE=$(yaml $1 "['num_nodes']")
VALUE=$(($VALUE-1))

osascript -e 'tell application "Terminal" to do script "cd /Users/rochan/Documents/UTMasters/UTSpring22/DistributedSystems/leader-election-bft/ && /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c configs/sync_connected.yaml -t client"' &
osascript -e 'tell application "Terminal" to do script "cd /Users/rochan/Documents/UTMasters/UTSpring22/DistributedSystems/leader-election-bft/ && /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c configs/sync_connected.yaml -t env"' &

# for i in $( eval echo {0..$VALUE} )
# do
# 	/Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c $1 -t node_$i &
# done

osascript -e 'tell application "Terminal" to do script "cd /Users/rochan/Documents/UTMasters/UTSpring22/DistributedSystems/leader-election-bft/ && /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c configs/sync_connected.yaml -t node_0"' &
osascript -e 'tell application "Terminal" to do script "cd /Users/rochan/Documents/UTMasters/UTSpring22/DistributedSystems/leader-election-bft/ && /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c configs/sync_connected.yaml -t node_1"' &
osascript -e 'tell application "Terminal" to do script "cd /Users/rochan/Documents/UTMasters/UTSpring22/DistributedSystems/leader-election-bft/ && /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c configs/sync_connected.yaml -t node_2"' &

