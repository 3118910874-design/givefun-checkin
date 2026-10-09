#!/usr/bin/env python
"""登录助手入口：``python login_helper.py --phone 138xxxxxxxx``。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.login import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
