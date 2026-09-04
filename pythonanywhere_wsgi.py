# WSGI file used on PythonAnywhere (account InternMatch).
# Web tab → WSGI configuration file.

import glob
import os
import sys

project_home = "/home/InternMatch/internmatch"
packages = glob.glob(project_home + "/venv/lib/python*/site-packages")
for path in packages + [project_home]:
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(project_home)

env_path = os.path.join(project_home, ".env")
if os.path.isfile(env_path):
    with open(env_path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from app import app as application
