#!/bin/bash

yaml() {
    python3 -c "import yaml;print(yaml.safe_load(open('$1'))$2)"
}

VALUE=$(yaml $1 "['num_nodes']")
VALUE=$(($VALUE-1))

python run_simulation_v2.py -c $1 -t client
python run_simulation_v2.py -c $1 -t env

for i in $( eval echo {0..$VALUE} )
do
	python run_simulation_v2.py -c $1 -t node_$i
done
