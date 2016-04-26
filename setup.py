from distutils.core import setup
import py2exe
import sys

# If run without args, build executables, in quiet mode.
if len(sys.argv) == 1:
    sys.argv.append("py2exe")
    sys.argv.append("-q")

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.version = "0.1.0"
        self.company_name = "SDVI"
        self.copyright = "(c) 2016 SDVI Corp."
        self.name = "statsd-agent"

statsd_agent = Target(
    # used for the versioninfo resource
    description="statsd-agent Windows Service",
    # what to build.  For a service, the module name (not the filename) must be specified!
    modules=["statsd-agent"],
    cmdline_style='pywin32'
    )

excludes = ["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
            "pywin.dialogs", "pywin.dialogs.list", 'Carbon', 'Carbon.Files', 'ElementC14N', '_psutil_linux',
            '_sysconfigdata', 'configparser', 'enum', 'psutil._psutil_bsd', 'psutil._psutil_osx',
            'psutil._psutil_posix', 'psutil._psutil_sunos', 'winreg']

setup(
    options={"py2exe": { # create a compressed zip archive
                          "compressed": 1,
                          "optimize": 2,
                          "excludes": excludes}},
    # The lib directory contains everything except the executables and the python dll.
    # Can include a subdirectory name.
    zipfile="lib/shared.zip",
    service=[statsd_agent],
)
