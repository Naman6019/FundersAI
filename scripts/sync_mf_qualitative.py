from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath("backend"))

from app.jobs.sync_mf_qualitative_factors import main


if __name__ == "__main__":
    raise SystemExit(main())
