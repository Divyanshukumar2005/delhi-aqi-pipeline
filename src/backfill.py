"""One-time history pull: the last BACKFILL_DAYS (90) days.

Usage: python src/backfill.py   (or python -m src.backfill)

Rate-limit budget: 8 stations x 4 pollutants x ~3 pages (2,160 hours / 1,000 per
page) is roughly 100 OpenAQ requests. At ~1 request/second that is about two
minutes and far below the free 2,000/hour limit. It reuses the daily collector,
so cleaning and de-duplication rules are identical.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in (None, ""):  # lets `python src/backfill.py` find the `src` package
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.collect import main as collect_main

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Backfilling %d days of history.", config.BACKFILL_DAYS)
    return collect_main(hours=config.BACKFILL_DAYS * 24)


if __name__ == "__main__":
    sys.exit(main())
