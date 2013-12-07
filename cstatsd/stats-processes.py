#!/usr/bin/env python2

import zmq, msgpack, time, yaml, psutil, fnmatch

ctx = zmq.Context()

sock = ctx.socket(zmq.PUSH)
sock.connect("ipc:///tmp/cstatsd")

with open("config/processes.yaml", "r") as cfile:
	config = yaml.safe_load(cfile)

interval = config["interval"]

old_status = {}

while True:
	all_procs = psutil.get_process_list()
	
	for service_name, patterns in config["processes"].iteritems():
		matches = all_procs
		
		try:
			matches = filter(lambda proc: len(proc.cmdline) > 0 and fnmatch.fnmatch(proc.cmdline[0], patterns["name"]), matches)
		except KeyError, e:
			pass
		
		try:
			for arg, pattern in patterns["args"].iteritems():
				try:
					matches = filter(lambda proc: len(proc.cmdline) >= (arg + 1) and fnmatch.fnmatch(proc.cmdline[arg], pattern), matches)
				except KeyError, e:
					pass
		except KeyError, e:
			pass  # No arguments specified to filter
			
		if len(matches) > 0:
			up = True
		else:
			up = False
			
		try:
			if up == old_status[service_name]:
				send_notice = False
			else:
				send_notice = True
				initial = False
		except KeyError, e:
			send_notice = True
			initial = True
			
		old_status[service_name] = up
			
		if send_notice:
			if up:
				msg_type = "up"
			else:
				msg_type = "down"
				
			sock.send(msgpack.packb({
				"service": "process",
				"msg_type": msg_type,
				"unit": service_name,
				"initial": initial
			}))
			
			
	time.sleep(interval)
	
