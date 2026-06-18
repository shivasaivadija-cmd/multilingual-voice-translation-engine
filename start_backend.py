import subprocess
import sys
import os

os.chdir("backend")
result = subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"], capture_output=False)
sys.exit(result.returncode)
