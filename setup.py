# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT
from setuptools import setup

setup(name = 'sdk-py-provider-alldata',
      version='1.2.0',
      description = 'From setup.py: The controller can be connected to one of the USB ports. The LibUSB allows the inputs to be read. ',
      author = 'SDK Team', 
      packages = ['alldataprovider', 'helper'],
      install_requires = ['ctrlx-datalayer', 'ctrlx-fbs'],
      scripts = ['main.py'],
      license = 'MIT License'
)
