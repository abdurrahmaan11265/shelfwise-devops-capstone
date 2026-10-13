"""ShelfWise API: a small library management service.

Books are the catalogue, loans record who has which copy. The health,
readiness and metrics endpoints exist for Kubernetes and Prometheus."""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Book, Loan
from .schemas import GENRES, BookCreate, BookOut, BookUpdate, CheckoutIn, LoanOut, Stats

app = FastAPI(title="ShelfWise API", version=settings.app_version,
              description="Library catalogue and lending API")

# /metrics in Prometheus format: request counts, latency histograms, in-progress gauge
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(
    app, include_in_schema=False)


def _get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="book not found")
    return book


@app.get("/")
def root():
    return {"service": "shelfwise-api", "library": settings.library_name,
            "version": settings.app_version, "docs": "/docs"}


@app.get("/health")
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness: only ready when the database answers."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "database unavailable"}


@app.get("/api/info")
def info():
    """Which build is serving: the image tag is the git commit SHA."""
    return {"library": settings.library_name, "version": settings.app_version}


@app.get("/api/genres")
def genres():
    return GENRES


@app.get("/api/books", response_model=list[BookOut])
def list_books(db: Session = Depends(get_db),
               q: str | None = Query(default=None, max_length=100),
               genre: str | None = None,
               available: bool | None = None):
    stmt = select(Book).order_by(Book.title)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like)))
    if genre:
        stmt = stmt.where(Book.genre == genre)
    if available is True:
        stmt = stmt.where(Book.available_copies > 0)
    elif available is False:
        stmt = stmt.where(Book.available_copies == 0)
    return db.scalars(stmt).all()


@app.get("/api/books/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    titles, total, avail = db.execute(
        select(func.count(Book.id), func.coalesce(func.sum(Book.total_copies), 0),
               func.coalesce(func.sum(Book.available_copies), 0))).one()
    open_loans = db.scalars(select(Loan).where(Loan.returned_at.is_(None))).all()
    overdue = sum(1 for l in open_loans
                  if (l.due_at if l.due_at.tzinfo else l.due_at.replace(tzinfo=timezone.utc)) < now)
    by_genre = dict(db.execute(select(Book.genre, func.count(Book.id)).group_by(Book.genre)).all())
    return Stats(titles=titles, total_copies=total, available_copies=avail,
                 on_loan=len(open_loans), overdue=overdue, by_genre=by_genre)


@app.get("/api/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return _get_book(db, book_id)


@app.post("/api/books", response_model=BookOut, status_code=201)
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    book = Book(**payload.model_dump(), available_copies=payload.total_copies)
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="a book with this ISBN already exists")
    db.refresh(book)
    return book


@app.put("/api/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, payload: BookUpdate, db: Session = Depends(get_db)):
    book = _get_book(db, book_id)
    changes = payload.model_dump(exclude_unset=True)
    if "total_copies" in changes:
        on_loan = book.total_copies - book.available_copies
        if changes["total_copies"] < on_loan:
            raise HTTPException(status_code=409,
                                detail=f"{on_loan} copies are on loan; total cannot go below that")
        book.available_copies = changes["total_copies"] - on_loan
    for k, v in changes.items():
        setattr(book, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="a book with this ISBN already exists")
    db.refresh(book)
    return book


@app.delete("/api/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = _get_book(db, book_id)
    if book.available_copies < book.total_copies:
        raise HTTPException(status_code=409, detail="cannot delete a book with copies on loan")
    db.delete(book)
    db.commit()
    return Response(status_code=204)


@app.post("/api/books/{book_id}/checkout", response_model=LoanOut, status_code=201)
def checkout(book_id: int, payload: CheckoutIn, db: Session = Depends(get_db)):
    book = _get_book(db, book_id)
    if book.available_copies < 1:
        raise HTTPException(status_code=409, detail="no copies available")
    days = payload.loan_days or settings.default_loan_days
    now = datetime.now(timezone.utc)
    loan = Loan(book_id=book.id, borrower=payload.borrower.strip(), borrowed_at=now,
                due_at=now + timedelta(days=days))
    book.available_copies -= 1
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


@app.post("/api/loans/{loan_id}/return", response_model=LoanOut)
def return_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    if loan.returned_at is not None:
        raise HTTPException(status_code=409, detail="loan already returned")
    loan.returned_at = datetime.now(timezone.utc)
    loan.book.available_copies += 1
    db.commit()
    db.refresh(loan)
    return loan


@app.get("/api/loans", response_model=list[LoanOut])
def list_loans(db: Session = Depends(get_db), open_only: bool = False,
               limit: int = Query(default=20, ge=1, le=100)):
    stmt = select(Loan).order_by(Loan.borrowed_at.desc()).limit(limit)
    if open_only:
        stmt = stmt.where(Loan.returned_at.is_(None))
    return db.scalars(stmt).all()
