#!/usr/bin/env python3
"""Obsolete generator — forwards to tools/check_boss_defs.py."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

print("gen_boss_defs.py is retired; running check_boss_defs.py instead.", file=sys.stderr)
runpy.run_path(str(Path(__file__).with_name("check_boss_defs.py")), run_name="__main__")
