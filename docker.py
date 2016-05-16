import socket
import json
from httplib import HTTPResponse
from StringIO import StringIO
from common import log


class FakeSocket(object):
    def __init__(self, response_str):
        self._file = StringIO(response_str)
    def makefile(self, *args, **kwargs):
        return self._file


def get(addr, path, debug=False):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(addr)
    client.send("GET {} HTTP/1.0\r\n\r\n".format(path))
    resp_str = client.recv(65536)
    source = FakeSocket(resp_str)
    resp = HTTPResponse(source)
    resp.begin()
    if resp.status == 200:
        text = resp.read(len(resp_str))
        data = json.loads(text)
        if debug:
            log.debug(data)
        return data

    return {}


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
