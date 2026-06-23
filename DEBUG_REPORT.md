# Debug Report: `GET /api/user` returns 500 despite successful SQL query

## Symptom

Calling `GET /api/user?email=test@example.com` returned `500 Internal Server Error`
even though the SQLAlchemy query logs showed the `SELECT ... WHERE users.email = ?`
statement executing without error:

```
SELECT users.id AS users_id, users.name AS users_name, users.email AS users_email
FROM users
WHERE users.email = ?
 LIMIT ? OFFSET ?
[generated in 0.00007s] ('test@example.com', 1, 0)
INFO:     127.0.0.1:50710 - "GET /api/user?email=test%40example.com HTTP/1.1" 500 Internal Server Error
```

The FastAPI route only surfaces a generic error for any non-`NOT_FOUND` gRPC failure
(`backend/app/api/routes.py:45-48`), which hid the real exception.

## Investigation

1. Enabled `debug=True` on the `FastAPI()` app and `log_level="debug"` on uvicorn
   (`backend/app/main.py`) to get more verbose output.
2. Reproduced the request against a locally running instance of the backend
   (`PYTHONPATH=. python3 app/main.py`, then `curl /api/user?email=...`).
3. The gRPC server logged the query running but no further detail — confirming the
   exception was happening inside the gRPC service handler, not the FastAPI proxy.
4. Surfacing the underlying gRPC exception directly showed the actual cause:

   ```
   Exception calling application: (sqlite3.OperationalError) no such table: users
   [SQL: SELECT users.id AS users_id, users.name AS users_name, users.email AS users_email
   FROM users
   WHERE users.email = ?
    LIMIT ? OFFSET ?]
   ```

   This was the key finding: the `users` table genuinely doesn't exist from the
   point of view of the connection serving the request, even though `init_db()`
   had just created and seeded it moments earlier in the same process.

## Root Cause

`backend/app/db/database.py` created the engine as:

```python
engine = create_engine("sqlite:///:memory:", echo=True)
```

For SQLite, `:memory:` databases are private to the connection that created them.
SQLAlchemy's default pooling strategy for this URL is `SingletonThreadPool`, which
hands out **one connection per thread** — meaning each thread that opens a session
gets its own independent, isolated in-memory database.

Sequence of events in `run_grpc()` (`backend/app/main.py`):

1. `init_db()` runs on the gRPC process's **main thread** — creates the `users`
   table and seeds the row there.
2. `grpc.server(futures.ThreadPoolExecutor(max_workers=5))` dispatches each RPC
   (`GetUser`, `GetUserByEmail`) to a **worker thread** from the pool.
3. That worker thread is not the main thread, so `SingletonThreadPool` gives it a
   brand new, empty `:memory:` SQLite database — one with no `users` table at all.

Hence `sqlite3.OperationalError: no such table: users` whenever a request is
actually handled, despite the table existing fine on the thread that ran `init_db()`.

## Fix

Force every thread to share the *same* underlying SQLite connection by using
`StaticPool` with `check_same_thread=False` (`backend/app/db/database.py`):

```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    echo=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

`StaticPool` maintains exactly one connection for the lifetime of the engine and
hands it out to every thread, so the table and seed data created during
`init_db()` remain visible to all gRPC worker threads.

## Status

- Fix applied to `backend/app/db/database.py`.
- Not yet re-verified end-to-end — a server instance was left running on ports
  8000/50051 from earlier testing and was not restarted, since killing it required
  confirmation. Recommend restarting the backend and re-running:
  ```
  curl "http://localhost:8000/api/user?email=test@example.com"
  ```
  to confirm a `200` with the seeded user is now returned.

## Secondary observation (not fixed)

`backend/app/api/routes.py:45-48` collapses every non-`NOT_FOUND` gRPC error into
a generic `"Internal gRPC Communication Failure"` 500 with no detail, which is what
made this bug hard to see from the HTTP side. Worth logging `e.details()` /
`e.code()` server-side even if the client-facing message stays generic.
