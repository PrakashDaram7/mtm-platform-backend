"""fix_alembic_version.py — ASCII safe, no emoji."""
import sqlalchemy as sa
from app.core.database import engine

GOOD = "907432fd47a7"

with engine.begin() as conn:
    rows = conn.execute(sa.text("SELECT version_num FROM alembic_version")).fetchall()
    cur = rows[0][0] if rows else None
    print("Current: " + str(cur))
    if rows:
        conn.execute(sa.text("UPDATE alembic_version SET version_num = :v"), {"v": GOOD})
    else:
        conn.execute(sa.text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": GOOD})
    print("Done. version_num set to: " + GOOD)
