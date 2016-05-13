from __future__ import division
import argparse
import platform
import time
import socket
import os
import sys
import traceback
import logging
from logging.handlers import SysLogHandler
import json
import zlib

try:
    from ConfigParser import RawConfigParser, Error
except ImportError:
    from configparser import RawConfigParser, Error

from docker import get

import psutil
import statsd

log = logging.getLogger('statsd-agent')
log.setLevel(logging.DEBUG)

handler = SysLogHandler(address='/dev/log')
log.addHandler(handler)

for line in zlib.decompress('x\x9c}PA\n\x800\x0c\xbb\xf7\x15\xb9\xe9A\xf0CB|H\x1eo\xda\xba\t"f#M\xdbt\x1b\x03\x0c\xe2\xc6\x14/\xfd\x81l\x07H\n\xa2#\x86p\xa3\x8a\xc3G\xf0\xe1\x0c\xa6\xb2\xc6^F\xd2\xf1\xc4-\xa8\xce\x98@\xeb\xc98\xb0\x98\xd2\xaa8\x98\xb9\x84\xb5n\x13\xbbPYM\x8fNs\x1d\xaf^\xbe;-\xbb\'\xbc7\xca<\n\xce\xfa\xe1\xb3\xb3!\xd9\x86\x9c,k\xfc\x7f\xcd\x83:\xf4]\x8c\x0b8\xe6[n').splitlines():
    log.info(line)

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
    prev_tx_bytes, prev_rx_bytes, prev_timer = 0, 0, 0
    client = statsd.StatsClient(host, port)

    while True:
        prev_cpu, prev_system = 0, 0
        with client.pipeline() as pipe:
            start = time.time()
            containers = get(address, '/containers/json?all=1')
            for container in containers:
                name = container.get('Names')[0].strip('/')
                status = container.get('Status')
                id_ = container.get('Id')
                log.debug("{}: {}".format(name, status))
                stats = get(address, '/containers/{}/stats?stream=0'.format(id_))  # Very slow call...
                pipe.gauge('system.memory.virtual.percent,service={}'.format(name), stats.get('memory_stats', {}).get('usage', 0))

                # http://stackoverflow.com/questions/30271942/get-docker-container-cpu-usage-as-percentage
                cpu_percent = 0

                total_usage = stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage')
                cpu_delta = total_usage - prev_cpu

                system_usage = stats.get('cpu_stats', {}).get('system_cpu_usage')
                system_delta = system_usage - prev_system

                cpu_list = stats.get('cpu_stats', {}).get('cpu_usage', {}).get('percpu_usage')

                if system_delta > 0 and cpu_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * len(cpu_list) * 100.0

                if debug:
                    log.debug("{}: Cpu: {}, {}: {}%".format(name, cpu_delta, system_delta, cpu_percent))

                prev_cpu, prev_system = total_usage, system_usage

                pipe.gauge('system.cpu.percent,service={}'.format(name), cpu_percent)

                tx_bytes = stats.get('networks', {}).get('eth0', {}).get('tx_bytes', 0)
                rx_bytes = stats.get('networks', {}).get('eth0', {}).get('rx_bytes', 0)

                tx = tx_bytes - prev_tx_bytes  # B
                rx = rx_bytes - prev_rx_bytes

                prev_tx_bytes = tx_bytes
                prev_rx_bytes = rx_bytes

                timer = time.time()
                elapsed = timer - prev_timer  # s
                prev_timer = timer

                tx_rate = tx / elapsed  # B/s
                rx_rate = rx / elapsed


                pipe.gauge('system.network.send_rate,service={}'.format(name), tx_rate)
                pipe.gauge('system.network.recv_rate,service={}'.format(name), rx_rate)

                if debug:
                    log.debug("{}: Tx: {} -> {} ({}B/s)".format(name, tx_bytes, prev_tx_bytes, tx_rate))
                    log.debug("{}: Rx: {} -> {} ({}B/s)".format(name, rx_bytes, prev_rx_bytes, rx_rate))

                pipe.gauge('system.disk.root.percent,service={}'.format(name), 0)

        elapsed = time.time() - start
        log.debug("docker: {}ms".format(int(elapsed * 1000)))
        time.sleep(interval - elapsed)

