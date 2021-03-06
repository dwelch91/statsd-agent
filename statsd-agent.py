from __future__ import division
import argparse
import platform
import time
import socket
import os
import sys
import traceback
import jmespath
from common import log

try:
    from ConfigParser import RawConfigParser, Error
except ImportError:
    from configparser import RawConfigParser, Error

from docker import get

import psutil
import statsd



system = platform.system()
isLinux = system == 'Linux'
isWindows = system == 'Windows'


def to_int(value, default):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def disk(host, port, prefix, fields, debug=False):
    prefix = '.'.join([prefix, 'disk']) if prefix else 'disk'
    client = statsd.StatsClient(host, port, prefix=prefix)
    disk_usage = psutil.disk_usage('/')
    with client.pipeline() as pipe:
        pipe.gauge('root.total{}'.format(fields), disk_usage.total)
        pipe.gauge('root.used{}'.format(fields), disk_usage.used)
        pipe.gauge('root.free{}'.format(fields), disk_usage.free)
        pipe.gauge('root.percent{}'.format(fields), disk_usage.percent)

        counters = psutil.disk_io_counters(False)
        pipe.gauge('all.read_time{}'.format(fields), counters.read_time)
        pipe.gauge('all.write_time{}'.format(fields), counters.write_time)
        if isLinux:
            pipe.gauge('all.busy_time{}'.format(fields), counters.busy_time)


def cpu_times(host, port, prefix, fields, debug=False):
    prefix = '.'.join([prefix, 'cpu']) if prefix else 'cpu'
    client = statsd.StatsClient(host, port, prefix=prefix)
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

        if isLinux:
            pipe.gauge('times.guest_nice{}'.format(fields), cpu_times.guest_nice)
            pipe.gauge('times.guest{}'.format(fields), cpu_times.guest)
            pipe.gauge('times.steal{}'.format(fields), cpu_times.steal)
            pipe.gauge('times.softirq{}'.format(fields), cpu_times.softirq)
            pipe.gauge('times.iowait{}'.format(fields), cpu_times.iowait)
            pipe.gauge('times.irq{}'.format(fields), cpu_times.irq)


def cpu_times_percent(host, port, prefix, fields, debug=False):
    prefix = '.'.join([prefix, 'cpu']) if prefix else 'cpu'
    client = statsd.StatsClient(host, port, prefix=prefix)
    value = psutil.cpu_percent(interval=1)
    cpu_times_pcnt = psutil.cpu_times_percent(interval=1)

    with client.pipeline() as pipe:
        pipe.gauge('percent{}'.format(fields), value)
        pipe.gauge('percent.user{}'.format(fields), cpu_times_pcnt.user)
        pipe.gauge('percent.system{}'.format(fields), cpu_times_pcnt.system)
        pipe.gauge('percent.idle{}'.format(fields), cpu_times_pcnt.idle)

        if not isWindows:
            pipe.gauge('percent.nice{}'.format(fields), cpu_times_pcnt.nice)

        if isLinux:
            pipe.gauge('percent.iowait{}'.format(fields), cpu_times_pcnt.iowait)
            pipe.gauge('percent.irq{}'.format(fields), cpu_times_pcnt.irq)
            pipe.gauge('percent.softirq{}'.format(fields), cpu_times_pcnt.softirq)
            pipe.gauge('percent.steal{}'.format(fields), cpu_times_pcnt.steal)
            pipe.gauge('percent.guest{}'.format(fields), cpu_times_pcnt.guest)
            pipe.gauge('percent.guest_nice{}'.format(fields), cpu_times_pcnt.guest_nice)


def memory(host, port, prefix, fields, debug=False):
    prefix = '.'.join([prefix, 'memory']) if prefix else 'memory'
    client = statsd.StatsClient(host, port, prefix=prefix)
    with client.pipeline() as pipe:
        virtual = psutil.virtual_memory()
        pipe.gauge('virtual.total{}'.format(fields), virtual.total)
        pipe.gauge('virtual.available{}'.format(fields), virtual.available)
        pipe.gauge('virtual.used{}'.format(fields), virtual.used)
        pipe.gauge('virtual.free{}'.format(fields), virtual.free)
        pipe.gauge('virtual.percent{}'.format(fields), virtual.percent)

        swap = psutil.swap_memory()
        pipe.gauge('swap.total{}'.format(fields), swap.total)
        pipe.gauge('swap.used{}'.format(fields), swap.used)
        pipe.gauge('swap.free{}'.format(fields), swap.free)
        pipe.gauge('swap.percent{}'.format(fields), swap.percent)

        if not isWindows:
            pipe.gauge('virtual.active{}'.format(fields), virtual.active)
            pipe.gauge('virtual.inactive{}'.format(fields), virtual.inactive)

        if isLinux:
            pipe.gauge('virtual.buffers{}'.format(fields), virtual.buffers)
            pipe.gauge('virtual.cached{}'.format(fields), virtual.cached)


