#!/usr/bin/env python2

import zmq, msgpack, time, yaml, socket

ctx = zmq.Context()

sock = ctx.socket(zmq.PUSH)
sock.connect("ipc:///tmp/cstatsd")

with open("config/ports.yaml", "r") as cfile:
	config = yaml.safe_load(cfile)

interval = config["interval"]

old_status = {}

while True:
	for port, service_name in config["ports"].iteritems():
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(0.5)
			s.connect(("127.0.0.1", port))
			s.shutdown(socket.SHUT_RDWR)
			s.close()
			up = True
		except socket.error, e:
			up = False
			
		try:
			if up == old_status[port]:
				send_notice = False
			else:
				send_notice = True
				initial = False
		except KeyError, e:
			send_notice = True
			initial = True
			
		old_status[port] = up
			
		if send_notice:
			if up:
				msg_type = "up"
			else:
				msg_type = "down"
				
			sock.send(msgpack.packb({
				"service": "port",
				"msg_type": msg_type,
				"unit": "%s (%s)" % (service_name, port),
				"initial": initial
			}))
			
	time.sleep(interval)
	
