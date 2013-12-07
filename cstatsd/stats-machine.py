#!/usr/bin/env python2

import zmq, msgpack, time, psutil, yaml, os

ctx = zmq.Context()

sock = ctx.socket(zmq.PUSH)
sock.connect("ipc:///tmp/cstatsd")

with open("config/machine.yaml", "r") as cfile:
	config = yaml.safe_load(cfile)
	
interval = config["interval"]
old_net_data = {}

while True:
	load_avgs = os.getloadavg()
	sock.send(msgpack.packb({
		"service": "machine",
		"msg_type": "value",
		"resource_type": "load_average",
		"unit": "",
		"values": {
			"1m": load_avgs[0],
			"5m": load_avgs[1],
			"15m": load_avgs[2]
		}
	}))
	
	cpu_loads = psutil.cpu_percent(percpu=True)
	
	for i in xrange(0, len(cpu_loads)):
		sock.send(msgpack.packb({
			"service": "machine",
			"msg_type": "value",
			"resource_type": "cpu",
			"unit": "core%d" % (i + 1),
			"values": {
				"load": cpu_loads[i]
			}
		}))
	
	for drive in config["drives"]:
		drive_data = psutil.disk_usage(drive)
		sock.send(msgpack.packb({
			"service": "machine",
			"msg_type": "value",
			"resource_type": "disk",
			"unit": drive,
			"values": {
				"total": drive_data.total,
				"used": drive_data.used,
				"free": drive_data.free,
				"used_percentage": drive_data.percent
			}
		}))
		
	ram_data = psutil.virtual_memory()
	sock.send(msgpack.packb({
		"service": "machine",
		"msg_type": "value",
		"resource_type": "memory",
		"unit": "physical",
		"values": {
			"total": ram_data.total,
			"used": ram_data.used,
			"free": ram_data.available,
			"used_percentage": ram_data.percent,
			"buffers": ram_data.buffers,
			"cache": ram_data.cached
		}
	}))
		
	swap_data = psutil.virtual_memory()
	sock.send(msgpack.packb({
		"service": "machine",
		"msg_type": "value",
		"resource_type": "memory",
		"unit": "swap",
		"values": {
			"total": swap_data.total,
			"used": swap_data.used,
			"free": swap_data.free,
			"used_percentage": swap_data.percent
		}
	}))
	
	net_data = psutil.net_io_counters(pernic=True)
	for nic, data in net_data.iteritems():
		try:
			old_in_b = old_net_data[nic].bytes_recv
			old_out_b = old_net_data[nic].bytes_sent
			old_in_p = old_net_data[nic].packets_recv
			old_out_p = old_net_data[nic].packets_sent
		except KeyError, e:
			# No old data yet, first run? Save and skip to next...
			old_net_data[nic] = data
			continue
		
		diff_in_b = data.bytes_recv - old_in_b
		diff_out_b = data.bytes_sent - old_out_b
		diff_in_p = data.packets_recv - old_in_p
		diff_out_p = data.packets_sent - old_out_p
		
		if diff_in_b < 0:
			diff_in_b = 0
		
		if diff_out_b < 0:
			diff_out_b = 0
		
		if diff_in_p < 0:
			diff_in_p = 0
		
		if diff_out_p < 0:
			diff_out_p = 0
			
		old_net_data[nic] = data
		
		sock.send(msgpack.packb({
			"service": "machine",
			"msg_type": "value",
			"resource_type": "network",
			"unit": nic,
			"values": {
				"bps_in": diff_in_b / interval,
				"bps_out": diff_out_b / interval,
				"pps_in": diff_in_p / interval,
				"pps_out": diff_out_p / interval
			}
		}))
		
	sock.send(msgpack.packb({
		"service": "machine",
		"msg_type": "value",
		"resource_type": "uptime",
		"unit": "",
		"values": {
			"uptime": time.time() - psutil.get_boot_time()
		}
	}))
	
	time.sleep(interval)

