"""create books and loans

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "books",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("isbn", sa.String(20), nullable=False, unique=True),
        sa.Column("genre", sa.String(40), nullable=False, server_default="General"),
        sa.Column("shelf", sa.String(20), nullable=False, server_default="A1"),
        sa.Column("total_copies", sa.Integer, nullable=False, server_default="1"),
        sa.Column("available_copies", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("available_copies >= 0", name="ck_books_available_non_negative"),
        sa.CheckConstraint("available_copies <= total_copies", name="ck_books_available_le_total"),
    )
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("borrower", sa.String(120), nullable=False),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_loans_book_id", "loans", ["book_id"])


def downgrade():
    op.drop_index("ix_loans_book_id", table_name="loans")
    op.drop_table("loans")
    op.drop_table("books")
