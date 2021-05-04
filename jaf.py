#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Shelby Spencer"
__version__ = "1.5.2"


import sys

if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 6):

    sys.stderr.write("Jenkins Attack Framework requires Python 3.6+\n")
    exit(-1)

from libs import JAF

JAF.JAF()
