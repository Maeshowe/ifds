"""Global test configuration — shared fixtures and environment setup."""

import os


# Disable trading day guard in all tests (production guard exits on NYSE holidays)
os.environ["IFDS_SKIP_TRADING_DAY_GUARD"] = "1"
