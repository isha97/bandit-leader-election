#!/bin/bash

yaml() {
    /Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 -c "import yaml;print(yaml.safe_load(open('$1'))$2)"
}

VALUE=$(yaml $1 "['num_nodes']")
VALUE=$(($VALUE-1))

/Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c $1 -t client
/Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c $1 -t env

for i in $( eval echo {0..$VALUE} )
do
	/Users/rochan/Documents/UTMasters/UTSpring22/reinforcement_learning/work/bin/python3 run_simulation_v2.py -c $1 -t node_$i
done
