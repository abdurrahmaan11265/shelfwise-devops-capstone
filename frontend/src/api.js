async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => `${d.loc?.at(-1)}: ${d.msg}`).join(', ')
      : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

export const api = {
  books: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null));
    return request(`/books${qs.toString() ? `?${qs}` : ''}`);
  },
  stats: () => request('/books/stats'),
  genres: () => request('/genres'),
  loans: () => request('/loans?limit=12'),
  createBook: (data) => request('/books', { method: 'POST', body: JSON.stringify(data) }),
  updateBook: (id, data) => request(`/books/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteBook: (id) => request(`/books/${id}`, { method: 'DELETE' }),
  checkout: (id, borrower) =>
    request(`/books/${id}/checkout`, { method: 'POST', body: JSON.stringify({ borrower }) }),
  returnLoan: (id) => request(`/loans/${id}/return`, { method: 'POST' }),
};
