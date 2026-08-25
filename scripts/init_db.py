#!/usr/bin/env python3
"""
SentinelRisk — Database Initialization Script

Usage:
    python scripts/init_db.py

Creates all database tables defined in the ORM models.
Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS).
"""

import sys
import os
import logging

# Add project root to path so we can import backend.app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import init_database


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("init_db")

    logger.info("Initializing SentinelRisk database...")

    try:
        init_database()
        logger.info("All tables created successfully.")
        logger.info("Database is ready.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
