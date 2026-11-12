#!/usr/bin/env python3
"""Entry point that works from any working directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zengauge.cli import main  # noqa: E402

sys.exit(main())
