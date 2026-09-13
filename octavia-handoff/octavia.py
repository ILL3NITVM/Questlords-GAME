#!/usr/bin/env python3
"""Short entry point; use the project environment without shell activation."""
import os
import sys
from pathlib import Path

if __name__ == '__main__':
    env = Path(__file__).resolve().parent / 'octavia_studio' / '.venv'
    if env.exists() and Path(sys.prefix).resolve() != env.resolve():
        os.execv(str(env / 'bin/python'), [str(env / 'bin/python'), __file__] + sys.argv[1:])
    from octavia_studio.cli import main
    sys.exit(main())
