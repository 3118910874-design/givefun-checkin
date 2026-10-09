#!/usr/bin/env python
"""每日领取入口：``python checkin.py`` / ``python checkin.py --dry-run``。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.daily import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
