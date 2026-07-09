import sys
from pathlib import Path
import time


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler.screenlocker import lock, unlock


print("Screen lock in 1s, then unblock after 20s")
time.sleep(1)
lock()
time.sleep(20)
unlock()
print("Screen unlocked")
