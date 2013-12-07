#!/usr/bin/env python2

import zmq, msgpack, time, psutil, yaml, os

ctx = zmq.Context()

sock = ctx.socket(zmq.PUSH)
sock.connect("ipc:///tmp/cstatsd")

with open("config/machine.yaml", "r") as cfile:
	config = yaml.safe_load(cfile)
	
interval = config["interval"]
old_net_data = {}

disk_map = {}
last_io_data = {}

for disk in psutil.disk_partitions():
	disk_map[disk.device] = disk

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
	
	io_counters = psutil.disk_io_counters(perdisk=True)
	
	for drive in config["drives"]:
		drive_data = psutil.disk_usage(disk_map[drive].mountpoint)
		io_data = None
		
		for diskname, data in io_counters.iteritems():
			if drive.endswith(diskname):
				io_data = data
				
		if io_data is None or drive not in last_io_data:
			read_bps = 0
			write_bps = 0
			read_iops = 0
			write_iops = 0
		else:
			read_bps = (io_data.read_bytes - last_io_data[drive].read_bytes) / interval
			write_bps = (io_data.write_bytes - last_io_data[drive].write_bytes) / interval
			read_iops = (io_data.read_count - last_io_data[drive].read_count) / interval
			write_iops = (io_data.write_count - last_io_data[drive].write_count) / interval
			
		if io_data is not None:
			last_io_data[drive] = io_data
			
		sock.send(msgpack.packb({
			"service": "machine",
			"msg_type": "value",
			"resource_type": "disk",
			"unit": drive,
			"values": {
				"total": drive_data.total,
				"used": drive_data.used,
				"free": drive_data.free,
				"used_percentage": drive_data.percent,
				"bps_read": read_bps,
				"bps_write": write_bps,
				"iops_read": read_iops,
				"iops_write": write_iops,
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

