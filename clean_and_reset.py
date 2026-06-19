import os
import sys
import glob

# Kill any remaining Flask processes on Windows
os.system('taskkill /F /IM python.exe 2>nul')

# Wait a moment for processes to be killed
import time
time.sleep(2)

# Now run the reset script
os.system(f'{sys.executable} src/reset_db.py')
