import os
import sys
import time
import subprocess
import signal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sub_company_system.settings')

# Start server
proc = subprocess.Popen(
    [sys.executable, 'manage.py', 'runserver', '--noreload', '8000'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd='company_system'
)

# Wait a bit for server to start
time.sleep(4)

# Terminate
proc.terminate()
try:
    out, err = proc.communicate(timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()
    out, err = proc.communicate()

print("STDOUT:", out[-2000:] if len(out) > 2000 else out)
print("STDERR:", err[-2000:] if len(err) > 2000 else err)
print("Return code:", proc.returncode)