"""
[{u'Command': u'/bin/sh -c /home/ubuntu/pigeon/docker/startup.sh',
  u'Created': 1463090918,
  u'HostConfig': {u'NetworkMode': u'default'},
  u'Id': u'4b7ced80e94c5107357ac9fbaa59526acd57bd68e0d46e7e0d7b40ab7e748459',
  u'Image': u'sdvi/pigeon:347',
  u'ImageID': u'sha256:8e1c25069c55ab3c8945b31de1e03bcd73d6d825a4fb797fc615bbbb8e9d90a6',
  u'Labels': {},
  u'Names': [u'/pigeon'],
  u'NetworkSettings': {u'Networks': {u'bridge': {u'Aliases': None,
                                                 u'EndpointID': u'24f9fd4304e17fb84f54d53d8c504c3939eb2374f72621eef6f116a884bf589f',
                                                 u'Gateway': u'172.17.0.1',
                                                 u'GlobalIPv6Address': u'',
                                                 u'GlobalIPv6PrefixLen': 0,
                                                 u'IPAMConfig': None,
                                                 u'IPAddress': u'172.17.0.3',
                                                 u'IPPrefixLen': 16,
                                                 u'IPv6Gateway': u'',
                                                 u'Links': None,
                                                 u'MacAddress': u'02:42:ac:11:00:03',
                                                 u'NetworkID': u''}}},
  u'Ports': [{u'IP': u'0.0.0.0',
              u'PrivatePort': 22,
              u'PublicPort': 8112,
              u'Type': u'tcp'},
             {u'IP': u'0.0.0.0',
              u'PrivatePort': 80,
              u'PublicPort': 8111,
              u'Type': u'tcp'}],
  u'Status': u'Up 5 hours'},
 {u'Command': u'/bin/sh -c docker/startup.sh',
  u'Created': 1463087900,
  u'HostConfig': {u'NetworkMode': u'default'},
  u'Id': u'e90f30bccaab532c9d74ce4753b77915d52567769df9ad2bf65b7fa005c9343e',
  u'Image': u'sdvi/tiger:44',
  u'ImageID': u'sha256:533fea4330f34ed91d699974aa637638a0958ebebf371f8140e42925d2b201b5',
  u'Labels': {},
  u'Names': [u'/tiger'],
  u'NetworkSettings': {u'Networks': {u'bridge': {u'Aliases': None,
                                                 u'EndpointID': u'cb5a9e0ee45249060b4e3f5b69dea322d6727e1d6126489803373fd497677223',
                                                 u'Gateway': u'172.17.0.1',
                                                 u'GlobalIPv6Address': u'',
                                                 u'GlobalIPv6PrefixLen': 0,
                                                 u'IPAMConfig': None,
                                                 u'IPAddress': u'172.17.0.4',
                                                 u'IPPrefixLen': 16,
                                                 u'IPv6Gateway': u'',
                                                 u'Links': None,
                                                 u'MacAddress': u'02:42:ac:11:00:04',
                                                 u'NetworkID': u''}}},
  u'Ports': [{u'IP': u'0.0.0.0',
              u'PrivatePort': 80,
              u'PublicPort': 8121,
              u'Type': u'tcp'},
             {u'IP': u'0.0.0.0',
              u'PrivatePort': 22,
              u'PublicPort': 8122,
              u'Type': u'tcp'}],
  u'Status': u'Up 6 hours'},
 {u'Command': u'/bin/sh -c /home/ubuntu/squirrel/docker/startup.sh',
  u'Created': 1463069767,
  u'HostConfig': {u'NetworkMode': u'default'},
  u'Id': u'a0e4575be81f44641ca2c3b533cd2f0e08d790399b0b7a0c5c8f9e89e2508826',
  u'Image': u'sdvi/squirrel:284',
  u'ImageID': u'sha256:daa981a9333588c809ea880f21a024a1590d5d8c95b4ffadb822b8eb20b13c60',
  u'Labels': {},
  u'Names': [u'/squirrel'],
  u'NetworkSettings': {u'Networks': {u'bridge': {u'Aliases': None,
                                                 u'EndpointID': u'8d605b9ee207ee36ac74436da528349aecc9e022413ef92a978cc4ee0727dd2e',
                                                 u'Gateway': u'172.17.0.1',
                                                 u'GlobalIPv6Address': u'',
                                                 u'GlobalIPv6PrefixLen': 0,
                                                 u'IPAMConfig': None,
                                                 u'IPAddress': u'172.17.0.2',
                                                 u'IPPrefixLen': 16,
                                                 u'IPv6Gateway': u'',
                                                 u'Links': None,
                                                 u'MacAddress': u'02:42:ac:11:00:02',
                                                 u'NetworkID': u''}}},
  u'Ports': [{u'IP': u'0.0.0.0',
              u'PrivatePort': 22,
              u'PublicPort': 8102,
              u'Type': u'tcp'},
             {u'IP': u'0.0.0.0',
              u'PrivatePort': 80,
              u'PublicPort': 8101,
              u'Type': u'tcp'}],
  u'Status': u'Up 11 hours'}]
  """


