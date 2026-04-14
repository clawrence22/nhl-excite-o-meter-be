import os
import sys
from pathlib import Path

# Ensure required env vars are present before importing app modules.
os.environ.setdefault("DB_HOST", "dummy")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "dummy")
os.environ.setdefault("DB_NAME", "dummy")
os.environ.setdefault("DB_REGION", "us-east-1")
os.environ.setdefault("DB_SSLMODE", "require")

# Ensure project root is on sys.path when tests run from subdir.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "backend"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Avoid accidental .pyc writes outside project.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