prev_bytes_sent, prev_bytes_recv, prev_timer = 0, 0, 0


def network(host, port, prefix, fields, nic, debug=False):
    global prev_bytes_sent, prev_bytes_recv, prev_timer

    try:
        net = psutil.net_io_counters(True)[nic]
    except KeyError:
        return
    timer = time.time()
    prefix = '.'.join([prefix, 'network']) if prefix else 'network'
    client = statsd.StatsClient(host, port, prefix=prefix)
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
        pipe.gauge('send_errors{}'.format(fields), net.errin)
        pipe.gauge('recv_errors{}'.format(fields), net.errout)


def misc(host, port, prefix, fields, debug=False):
    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time
    client = statsd.StatsClient(host, port, prefix=prefix)
    with client.pipeline() as pipe:
        pipe.gauge('uptime{}'.format(fields), uptime)
        if debug:
            log.debug("uptime={}".format(uptime))

        pipe.gauge('users{}'.format(fields), len(psutil.users()))
        pipe.gauge('processes{}'.format(fields), len(psutil.pids()))


def run_once(host, port, prefix, fields, nic, debug=False):
    misc(host, port, prefix, fields, debug)
    network(host, port, prefix, fields, nic, debug)
    memory(host, port, prefix, fields, debug)
    cpu_times(host, port, prefix, fields, debug)
    cpu_times_percent(host, port, prefix, fields, debug)
    disk(host, port, prefix, fields, debug)


def run_docker(address, interval, host, port, debug=False):
    prev_cpu, prev_system = {}, {}
    prev_tx_bytes, prev_rx_bytes, prev_timer = {}, {}, {}
    client = statsd.StatsClient(host, port)
    MEM_USAGE = jmespath.compile('memory_stats.usage')
    MEM_LIMIT = jmespath.compile('memory_stats.limit')
    TOTAL_USAGE = jmespath.compile('cpu_stats.cpu_usage.total_usage')
    SYSTEM_USAGE = jmespath.compile('cpu_stats.system_cpu_usage')
    NUM_CPUS = jmespath.compile('length(cpu_stats.cpu_usage.percpu_usage)')
    TX_BYTES = jmespath.compile('networks.eth0.tx_bytes')  # TODO: Always eth0??? (likely not...)
    RX_BYTES = jmespath.compile('networks.eth0.rx_bytes')
    try:
        while True:
            with client.pipeline() as pipe:
                start = time.time()
                containers = get(address, '/containers/json?all=1', debug)
                for container in containers:
                    name = container.get('Names')[0].strip('/')
                    status = container.get('Status')
                    id_ = container.get('Id')
                    log.debug("{}: {}".format(name, status))
                    stats = get(address, '/containers/{}/stats?stream=0'.format(id_), debug)  # Very slow call...

                    mem_usage = MEM_USAGE.search(stats) or 0
                    mem_limit = MEM_LIMIT.search(stats) or 1
                    mem_percent = 100.0 * (mem_usage / mem_limit) if mem_limit > 0 else 0

                    if debug:
                        log.debug("{}: Mem: {:,} {:,} {}%".format(name, mem_usage, mem_limit, mem_percent))

                    pipe.gauge('system.memory.virtual.percent,service={}'.format(name), mem_percent)

                    # http://stackoverflow.com/questions/30271942/get-docker-container-cpu-usage-as-percentage
                    cpu_percent = 0

                    total_usage = TOTAL_USAGE.search(stats) or 0
                    cpu_delta = total_usage - prev_cpu.get(name, 0)

                    system_usage = SYSTEM_USAGE.search(stats) or 0
                    system_delta = system_usage - prev_system.get(name, 0)

                    num_cpus = NUM_CPUS.search(stats) or 1

                    if system_delta > 0 and cpu_delta > 0:
                        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

                    if debug:
                        log.debug("{}: Cpu: {}, {}: {}%".format(name, cpu_delta, system_delta, cpu_percent))

                    prev_cpu[name], prev_system[name] = total_usage, system_usage

                    pipe.gauge('system.cpu.percent,service={}'.format(name), cpu_percent)

                    tx_bytes = TX_BYTES.search(stats) or 0
                    rx_bytes = RX_BYTES.search(stats) or 0

                    tx = tx_bytes - prev_tx_bytes.setdefault(name, 0)  # B
                    rx = rx_bytes - prev_rx_bytes.setdefault(name, 0)

                    timer = time.time()
                    elapsed = timer - prev_timer.get(name, 0)  # s
                    prev_timer[name] = timer

                    tx_rate = tx / elapsed if tx > 0 and elapsed > 0 else 0  # B/s
                    rx_rate = rx / elapsed if rx > 0 and elapsed > 0 else 0

                    pipe.gauge('system.network.send_rate,service={}'.format(name), tx_rate)
                    pipe.gauge('system.network.recv_rate,service={}'.format(name), rx_rate)

                    if debug:
                        log.debug("{}: Net Tx: {:,} -> {:,} ({}B/s)".format(name, tx_bytes, prev_tx_bytes[name], tx_rate))
                        log.debug("{}: Net Rx: {:,} -> {:,} ({}B/s)".format(name, rx_bytes, prev_rx_bytes[name], rx_rate))

                    prev_tx_bytes[name] = tx_bytes
                    prev_rx_bytes[name] = rx_bytes

                    pipe.gauge('system.disk.root.percent,service={}'.format(name), 0)

            elapsed = time.time() - start
            log.debug("docker: {}ms".format(int(elapsed * 1000)))
            time.sleep(interval - elapsed)

    except Exception as e:
        log.exception(e)


