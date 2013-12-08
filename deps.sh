#!/bin/bash
# You need squeeze-backports if you run this on squeeze!
apt-get install -y libzmq-dev libffi-dev
pip install pyzmq msgpack-python pynacl pyyaml
