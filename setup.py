from distutils.core import setup
import py2exe
setup(console=['statsd-agent.py'],
      options={'py2exe': {'bundle_files': 1, 'compressed': False}},
      zipfile=None)
