#! /bin/bash

set -e
export TRG_DIR=/opt/statsd-agent

sudo apt-get install python-pip
sudo pip install -r requirements.txt

sudo mkdir -pv $TRG_DIR
sudo cp -v *.py $TRG_DIR
sudo cp -v *.cfg $TRG_DIR
sudo cp -v *.conf /etc/init

echo "TODO: Edit $TRG_DIR/statsd-agent.cfg and fix the service= line and then run:"
echo "sudo service statsd-agent start"
echo

