import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.db import init_db, resolve_db_path


def main():
    app = create_app()
    with app.app_context():
        init_db()
        print(f"SQLite database initialized: {resolve_db_path()}")


if __name__ == "__main__":
    main()
