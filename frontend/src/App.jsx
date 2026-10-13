import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';

const EMPTY = { title: '', author: '', isbn: '', genre: 'General', shelf: 'A1', total_copies: 1 };

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

function Kpi({ label, value, tone, hint }) {
  return (
    <div className={`kpi ${tone || ''}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value ?? '–'}</span>
      {hint && <span className="kpi-hint">{hint}</span>}
    </div>
  );
}

function BookModal({ initial, genres, onClose, onSave }) {
  const [form, setForm] = useState(initial || EMPTY);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: k === 'total_copies' ? Number(e.target.value) : e.target.value });

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const { title, author, isbn, genre, shelf, total_copies } = form;
      await onSave({ title, author, isbn, genre, shelf, total_copies });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h2>{initial ? 'Edit book' : 'Add a book'}</h2>
        <label>Title<input value={form.title} onChange={set('title')} required /></label>
        <label>Author<input value={form.author} onChange={set('author')} required /></label>
        <div className="row">
          <label>ISBN<input value={form.isbn} onChange={set('isbn')} placeholder="978-…" required /></label>
          <label>Genre
            <select value={form.genre} onChange={set('genre')}>
              {genres.map((g) => <option key={g}>{g}</option>)}
            </select>
          </label>
        </div>
        <div className="row">
          <label>Shelf<input value={form.shelf} onChange={set('shelf')} /></label>
          <label>Copies<input type="number" min="1" max="500" value={form.total_copies} onChange={set('total_copies')} /></label>
        </div>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={saving}>{saving ? 'Saving…' : 'Save book'}</button>
        </div>
      </form>
    </div>
  );
}

export default function App() {
  const [books, setBooks] = useState([]);
  const [stats, setStats] = useState(null);
  const [loans, setLoans] = useState([]);
  const [genres, setGenres] = useState(['General']);
  const [filters, setFilters] = useState({ q: '', genre: '', available: '' });
  const [modal, setModal] = useState(null);
  const [status, setStatus] = useState('loading');
  const [toast, setToast] = useState('');
  const [build, setBuild] = useState('');

  const load = useCallback(async () => {
    try {
      const [b, s, l] = await Promise.all([api.books(filters), api.stats(), api.loans()]);
      setBooks(b); setStats(s); setLoans(l); setStatus('ok');
    } catch (e) {
      setStatus('error');
    }
  }, [filters]);

  useEffect(() => {
    api.genres().then(setGenres).catch(() => {});
    api.info().then((i) => setBuild(i.version)).catch(() => {});
  }, []);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2600); };

  async function act(fn, msg) {
    try { await fn(); flash(msg); load(); } catch (e) { flash(e.message); }
  }

  async function checkout(book) {
    const borrower = window.prompt(`Who is borrowing "${book.title}"?`);
    if (borrower) act(() => api.checkout(book.id, borrower), `Checked out to ${borrower}`);
  }

  const openLoanFor = (bookId) => loans.find((l) => l.book_id === bookId && !l.returned_at);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><img src="/favicon.svg" alt="" /> ShelfWise</div>
        <nav>
          <a className="active">Catalogue</a>
          <a>Loans</a>
          <a>Members</a>
          <a>Reports</a>
        </nav>
        <div className="sidebar-foot">
          <span className={`dot ${status === 'ok' ? 'up' : status === 'error' ? 'down' : ''}`} />
          {status === 'ok' ? 'API connected' : status === 'error' ? 'API unreachable' : 'Connecting…'}
          {build && <span className="build" title={build}>build {build.slice(0, 7)}</span>}
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <h1>Catalogue</h1>
            <p className="sub">Central Library · {stats ? `${stats.titles} titles` : '…'}</p>
          </div>
          <button className="btn primary" onClick={() => setModal({})}>+ Add book</button>
        </header>

        {status === 'error' && (
          <div className="banner">The API is not responding. Check that the backend and database are running.</div>
        )}

        <section className="kpis">
          <Kpi label="Titles" value={stats?.titles} />
          <Kpi label="Copies on shelf" value={stats?.available_copies} hint={stats && `of ${stats.total_copies}`} />
          <Kpi label="On loan" value={stats?.on_loan} tone="info" />
          <Kpi label="Overdue" value={stats?.overdue} tone={stats?.overdue ? 'warn' : ''} />
        </section>

        <div className="grid">
          <section className="card">
            <div className="filters">
              <input placeholder="Search title, author or ISBN" value={filters.q}
                onChange={(e) => setFilters({ ...filters, q: e.target.value })} />
              <select value={filters.genre} onChange={(e) => setFilters({ ...filters, genre: e.target.value })}>
                <option value="">All genres</option>
                {genres.map((g) => <option key={g}>{g}</option>)}
              </select>
              <div className="seg">
                {[['', 'All'], ['true', 'Available'], ['false', 'All out']].map(([v, l]) => (
                  <button key={v} className={filters.available === v ? 'on' : ''}
                    onClick={() => setFilters({ ...filters, available: v })}>{l}</button>
                ))}
              </div>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Title</th><th>Genre</th><th>Shelf</th><th>Availability</th><th /></tr>
                </thead>
                <tbody>
                  {status === 'loading' && <tr><td colSpan="5" className="empty">Loading catalogue…</td></tr>}
                  {status === 'ok' && books.length === 0 && <tr><td colSpan="5" className="empty">No books match these filters.</td></tr>}
                  {books.map((b) => {
                    const loan = openLoanFor(b.id);
                    return (
                      <tr key={b.id}>
                        <td><div className="title">{b.title}</div><div className="muted">{b.author} · {b.isbn}</div></td>
                        <td><span className={`badge g-${b.genre.toLowerCase().replace(/[^a-z]/g, '')}`}>{b.genre}</span></td>
                        <td className="mono">{b.shelf}</td>
                        <td>
                          <div className="avail">
                            <div className="bar"><span style={{ width: `${(b.available_copies / b.total_copies) * 100}%` }} /></div>
                            <span className={b.available_copies === 0 ? 'out' : ''}>{b.available_copies}/{b.total_copies}</span>
                          </div>
                        </td>
                        <td className="actions">
                          <button className="btn sm" disabled={!b.available_copies} onClick={() => checkout(b)}>Lend</button>
                          {loan && <button className="btn sm ghost" onClick={() => act(() => api.returnLoan(loan.id), 'Returned')}>Return</button>}
                          <button className="btn sm ghost" onClick={() => setModal(b)}>Edit</button>
                          <button className="btn sm danger" onClick={() => window.confirm(`Delete "${b.title}"?`) && act(() => api.deleteBook(b.id), 'Deleted')}>Delete</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="card activity">
            <h3>Recent activity</h3>
            {loans.length === 0 && <p className="muted">No loans yet. Lend a book to see it here.</p>}
            <ul>
              {loans.map((l) => (
                <li key={l.id}>
                  <span className={`pill ${l.returned_at ? 'ret' : l.overdue ? 'late' : 'out'}`}>
                    {l.returned_at ? 'returned' : l.overdue ? 'overdue' : 'on loan'}
                  </span>
                  <div><strong>{l.borrower}</strong> · {l.book_title}</div>
                  <div className="muted">{fmtDate(l.borrowed_at)} → due {fmtDate(l.due_at)}</div>
                </li>
              ))}
            </ul>
            {stats && (
              <>
                <h3>By genre</h3>
                <div className="genres">
                  {Object.entries(stats.by_genre).map(([g, n]) => (
                    <div key={g} className="genre-row"><span>{g}</span><span className="mono">{n}</span></div>
                  ))}
                </div>
              </>
            )}
          </aside>
        </div>
      </main>

      {modal && (
        <BookModal
          initial={modal.id ? modal : null}
          genres={genres}
          onClose={() => setModal(null)}
          onSave={async (data) => {
            if (modal.id) await api.updateBook(modal.id, data); else await api.createBook(data);
            setModal(null); flash(modal.id ? 'Book updated' : 'Book added'); load();
          }}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
