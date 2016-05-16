#! /bin/bash

set -e
export TRG_DIR = /opt/statsd-agent

sudo apt-get install python-pip
sudo pip install -r requirements.txt

sudo mkdir -p $TRG_DIR
sudo cp *.py $TRG_DIR
sudo cp *.cfg $TRG_DIR
sudo cp *.conf /etc/init

echo "TODO: Edit $TRG_DIR/statsd-agent.cfg and fix the service= line."
