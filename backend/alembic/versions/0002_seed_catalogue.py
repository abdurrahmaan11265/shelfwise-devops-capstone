"""seed a starter catalogue so a fresh install is not an empty page

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

BOOKS = [
    ("The Phoenix Project", "Gene Kim", "978-1942788294", "Technology", "T1", 3),
    ("Site Reliability Engineering", "Betsy Beyer", "978-1491929124", "Technology", "T1", 2),
    ("Accelerate", "Nicole Forsgren", "978-1942788331", "Technology", "T2", 2),
    ("Sapiens", "Yuval Noah Harari", "978-0062316097", "History", "H1", 4),
    ("A Brief History of Time", "Stephen Hawking", "978-0553380163", "Science", "S1", 2),
    ("The Midnight Library", "Matt Haig", "978-0525559474", "Fiction", "F2", 3),
    ("Steve Jobs", "Walter Isaacson", "978-1451648539", "Biography", "B1", 1),
    ("Atomic Habits", "James Clear", "978-0735211292", "Non-fiction", "N1", 3),
]


def upgrade():
    books = sa.table("books", sa.column("title"), sa.column("author"), sa.column("isbn"),
                     sa.column("genre"), sa.column("shelf"), sa.column("total_copies"),
                     sa.column("available_copies"))
    op.bulk_insert(books, [dict(title=t, author=a, isbn=i, genre=g, shelf=s, total_copies=c,
                                available_copies=c) for t, a, i, g, s, c in BOOKS])


def downgrade():
    op.execute("DELETE FROM books WHERE isbn IN (%s)" % ",".join(f"'{b[2]}'" for b in BOOKS))
