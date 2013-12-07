#!/usr/bin/env python2

import zmq, msgpack

ctx = zmq.Context()

sock = ctx.socket(zmq.PUSH)
sock.connect("ipc:///tmp/cstatsd")

# Can't write any more code here, Tahoe-LAFS' JSON web API status thingie is broken...