class StatsdConfig(RawConfigParser):
    def get_str(self, opt, section='statsd-agent', default=''):
        try:
            return self.get(section, opt)
        except Error:
            return default

    def get_int(self, opt, section='statsd-agent', default=0):
        return to_int(self.get_str(opt, section), default)

    def get_boolean(self, opt, section='statsd-agent', default=False):
        try:
            return self.getboolean(section, opt)
        except Error:
            return default

    def get_fields(self, arg_fields=None, arg_add_host_field=True):
        if arg_fields is None:
            arg_fields = []

        fields = []
        field_set = set()
        for field in arg_fields:
            name, value = field.split('=', 1)
            if name not in field_set:
                fields.append(field)
                field_set.add(name)

        try:
            cfg_fields = self.options('fields')
        except Error:
            cfg_fields = []

        for option in cfg_fields:
            try:
                value = self.get('fields', option)
            except Error:
                continue
            if '<insert service' in value:
                log.error("Set the service type in statsd-agent.cfg")
                continue

            if value and option not in field_set:
                fields.append("{}={}".format(option, value))
                field_set.add(option)

        if self.get_boolean('add-host-field', default=False) or arg_add_host_field and 'host' not in field_set:
            fields.append("host={}".format(socket.gethostname()))

        fields = ','.join([f.replace(',', '_').replace(' ', '_').replace('.', '-') for f in fields])
        if fields and not fields.endswith(','):
            fields = ',' + fields
        return fields


def get_nic(netiface):
    if not netiface:
        found = False
        nics = psutil.net_if_addrs()
        for n, info in nics.items():
            for addr in info:
                if addr.family == socket.AF_INET and addr.address.startswith('10.'):
                    netiface = n
                    found = True
                    break
            if found:
                break
        else:
            return

    try:
        psutil.net_io_counters(True)[netiface]
    except KeyError:
        log.error("Unknown network interface!")
        return

    return netiface


