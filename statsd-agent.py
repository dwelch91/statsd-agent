import argparse
import multiprocessing
import platform
import time

import psutil
import statsd

isLinux = platform.system() == 'Linux'


def disk(host, port, prefix):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'disk']))
        while True:
            disk_usage = psutil.disk_usage('/')
            with client.pipeline() as pipe:
                pipe.gauge('root.total', disk_usage.total)
                pipe.gauge('root.used', disk_usage.used)
                pipe.gauge('root.free', disk_usage.free)
                pipe.gauge('root.percent', disk_usage.percent)

            time.sleep(10)

    except KeyboardInterrupt:
        print("Exiting...")


def cpu_times(host, port, prefix):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'cpu']))
        while True:
            cpu_times = psutil.cpu_times()
            with client.pipeline() as pipe:
                pipe.gauge('system_wide.times.user', cpu_times.user)
                pipe.gauge('system_wide.times.nice', cpu_times.nice)
                pipe.gauge('system_wide.times.system', cpu_times.system)
                pipe.gauge('system_wide.times.idle', cpu_times.idle)
                if isLinux:
                    pipe.gauge('system_wide.times.guest_nice', cpu_times.guest_nice)
                    pipe.gauge('system_wide.times.guest', cpu_times.guest)
                    pipe.gauge('system_wide.times.steal', cpu_times.steal)
                    pipe.gauge('system_wide.times.softirq', cpu_times.softirq)
                    pipe.gauge('system_wide.times.iowait', cpu_times.iowait)
                    pipe.gauge('system_wide.times.irq', cpu_times.irq)

            time.sleep(10)

    except KeyboardInterrupt:
        print("Exiting...")


def cpu_times_percent(host, port, prefix):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'cpu']))
        while True:
            value = psutil.cpu_percent(interval=1)
            cpu_times_pcnt = psutil.cpu_times_percent(interval=1)

            with client.pipeline() as pipe:
                pipe.gauge('system_wide.percent', value)
                pipe.gauge('system_wide.times_percent.user', cpu_times_pcnt.user)
                pipe.gauge('system_wide.times_percent.nice', cpu_times_pcnt.nice)
                pipe.gauge('system_wide.times_percent.system', cpu_times_pcnt.system)
                pipe.gauge('system_wide.times_percent.idle', cpu_times_pcnt.idle)
                if isLinux:
                    pipe.gauge('system_wide.times_percent.iowait', cpu_times_pcnt.iowait)
                    pipe.gauge('system_wide.times_percent.irq', cpu_times_pcnt.irq)
                    pipe.gauge('system_wide.times_percent.softirq', cpu_times_pcnt.softirq)
                    pipe.gauge('system_wide.times_percent.steal', cpu_times_pcnt.steal)
                    pipe.gauge('system_wide.times_percent.guest', cpu_times_pcnt.guest)
                    pipe.gauge('system_wide.times_percent.guest_nice', cpu_times_pcnt.guest_nice)

            time.sleep(8)

    except KeyboardInterrupt:
        print("Exiting...")


def memory(host, port, prefix):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'memory']))
        while True:
            swap = psutil.swap_memory()
            virtual = psutil.virtual_memory()

            with client.pipeline() as pipe:
                pipe.gauge('swap.total', swap.total)
                pipe.gauge('swap.used', swap.used)
                pipe.gauge('swap.free', swap.free)
                pipe.gauge('swap.percent', swap.percent)
                pipe.gauge('virtual.total', virtual.total)
                pipe.gauge('virtual.available', virtual.available)
                pipe.gauge('virtual.used', virtual.used)
                pipe.gauge('virtual.free', virtual.free)
                pipe.gauge('virtual.percent', virtual.percent)
                pipe.gauge('virtual.active', virtual.active)
                pipe.gauge('virtual.inactive', virtual.inactive)
                if isLinux:
                    pipe.gauge('virtual.buffers', virtual.buffers)
                    pipe.gauge('virtual.cached', virtual.cached)

            time.sleep(10)

    except KeyboardInterrupt:
        print("Exiting...")


def network(host, port, prefix, nic):
    try:
        client = statsd.StatsClient(host, port, prefix='.'.join([prefix, 'network']))

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
                pipe.gauge('network.send_rate', send_rate)
                pipe.gauge('network.recv_rate', recv_rate)

            time.sleep(10)

    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-t', type=str, default='localhost')
    parser.add_argument('--port', '-p', type=int, default=8125)
    parser.add_argument('--prefix', '-x', type=str, default='')
    parser.add_argument('--network', '--nic', '-n', type=str, default='eth0')
    args = parser.parse_args()

    multiprocessing.Process(target=disk, args=(args.host, args.port, args.prefix)).start()
    multiprocessing.Process(target=cpu_times, args=(args.host, args.port, args.prefix)).start()
    multiprocessing.Process(target=cpu_times_percent, args=(args.host, args.port, args.prefix)).start()
    multiprocessing.Process(target=memory, args=(args.host, args.port, args.prefix)).start()
    multiprocessing.Process(target=network, args=(args.host, args.port, args.prefix, args.network)).start()
