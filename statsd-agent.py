import argparse
import multiprocessing
import os
import platform
import sys
import time
import socket

import psutil
import statsd

system = platform.system()
isLinux = system == 'Linux'
isWindows = system == 'Windows'


def disk(host, port, prefix, basic, fields, interval=10):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'disk']))
        while True:
            disk_usage = psutil.disk_usage('/')
            with client.pipeline() as pipe:
                pipe.gauge('root.total{}'.format(fields), disk_usage.total)
                pipe.gauge('root.used{}'.format(fields), disk_usage.used)
                pipe.gauge('root.free{}'.format(fields), disk_usage.free)
                pipe.gauge('root.percent{}'.format(fields), disk_usage.percent)

                if not basic:
                    counters = psutil.disk_io_counters(False)
                    pipe.gauge('all.read_time{}'.format(fields), counters.read_time)
                    pipe.gauge('all.write_time{}'.format(fields), counters.write_time)
                    if isLinux:
                        pipe.gauge('all.busy_time{}'.format(fields), counters.busy_time)

            time.sleep(interval)

    except KeyboardInterrupt:
        pass


def cpu_times(host, port, prefix, basic, fields, interval=10):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'cpu']))
        while True:
            cpu_times = psutil.cpu_times()
            with client.pipeline() as pipe:
                pipe.gauge('times.user{}'.format(fields), cpu_times.user)
                pipe.gauge('times.system{}'.format(fields), cpu_times.system)
                pipe.gauge('times.idle{}'.format(fields), cpu_times.idle)

                if not isWindows:
                    pipe.gauge('times.nice{}'.format(fields), cpu_times.nice)
                    load = os.getloadavg()
                    pipe.gauge('loadavg.1{}'.format(fields), load[0])
                    pipe.gauge('loadavg.5{}'.format(fields), load[1])
                    pipe.gauge('loadavg.15{}'.format(fields), load[2])

                if isLinux and not basic:
                    pipe.gauge('times.guest_nice{}'.format(fields), cpu_times.guest_nice)
                    pipe.gauge('times.guest{}'.format(fields), cpu_times.guest)
                    pipe.gauge('times.steal{}'.format(fields), cpu_times.steal)
                    pipe.gauge('times.softirq{}'.format(fields), cpu_times.softirq)
                    pipe.gauge('times.iowait{}'.format(fields), cpu_times.iowait)
                    pipe.gauge('times.irq{}'.format(fields), cpu_times.irq)

            time.sleep(interval)

    except KeyboardInterrupt:
        pass


def cpu_times_percent(host, port, prefix, basic, fields, interval=10):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'cpu']))
        while True:
            value = psutil.cpu_percent(interval=1)
            cpu_times_pcnt = psutil.cpu_times_percent(interval=1)

            with client.pipeline() as pipe:
                pipe.gauge('percent{}'.format(fields), value)
                pipe.gauge('percent.user{}'.format(fields), cpu_times_pcnt.user)
                pipe.gauge('percent.system{}'.format(fields), cpu_times_pcnt.system)
                pipe.gauge('percent.idle{}'.format(fields), cpu_times_pcnt.idle)

                if not isWindows:
                    pipe.gauge('percent.nice{}'.format(fields), cpu_times_pcnt.nice)

                if isLinux and not basic:
                    pipe.gauge('percent.iowait{}'.format(fields), cpu_times_pcnt.iowait)
                    pipe.gauge('percent.irq{}'.format(fields), cpu_times_pcnt.irq)
                    pipe.gauge('percent.softirq{}'.format(fields), cpu_times_pcnt.softirq)
                    pipe.gauge('percent.steal{}'.format(fields), cpu_times_pcnt.steal)
                    pipe.gauge('percent.guest{}'.format(fields), cpu_times_pcnt.guest)
                    pipe.gauge('percent.guest_nice{}'.format(fields), cpu_times_pcnt.guest_nice)

            time.sleep(interval - 2)

    except KeyboardInterrupt:
        pass


