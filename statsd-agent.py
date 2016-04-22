import argparse
import multiprocessing
import os
import platform
import socket
import sys
import time
from ConfigParser import RawConfigParser

import psutil
import statsd

system = platform.system()
isLinux = system == 'Linux'
isWindows = system == 'Windows'


def disk(host, port, prefix, basic, fields, interval=10, debug=False):
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


def cpu_times(host, port, prefix, basic, fields, interval=10, debug=False):
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


def cpu_times_percent(host, port, prefix, basic, fields, interval=10, debug=False):
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


def memory(host, port, prefix, basic, fields, interval=10, debug=False):
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


def network(host, port, prefix, nic, basic, fields, interval=10, debug=False):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'network']))
        if nic is None:
            found = False
            nics = psutil.net_if_addrs()
            for n, info in nics.items():
                for addr in info:
                    if addr.family == socket.AF_INET and addr.address.startswith('10.'):
                        nic = n
                        found = True
                        break
                if found:
                    break
            else:
                print("ERROR: Could not locate 10.x.x.x network interface!")
                return

        if debug:
            print(nic)

        fields += ',nic={}'.format(nic)
        prev_bytes_sent, prev_bytes_recv, prev_timer = 0, 0, 0
        while True:
            try:
                net = psutil.net_io_counters(True)[nic]
                timer = time.time()
            except KeyError:
                print("ERROR: Unknown network interface!")
                return

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


def misc(host, port, prefix, _, fields, interval=10, debug=False):
    try:
        client = statsd.StatsClient(host, port, prefix=prefix)
        boot_time = psutil.boot_time()
        client.gauge('boot_time{}'.format(fields), boot_time)
        if debug:
            print(boot_time)
        while True:
            with client.pipeline() as pipe:
                uptime = time.time() - boot_time
                pipe.gauge('uptime{}'.format(fields), uptime)
                if debug:
                    print(uptime)
                pipe.gauge('users{}'.format(fields), len(psutil.users()))
                pipe.gauge('processes{}'.format(fields), len(psutil.pids()))

            time.sleep(interval)

    except KeyboardInterrupt:
        pass


def to_int(v, d):
    try:
        return int(v)
    except (ValueError, TypeError):
        return d


if __name__ == '__main__':
    config = RawConfigParser(allow_no_value=True)
    config.read('statsd-agent.cfg')

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-t', type=str, default=config.get('statsd-agent', 'host') or 'localhost',
                        help='Hostname or IP of statsd server.')
    parser.add_argument('--port', '-p', type=int, default=to_int(config.getint('statsd-agent', 'port'), 8125),
                        help='UDP port number of statsd server.')
    parser.add_argument('--prefix', '-x', type=str, default=config.get('statsd-agent', 'prefix'),
                        help='Prefix value to add to each measurement.')
    parser.add_argument('--field', '-f', action='append', default=[],
                        help="One or more 'key=value' fields to add to each measurement.")
    parser.add_argument('--network', '--nic', '-n', type=str,
                        default=config.get('statsd-agent', 'nic') or None,
                        help='NIC to measure.')
    parser.add_argument('--basic', '-b', action='store_true',
                        help='If set, only basic measurements gathered and sent to statsd.')
    parser.add_argument('--interval', '-i', type=int, default=to_int(config.getint('statsd-agent', 'interval')) or 10,
                        help='Time in seconds between measurements. Must be > 2.')
    parser.add_argument('--add-host-field', '-a', action='store_true', help='Auto add host= to fields.')
    parser.add_argument('--debug', '-g', action='store_true', help="Turn on debugging.")
    args = parser.parse_args()

    fields = []
    field_set = set()
    for field in args.field:
        name, value = field.split('=', 1)
        if name not in field_set:
            fields.append(field)
            field_set.add(name)

    for option in config.options('fields'):
        value = config.get('fields', option)
        if value and option not in field_set:
            fields.append("{}={}".format(option, value))
            field_set.add(option)

    debug = config.getboolean('statsd-agent', 'debug') or args.debug
    basic = config.getboolean('statsd-agent', 'basic') or args.basic
    prefix = args.prefix if args.prefix else None

    if config.getboolean('statsd-agent', 'add-host-field') or args.add_host_field:
        host_field = "host={}".format(socket.gethostname())
        fields.append(host_field)
        if debug:
            print(host_field)

    fields = ','.join([f.replace(',', '_').replace(' ', '_').replace('.', '-') for f in fields])
    if debug:
        print(fields)
    if fields:
        fields = ',' + fields

    if args.interval < 3:
        print("ERROR: Invalid interval (< 3sec).")
        sys.exit(1)

    multiprocessing.Process(target=disk, args=(args.host, args.port, prefix, basic, fields, args.interval, debug)).start()
    multiprocessing.Process(target=cpu_times, args=(args.host, args.port, prefix, basic, fields, args.interval, debug)).start()
    multiprocessing.Process(target=cpu_times_percent, args=(args.host, args.port, prefix, basic, fields, args.interval, debug)).start()
    multiprocessing.Process(target=memory, args=(args.host, args.port, prefix, basic, fields, args.interval, debug)).start()
    multiprocessing.Process(target=network, args=(args.host, args.port, prefix, args.network, basic, fields, args.interval, debug)).start()
    multiprocessing.Process(target=misc, args=(args.host, args.port, prefix, basic, fields, args.interval, debug)).start()
