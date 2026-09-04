# Copy this into the PythonAnywhere WSGI file (Web tab → WSGI configuration).
# Replace YOUR_USERNAME with your PythonAnywhere username.

import os
import sys

from dotenv import load_dotenv

project_home = "/home/YOUR_USERNAME/internmatch"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)
load_dotenv(os.path.join(project_home, ".env"))

from app import app as application
