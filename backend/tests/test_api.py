def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_checks_database(client):
    assert client.get("/ready").json()["status"] == "ready"


def test_create_and_get_book(client, book):
    assert book["available_copies"] == 2
    r = client.get(f"/api/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "The Pragmatic Programmer"


def test_duplicate_isbn_rejected(client, book):
    r = client.post("/api/books", json={"title": "Copy", "author": "X", "isbn": book["isbn"]})
    assert r.status_code == 409


def test_list_and_search_books(client, book):
    client.post("/api/books", json={"title": "Sapiens", "author": "Harari", "isbn": "978-0062316097",
                                    "genre": "History"})
    assert len(client.get("/api/books").json()) == 2
    found = client.get("/api/books", params={"q": "pragmatic"}).json()
    assert [b["title"] for b in found] == ["The Pragmatic Programmer"]
    assert len(client.get("/api/books", params={"genre": "History"}).json()) == 1


def test_update_book(client, book):
    r = client.put(f"/api/books/{book['id']}", json={"shelf": "T3", "total_copies": 5})
    assert r.status_code == 200
    assert r.json()["shelf"] == "T3"
    assert r.json()["available_copies"] == 5


def test_delete_book(client, book):
    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


def test_validation_error(client):
    r = client.post("/api/books", json={"title": "", "author": "A", "isbn": "bad"})
    assert r.status_code == 422


def test_checkout_return_and_stats(client, book):
    loan = client.post(f"/api/books/{book['id']}/checkout", json={"borrower": "Ayesha"}).json()
    assert client.get(f"/api/books/{book['id']}").json()["available_copies"] == 1
    s = client.get("/api/books/stats").json()
    assert s["on_loan"] == 1 and s["titles"] == 1
    # a book with copies on loan cannot be deleted
    assert client.delete(f"/api/books/{book['id']}").status_code == 409
    assert client.post(f"/api/loans/{loan['id']}/return").status_code == 200
    assert client.post(f"/api/loans/{loan['id']}/return").status_code == 409
    assert client.get(f"/api/books/{book['id']}").json()["available_copies"] == 2


def test_no_copies_left(client, book):
    for name in ["A1", "B2"]:
        assert client.post(f"/api/books/{book['id']}/checkout", json={"borrower": name}).status_code == 201
    assert client.post(f"/api/books/{book['id']}/checkout", json={"borrower": "C3"}).status_code == 409


def test_metrics_endpoint(client, book):
    client.get("/api/books")
    body = client.get("/metrics").text
    assert "http_requests_total" in body
