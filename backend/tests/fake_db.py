"""An in-memory stand-in for the Supabase client.

It supports only the query shapes app/projects/service.py actually uses, which is
enough to exercise every endpoint without a live database.
"""

import itertools
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# Postgres gives every insert a distinct now(); mirror that so ordering is never a tie.
_tick = itertools.count()

DEFAULT_TIMESTAMPS = {
    "projects": "created_at",
    "agent_runs": "started_at",
    "evidence": "created_at",
    "findings": "created_at",
    "actions": "created_at",
}


class Result:
    def __init__(self, data: list[dict]):
        self.data = data


class Query:
    def __init__(self, rows: list[dict], operation: str, payload: Any = None):
        self._rows = rows
        self._operation = operation
        self._payload = payload
        self._filters: list = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None

    def select(self, *_columns: str) -> "Query":
        return self

    def eq(self, column: str, value: Any) -> "Query":
        self._filters.append(lambda row: row.get(column) == value)
        return self

    def in_(self, column: str, values: list) -> "Query":
        self._filters.append(lambda row: row.get(column) in values)
        return self

    def order(self, column: str, desc: bool = False) -> "Query":
        self._order = (column, desc)
        return self

    def limit(self, count: int) -> "Query":
        self._limit = count
        return self

    def execute(self) -> Result:
        if self._operation == "insert":
            return Result(self._payload)

        matched = [row for row in self._rows if all(keep(row) for keep in self._filters)]

        if self._operation == "update":
            for row in matched:
                row.update(self._payload)
            return Result(matched)

        if self._operation == "delete":
            for row in matched:
                self._rows.remove(row)
            return Result(matched)

        if self._order:
            column, desc = self._order
            matched = sorted(matched, key=lambda row: row.get(column) or "", reverse=desc)
        if self._limit is not None:
            matched = matched[: self._limit]
        return Result([dict(row) for row in matched])


class Table:
    def __init__(self, name: str, rows: list[dict]):
        self._name = name
        self._rows = rows

    def select(self, *columns: str) -> Query:
        return Query(self._rows, "select").select(*columns)

    def insert(self, payload: dict | list[dict]) -> Query:
        records = payload if isinstance(payload, list) else [payload]
        inserted = [self._with_defaults(record) for record in records]
        self._rows.extend(inserted)
        return Query(self._rows, "insert", [dict(record) for record in inserted])

    def update(self, payload: dict) -> Query:
        return Query(self._rows, "update", payload)

    def delete(self) -> Query:
        return Query(self._rows, "delete")

    def upsert(self, payload: dict, on_conflict: str | None = None) -> Query:
        """Good enough for the one real upsert in the app: match on `on_conflict`'s
        columns, update the row if one matches, otherwise insert a new one."""
        keys = (on_conflict or "id").split(",")
        match = next(
            (row for row in self._rows if all(row.get(key) == payload.get(key) for key in keys)),
            None,
        )
        if match is not None:
            match.update(payload)
            return Query(self._rows, "insert", [dict(match)])

        inserted = self._with_defaults(payload)
        self._rows.append(inserted)
        return Query(self._rows, "insert", [dict(inserted)])

    def _with_defaults(self, record: dict) -> dict:
        row = {"id": str(uuid.uuid4()), **record}
        timestamp_column = DEFAULT_TIMESTAMPS.get(self._name)
        if timestamp_column and timestamp_column not in row:
            moment = datetime.now(timezone.utc) + timedelta(microseconds=next(_tick))
            row[timestamp_column] = moment.isoformat()
        return row


class FakeUser:
    def __init__(self, id: str, email: str | None = None):
        self.id = id
        self.email = email


class FakeAuthResponse:
    def __init__(self, user: FakeUser | None):
        self.user = user


class FakeAuth:
    """Maps a bearer token to a user, the way Supabase's auth.get_user(token) does."""

    def __init__(self) -> None:
        self.users: dict[str, FakeUser] = {}

    def get_user(self, token: str) -> FakeAuthResponse:
        return FakeAuthResponse(self.users.get(token))


class FakeDatabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}
        self.auth = FakeAuth()

    def table(self, name: str) -> Table:
        return Table(name, self.tables.setdefault(name, []))
