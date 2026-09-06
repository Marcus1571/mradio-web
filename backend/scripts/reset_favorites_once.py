"""ONE-TIME script: overwrite every existing user's favorites with the
new default 12-station lineup (see stations.py's DEFAULT_STATIONS[:12]
and MEMORY.md's dated entry for why). Run once by hand, then never
again — this is NOT part of the app's normal startup or migration path,
and does not get re-run automatically on future deploys.

Only touches each user's `favorites` list — config.json (theme, volume,
provider, language) is left completely untouched.

Usage (from backend/, with the same env the app itself would use so
MRADIO_DATA_DIR resolves correctly):

    python3 -m scripts.reset_favorites_once --dry-run   # preview only
    python3 -m scripts.reset_favorites_once             # actually write
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, stations, userdata  # noqa: E402
from app.users import list_users  # noqa: E402

NEW_FAVORITES = list(stations.DEFAULT_STATIONS[: stations.MAX_FAV])


async def main(dry_run: bool) -> None:
    await db.init_db()
    try:
        users = await list_users()
        print(f"Found {len(users)} user(s).")
        print("New favorites lineup:")
        for i, s in enumerate(NEW_FAVORITES, 1):
            print(f"  {i:2}. {s['name']} ({s['genre']})")
        print()

        for u in users:
            current = await userdata.load_favorites(u["id"])
            if dry_run:
                print(f"[dry-run] user {u['id']} ({u['username']}): "
                      f"would replace {len(current)} favorite slot(s)")
                continue
            await userdata.save_favorites(u["id"], NEW_FAVORITES)
            print(f"user {u['id']} ({u['username']}): favorites overwritten")

        print()
        print("Dry run — nothing was written." if dry_run else "Done.")
    finally:
        await db.close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                         help="Preview affected users without writing anything.")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
