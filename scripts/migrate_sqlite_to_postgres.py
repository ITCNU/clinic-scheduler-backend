"""
One-off migration script: copy data from local SQLite (clinic_scheduler.db)
to the Postgres database configured in .env (DATABASE_URL).

Usage:
  1) Ensure .env points to Postgres (DATABASE_URL).
  2) Activate venv, run:
       python scripts/migrate_sqlite_to_postgres.py
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# Ensure project root is in sys.path so `app` imports work when run as a script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env to get Postgres URL for destination
load_dotenv()

SQLITE_URL = "sqlite:///./clinic_scheduler.db"
POSTGRES_URL = os.getenv("DATABASE_URL")
if not POSTGRES_URL:
    raise SystemExit("DATABASE_URL not set in environment/.env")

# Import models
from app.models.user import User
from app.models.student_schedule import (
    StudentSchedule,
    StudentPair,
    OperationSchedule,
    ScheduleWeekSchedule,
    ScheduleAssignment,
    OperationTracking,
)


def open_session(url: str):
    eng = create_engine(url, pool_pre_ping=True)
    return sessionmaker(bind=eng, autoflush=False, autocommit=False)(), eng


def copy_table(src_sess, dst_sess, model, order_by=None, transform=None):
    q = src_sess.query(model)
    if order_by is not None:
        q = q.order_by(order_by)
    rows = q.all()
    for row in rows:
        data = {c.name: getattr(row, c.name) for c in model.__table__.columns}
        if transform:
            data = transform(data)
        dst_sess.add(model(**data))
    dst_sess.commit()
    print(f"Copied {len(rows)} rows -> {model.__tablename__}")


def copy_operations_with_dedup(src_sess, dst_sess):
    """Copy OperationSchedule rows, deduplicating by unique name.
    Returns a mapping of {src_id: dst_id} to rewrite foreign keys.
    """
    name_to_dest = {op.name: op.id for op in dst_sess.query(OperationSchedule).all() if op.name}
    id_map = {}
    rows = src_sess.query(OperationSchedule).order_by(OperationSchedule.id).all()
    for row in rows:
        src_id = row.id
        if row.name and row.name in name_to_dest:
            # Already exists; map to existing ID
            id_map[src_id] = name_to_dest[row.name]
            continue
        # Create new operation without forcing ID to avoid PK conflicts
        new_op = OperationSchedule(
            name=row.name,
            description=row.description,
            cdt_code=row.cdt_code,
            created_at=row.created_at,
        )
        dst_sess.add(new_op)
        dst_sess.flush()  # get generated id
        id_map[src_id] = new_op.id
        if row.name:
            name_to_dest[row.name] = new_op.id
    dst_sess.commit()
    print(f"Copied/merged {len(rows)} operations -> {OperationSchedule.__tablename__}")
    return id_map


def copy_users_merge_on_username(src_sess, dst_sess):
    """Copy users, merging on unique username to avoid PK/unique conflicts.
    Existing users are left as-is; new ones are inserted letting Postgres assign IDs.
    """
    dest_by_username = {u.username: u for u in dst_sess.query(User).all()}
    rows = src_sess.query(User).order_by(User.id).all()
    inserted = 0
    skipped = 0
    for row in rows:
        if row.username in dest_by_username:
            skipped += 1
            continue
        new_u = User(
            username=row.username,
            email=row.email,
            password_hash=row.password_hash,
            role=row.role,
            first_name=row.first_name,
            last_name=row.last_name,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        dst_sess.add(new_u)
        inserted += 1
    dst_sess.commit()
    print(f"Users: inserted {inserted}, skipped {skipped} (by username)")


def purge_destination(dst_sess):
    """Dangerous: wipe destination tables to avoid unique conflicts on fresh import.
    Use when the Postgres DB doesn’t need to keep existing app data.
    """
    tables = [
        'operation_tracking',
        'schedule_assignments',
        'student_pairs',
        'student_schedule_weeks',
        'student_schedule_operations',
        'student_schedule_students',
        'users',
    ]
    for tbl in tables:
        dst_sess.execute(text(f'TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE;'))
    dst_sess.commit()
    print("Destination truncated (RESTART IDENTITY CASCADE)")


def main():
    src, src_eng = open_session(SQLITE_URL)
    dst, dst_eng = open_session(POSTGRES_URL)

    try:
        # If this is a fresh import and you've already populated some rows,
        # uncomment the next line to wipe destination before copying:
        purge_destination(dst)

        # Order matters: base tables before FK dependents
        copy_users_merge_on_username(src, dst)
        copy_table(src, dst, StudentSchedule, order_by=StudentSchedule.id)
        copy_table(src, dst, ScheduleWeekSchedule, order_by=ScheduleWeekSchedule.id)

        # Operations: deduplicate by name and build id map
        op_id_map = copy_operations_with_dedup(src, dst)

        copy_table(src, dst, StudentPair, order_by=StudentPair.id)

        # Rewrite foreign keys to new operation IDs where necessary
        copy_table(
            src,
            dst,
            ScheduleAssignment,
            order_by=ScheduleAssignment.id,
            transform=lambda d: {**d, 'operation_id': op_id_map.get(d.get('operation_id'), d.get('operation_id'))},
        )
        copy_table(
            src,
            dst,
            OperationTracking,
            order_by=OperationTracking.id,
            transform=lambda d: {**d, 'operation_id': op_id_map.get(d.get('operation_id'), d.get('operation_id'))},
        )
    finally:
        src.close()
        dst.close()
        src_eng.dispose()
        dst_eng.dispose()


if __name__ == "__main__":
    main()


