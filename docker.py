import socket
import json
from httplib import HTTPResponse
from StringIO import StringIO


class FakeSocket(object):
    def __init__(self, response_str):
        self._file = StringIO(response_str)
    def makefile(self, *args, **kwargs):
        return self._file


def get(addr, path):
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
        return data

    return {}