def memory(host, port, prefix, basic, fields, interval=10):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'memory']))
        while True:
            with client.pipeline() as pipe:
                virtual = psutil.virtual_memory()
                pipe.gauge('virtual.total{}'.format(fields), virtual.total)
                pipe.gauge('virtual.available{}'.format(fields), virtual.available)
                pipe.gauge('virtual.used{}'.format(fields), virtual.used)
                pipe.gauge('virtual.free{}'.format(fields), virtual.free)
                pipe.gauge('virtual.percent{}'.format(fields), virtual.percent)

                if not basic:
                    swap = psutil.swap_memory()
                    pipe.gauge('swap.total{}'.format(fields), swap.total)
                    pipe.gauge('swap.used{}'.format(fields), swap.used)
                    pipe.gauge('swap.free{}'.format(fields), swap.free)
                    pipe.gauge('swap.percent{}'.format(fields), swap.percent)

                if not isWindows and not basic:
                    pipe.gauge('virtual.active{}'.format(fields), virtual.active)
                    pipe.gauge('virtual.inactive{}'.format(fields), virtual.inactive)

                if isLinux and not basic:
                    pipe.gauge('virtual.buffers{}'.format(fields), virtual.buffers)
                    pipe.gauge('virtual.cached{}'.format(fields), virtual.cached)

            time.sleep(interval)

    except KeyboardInterrupt:
        pass


def network(host, port, prefix, nic, basic, fields, interval=10):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'network']))
        fields += ',nic={}'.format(nic)
        prev_bytes_sent, prev_bytes_recv, prev_timer = 0, 0, 0
        while True:
            try:
                net = psutil.net_io_counters(True)[nic]
                timer = time.time()
            except KeyError:
                print("ERROR: Unknown network interface!")
                break

            sent = net.bytes_sent - prev_bytes_sent  # B
            recv = net.bytes_recv - prev_bytes_recv
            prev_bytes_sent = net.bytes_sent
            prev_bytes_recv = net.bytes_recv
            elapsed = timer - prev_timer  # s
            send_rate = sent / elapsed  # B/s
            recv_rate = recv / elapsed
            prev_timer = timer

            with client.pipeline() as pipe:
                pipe.gauge('send_rate{}'.format(fields), send_rate)
                pipe.gauge('recv_rate{}'.format(fields), recv_rate)
                if not basic:
                    pipe.gauge('send_errors{}'.format(fields), net.errin)
                    pipe.gauge('recv_errors{}'.format(fields), net.errout)

            time.sleep(interval)

    except KeyboardInterrupt:
        pass


def misc(host, port, prefix, _, fields, interval=10):
    try:
        client = statsd.StatsClient(host, port, prefix=prefix)
        boot_time = psutil.boot_time()
        client.gauge('boot_time{}'.format(fields), boot_time)
        while True:
            with client.pipeline() as pipe:
                pipe.gauge('uptime{}'.format(fields), time.time() - boot_time)
                pipe.gauge('users{}'.format(fields), len(psutil.users()))
                pipe.gauge('processes{}'.format(fields), len(psutil.pids()))

            time.sleep(interval)

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-t', type=str, default='localhost', help='Hostname or IP of statsd server.')
    parser.add_argument('--port', '-p', type=int, default=8125, help='UDP port number of statsd server.')
    parser.add_argument('--prefix', '-x', type=str, default='system', help='Prefix value to add to each measurement.')
    parser.add_argument('--field', '-f', action='append', default=[],
                        help="One or more 'key=value' fields to add to each measurement.")
    parser.add_argument('--network', '--nic', '-n', type=str,
                        default='Local Area Connection' if isWindows else 'eth0' if isLinux else 'en0',
                        help='NIC to measure.')
    parser.add_argument('--basic', '-b', action='store_true',
                        help='If set, only basic measurements gathered and sent to statsd.')
    parser.add_argument('--interval', '-i', type=int, default=10,
                        help='Time in seconds between measurements. Must be > 2.')
    parser.add_argument('--add-host-field', '-a', action='store_true', help='Auto add host= to fields.')
    args = parser.parse_args()
    fields = args.field[:]

    if args.add_host_field:
        fields.append("host={}".format(socket.gethostname()))

    fields = ','.join([f.replace(',', '_').replace(' ', '_').replace('.', '-') for f in fields])
    if fields:
        fields = ',' + fields

    if args.interval < 3:
        print("ERROR: Invalid interval (< 3sec).")
        sys.exit(1)

    multiprocessing.Process(target=disk, args=(args.host, args.port, args.prefix, args.basic, fields, args.interval)).start()
    multiprocessing.Process(target=cpu_times, args=(args.host, args.port, args.prefix, args.basic, fields, args.interval)).start()
    multiprocessing.Process(target=cpu_times_percent, args=(args.host, args.port, args.prefix, args.basic, fields, args.interval)).start()
    multiprocessing.Process(target=memory, args=(args.host, args.port, args.prefix, args.basic, fields, args.interval)).start()
    multiprocessing.Process(target=network, args=(args.host, args.port, args.prefix, args.network, args.basic, fields, args.interval)).start()
    multiprocessing.Process(target=misc, args=(args.host, args.port, args.prefix, args.basic, fields, args.interval)).start()