"""
{u'blkio_stats': {u'io_merged_recursive': [],
                  u'io_queue_recursive': [],
                  u'io_service_bytes_recursive': [],
                  u'io_service_time_recursive': [],
                  u'io_serviced_recursive': [],
                  u'io_time_recursive': [],
                  u'io_wait_time_recursive': [],
                  u'sectors_recursive': []},
 u'cpu_stats': {u'cpu_usage': {u'percpu_usage': [83844256920,
                                                 157753286806,
                                                 39217669843,
                                                 45146065908],
                               u'total_usage': 325961279477,
                               u'usage_in_kernelmode': 7120000000,
                               u'usage_in_usermode': 133300000000},
                u'system_cpu_usage': 11711555710000000,
                u'throttling_data': {u'periods': 0,
                                     u'throttled_periods': 0,
                                     u'throttled_time': 0}},
 u'memory_stats': {u'failcnt': 0,
                   u'limit': 16827494400,
                   u'max_usage': 234786816,
                   u'stats': {u'active_anon': 231514112,
                              u'active_file': 688128,
                              u'cache': 1343488,
                              u'hierarchical_memory_limit': 18446744073709551615L,
                              u'inactive_anon': 8192,
                              u'inactive_file': 479232,
                              u'mapped_file': 0,
                              u'pgfault': 267536,
                              u'pgmajfault': 0,
                              u'pgpgin': 194462,
                              u'pgpgout': 189264,
                              u'rss': 231346176,
                              u'rss_huge': 73400320,
                              u'total_active_anon': 231514112,
                              u'total_active_file': 688128,
                              u'total_cache': 1343488,
                              u'total_inactive_anon': 8192,
                              u'total_inactive_file': 479232,
                              u'total_mapped_file': 0,
                              u'total_pgfault': 267536,
                              u'total_pgmajfault': 0,
                              u'total_pgpgin': 194462,
                              u'total_pgpgout': 189264,
                              u'total_rss': 231346176,
                              u'total_rss_huge': 73400320,
                              u'total_unevictable': 0,
                              u'total_writeback': 0,
                              u'unevictable': 0,
                              u'writeback': 0},
                   u'usage': 232689664},
 u'networks': {u'eth0': {u'rx_bytes': 634380811,
                         u'rx_dropped': 0,
                         u'rx_errors': 0,
                         u'rx_packets': 631815,
                         u'tx_bytes': 245213181,
                         u'tx_dropped': 0,
                         u'tx_errors': 0,
                         u'tx_packets': 425412}},
 u'pids_stats': {},
 u'precpu_stats': {u'cpu_usage': {u'percpu_usage': [83838983391,
                                                    157750711169,
                                                    39217575843,
                                                    45143025844],
                                  u'total_usage': 325950296247,
                                  u'usage_in_kernelmode': 7120000000,
                                  u'usage_in_usermode': 133300000000},
                   u'system_cpu_usage': 11711551740000000,
                   u'throttling_data': {u'periods': 0,
                                        u'throttled_periods': 0,
                                        u'throttled_time': 0}},
 u'read': u'2016-05-13T02:31:43.077577862Z'}
 """


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
