from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

GENRES = ["Fiction", "Non-fiction", "Technology", "Science", "History", "Biography", "General"]


class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=10, max_length=20, pattern=r"^[0-9Xx-]+$")
    genre: str = Field(default="General", max_length=40)
    shelf: str = Field(default="A1", max_length=20)
    total_copies: int = Field(default=1, ge=1, le=500)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    isbn: str | None = Field(default=None, min_length=10, max_length=20, pattern=r"^[0-9Xx-]+$")
    genre: str | None = Field(default=None, max_length=40)
    shelf: str | None = Field(default=None, max_length=20)
    total_copies: int | None = Field(default=None, ge=1, le=500)


class BookOut(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    available_copies: int
    created_at: datetime
    updated_at: datetime


class CheckoutIn(BaseModel):
    borrower: str = Field(min_length=2, max_length=120)
    loan_days: int | None = Field(default=None, ge=1, le=90)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    book_title: str
    borrower: str
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    overdue: bool

    @model_validator(mode="before")
    @classmethod
    def from_orm_loan(cls, v):
        if hasattr(v, "book"):
            from datetime import timezone
            now = datetime.now(timezone.utc)
            due = v.due_at if v.due_at.tzinfo else v.due_at.replace(tzinfo=timezone.utc)
            return {
                "id": v.id, "book_id": v.book_id, "book_title": v.book.title,
                "borrower": v.borrower, "borrowed_at": v.borrowed_at, "due_at": v.due_at,
                "returned_at": v.returned_at, "overdue": v.returned_at is None and due < now,
            }
        return v


class Stats(BaseModel):
    titles: int
    total_copies: int
    available_copies: int
    on_loan: int
    overdue: int
    by_genre: dict[str, int]
