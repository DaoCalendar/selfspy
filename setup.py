import os
import platform
from setuptools import setup


if platform.system() == 'Darwin':
    requisites = 'osx-requirements.txt'
    # needed for installing pycrypto
    os.environ["CFLAGS"] = "-I/usr/local/include -L/usr/local/lib"
elif platform.system() == "Windows":
    requisites = "win-requirements.txt"
else:
    requisites = 'requirements.txt'

with open(os.path.join(os.path.dirname(__file__), requisites)) as f:
    requires = list(f.readlines())

print('"%s"' % requires)

setup(name="selfspy",
      version='0.3.0',
      packages=['selfspy', 'selfspy.modules'],
      author="David Fendrich",
      description=''.join("""
          Log everything you do on the computer, for statistics,
          future reference and all-around fun!
      """.strip().split('\n')),
      install_requires=requires,
      entry_points=dict(console_scripts=['selfspy=selfspy.selfspy:main',
                                         'selfstats=selfspy.stats:main']))
