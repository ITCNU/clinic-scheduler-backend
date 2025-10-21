"""make_operation_name_nullable

Revision ID: 774a11227da3
Revises: 7b1a135ca30c
Create Date: 2025-10-09 12:39:29.359038

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '774a11227da3'
down_revision = '7b1a135ca30c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind else None
    # On Postgres (and most RDBMS), we can just ALTER COLUMN
    if dialect and dialect != 'sqlite':
        op.alter_column(
            'student_schedule_operations',
            'name',
            existing_type=sa.String(length=100),
            nullable=True
        )
    else:
        # SQLite path: recreate table (original behavior)
        op.create_table('student_schedule_operations_new',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('cdt_code', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.execute(
            """
            INSERT INTO student_schedule_operations_new (id, name, description, cdt_code, created_at)
            SELECT id, name, description, cdt_code, created_at
            FROM student_schedule_operations
            """
        )
        op.drop_table('student_schedule_operations')
        op.rename_table('student_schedule_operations_new', 'student_schedule_operations')
        op.create_index(op.f('ix_student_schedule_operations_id'), 'student_schedule_operations', ['id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind else None
    if dialect and dialect != 'sqlite':
        op.alter_column(
            'student_schedule_operations',
            'name',
            existing_type=sa.String(length=100),
            nullable=False
        )
    else:
        # SQLite path
        op.create_table('student_schedule_operations_old',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('cdt_code', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.execute(
            """
            INSERT INTO student_schedule_operations_old (id, name, description, cdt_code, created_at)
            SELECT id, name, description, cdt_code, created_at
            FROM student_schedule_operations
            WHERE name IS NOT NULL
            """
        )
        op.drop_table('student_schedule_operations')
        op.rename_table('student_schedule_operations_old', 'student_schedule_operations')
        op.create_index(op.f('ix_student_schedule_operations_id'), 'student_schedule_operations', ['id'], unique=False)