if isWindows:
    # noinspection PyUnresolvedReferences
    import win32serviceutil
    # noinspection PyUnresolvedReferences
    import win32service
    # noinspection PyUnresolvedReferences
    import win32event
    # noinspection PyUnresolvedReferences
    import servicemanager


    class StatsdAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = "StatsdAgent"
        _svc_display_name_ = "Statsd Agent Service"
        _svc_deps_ = ["EventLog"]

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)

        def log(self, msg):
            servicemanager.LogInfoMsg(str(msg))

        def SvcDoRun(self):
            self.log("Starting...")
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            cfg_file = 'C:\\statsd-agent\\statsd-agent.cfg'
            if not os.path.exists(cfg_file):
                servicemanager.LogErrorMsg('ERROR: Could not read config file at {}.'.format(cfg_file))
                self.ReportServiceStatus(win32service.SERVICE_ERROR_CRITICAL)
                self.ReportServiceStatus(win32service.SERVICE_STOPPED)
                return
            config = StatsdConfig(allow_no_value=True)
            config.read(cfg_file)
            fields = config.get_fields()
            nic = get_nic(config.get_str('nic'))
            interval, rc = config.get_int('interval', default=10) - 2, None
            host = config.get_str('host', default='localhost')
            port = config.get_int('port', default=8125)
            prefix = config.get_str('prefix', default='system')
            debug = config.get_boolean('debug', default=False)

            self.ReportServiceStatus(win32service.SERVICE_RUNNING)

            while rc != win32event.WAIT_OBJECT_0:
                try:
                    run_once(host, port, prefix, fields, nic, debug)
                except:
                    servicemanager.LogErrorMsg(traceback.format_exc())

                rc = win32event.WaitForSingleObject(self.hWaitStop, interval * 1000)

            self.log("Stopped.")
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)


def main():
    if isWindows:
        win32serviceutil.HandleCommandLine(StatsdAgentService)

    else:
        import multiprocessing

        config = StatsdConfig(allow_no_value=True)
        config.read('statsd-agent.cfg')

        parser = argparse.ArgumentParser()
        parser.add_argument('--host', '-t', type=str, default=config.get_str('host', default='localhost'),
                            help='Hostname or IP of statsd/statsite server.')
        parser.add_argument('--port', '-p', type=int, default=config.get_int('port', default=8125),
                            help='UDP port number of statsd/statsite server.')
        parser.add_argument('--prefix', '-x', type=str, default=config.get_str('prefix'),
                            help='Prefix value to add to each measurement.')
        parser.add_argument('--field', '-f', action='append', default=[],
                            help="One or more 'key=value' fields to add to each measurement.")
        parser.add_argument('--network', '--nic', '-n', type=str,
                            default=config.get_str('nic'), help='NIC to measure.')
        parser.add_argument('--interval', '-i', type=int, default=config.get_int('interval', default=10),
                            help='Time in seconds between system measurements. Must be > 2.')
        parser.add_argument('--add-host-field', '-a', action='store_true', help='Auto add host= to fields.')
        parser.add_argument('--debug', '-g', action='store_true', help="Turn on debugging.")
        parser.add_argument('--docker', '-d', action='store_true', help="Enable docker")
        parser.add_argument('--docker-addr', '-D', type=str, default=config.get_str('address', 'docker',
                                                                                    default='/var/run/docker.sock'))
        parser.add_argument('--docker-interval', '-I', type=int, default=config.get_int('interval', 'docker', default=15),
                            help='Time in seconds between docker measurements. Must be > 2.')

        args = parser.parse_args()
        docker = config.get_boolean('enabled', 'docker', default=False) or args.docker
        debug = config.get_boolean('debug', default=False) or args.debug
        prefix = args.prefix if args.prefix else ''

        if debug:
            log.debug("host={}:{}".format(args.host, args.port))
            log.debug("prefix={}".format(prefix))

        fields = config.get_fields(args.field, args.add_host_field)

        if debug:
            log.debug("fields: {}".format(fields))

        if args.interval < 3:
            log.error("Invalid system interval (< 3sec).")
            return 1

        if args.docker_interval < 3:
            log.error("Invalid docker interval (< 3sec).")
            return 1

        nic = get_nic(args.network)
        if not nic:
            log.error("Could not locate 10.x.x.x network interface!")
            return 1

        if docker:
            multiprocessing.Process(target=run_docker,
                                    args=(args.docker_addr, args.docker_interval, args.host, args.port, debug)).start()

        try:
            while True:
                start = time.time()
                run_once(args.host, args.port, prefix, fields, nic, debug)
                elapsed = time.time() - start
                log.debug("statsd: {}ms".format(int(elapsed * 1000)))
                time.sleep(args.interval - elapsed)
        except KeyboardInterrupt:
            pass

        return 0

if __name__ == '__main__':
    sys.exit(main())
