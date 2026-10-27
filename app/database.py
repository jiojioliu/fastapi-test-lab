from __future__ import annotations

import json
import math
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Sequence

from .config import DATABASE_PATH
from .security import hash_password


class OrderError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    stock INTEGER NOT NULL,
    rating REAL NOT NULL,
    description TEXT NOT NULL,
    accent TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL,
    subtotal_cents INTEGER NOT NULL,
    tax_cents INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'alipay',
    payment_status TEXT NOT NULL DEFAULT 'paid',
    note TEXT,
    idempotency_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency
ON orders(user_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL
);
"""


PRODUCT_SEED = [
    ("KB-204", "Nimbus 75", "Keyboard", 8990, 184, 4.8, "75% gasket-mounted mechanical keyboard with tactile switches.", "#5eead4"),
    ("MS-118", "Orbit M2", "Mouse", 4990, 220, 4.6, "Lightweight wireless mouse with a 26K optical sensor.", "#60a5fa"),
    ("AU-310", "EchoPods", "Audio", 12900, 96, 4.7, "Hybrid noise-cancelling earbuds with multipoint Bluetooth.", "#c084fc"),
    ("DK-077", "Dockline 9", "Dock", 15900, 58, 4.5, "Nine-port USB-C dock with dual 4K display output.", "#f472b6"),
    ("MN-402", "Canvas 27", "Monitor", 269900, 31, 4.9, "27-inch 4K IPS display with 98% DCI-P3 coverage.", "#fbbf24"),
    ("CB-055", "Loop 140W", "Cable", 1690, 480, 4.4, "Braided USB-C cable rated for 140W charging.", "#34d399"),
    ("ST-210", "Pebble Stand", "Accessory", 3590, 112, 4.3, "Adjustable aluminium laptop stand with cable routing.", "#f97316"),
    ("HP-330", "Aero Studio", "Audio", 69900, 42, 4.8, "Open-back studio headphones with replaceable ear pads.", "#38bdf8"),
    ("KB-300", "Tide 65", "Keyboard", 11900, 68, 4.9, "Aluminium 65% keyboard with hot-swappable switches.", "#a3e635"),
    ("MS-201", "Vector Pro", "Mouse", 7900, 143, 4.7, "Ergonomic vertical mouse with configurable shortcuts.", "#fb7185"),
    ("DK-010", "Base Hub", "Dock", 5490, 205, 4.2, "Compact seven-port hub for hybrid work setups.", "#818cf8"),
    ("AC-808", "Desk Grid", "Accessory", 2290, 330, 4.1, "Modular magnetic cable management grid.", "#2dd4bf"),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _seed_users(conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    users = [
        ("admin", "admin123", "Lab Administrator", "admin"),
        ("customer", "customer123", "Standard User", "customer"),
        ("guest", secrets.token_urlsafe(32), "Guest User", "guest"),
    ]
    for username, password, display, role in users:
        if conn.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone():
            continue
        conn.execute(
            """
            INSERT INTO users (username, password_hash, display_name, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, hash_password(password), display, role, now),
        )


def _seed_products(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count:
        return
    now = utc_now_iso()
    conn.executemany(
        """
        INSERT INTO products
            (sku, name, category, price_cents, stock, rating, description, accent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*product, now) for product in PRODUCT_SEED],
    )


def _seed_order(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    username: str,
    sku: str,
    note: str,
    payment_method: str,
) -> None:
    if conn.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,)).fetchone():
        return
    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    product = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
    if not user or not product:
        return
    now = utc_now_iso()
    subtotal = int(product["price_cents"])
    tax = round(subtotal * 0.06)
    conn.execute(
        """
        INSERT INTO orders
            (id, user_id, status, subtotal_cents, tax_cents, total_cents,
             payment_method, payment_status, note, created_at, updated_at)
        VALUES (?, ?, 'completed', ?, ?, ?, ?, 'paid', ?, ?, ?)
        """,
        (
            order_id,
            user["id"],
            subtotal,
            tax,
            subtotal + tax,
            payment_method,
            note,
            now,
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO order_items
            (order_id, product_id, product_name, unit_price_cents, quantity)
        VALUES (?, ?, ?, ?, 1)
        """,
        (order_id, product["id"], product["name"], product["price_cents"]),
    )


def _seed_orders(conn: sqlite3.Connection) -> None:
    _seed_order(
        conn,
        order_id="ORD-SEED-ADMIN-0001",
        username="admin",
        sku="KB-204",
        note="Seed order for the administrator test account",
        payment_method="alipay",
    )
    _seed_order(
        conn,
        order_id="ORD-SEED-CUSTOMER-0001",
        username="customer",
        sku="MS-118",
        note="Seed order for the isolated standard user",
        payment_method="wechat",
    )


def _apply_migrations(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(orders)").fetchall()
    }
    if "payment_method" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'alipay'"
        )
    if "payment_status" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'paid'"
        )
    tester = conn.execute(
        "SELECT id FROM users WHERE username = 'tester' COLLATE NOCASE"
    ).fetchone()
    if tester:
        conn.execute(
            """
            DELETE FROM order_items
            WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)
            """,
            (tester["id"],),
        )
        conn.execute("DELETE FROM orders WHERE user_id = ?", (tester["id"],))
        conn.execute("DELETE FROM users WHERE id = ?", (tester["id"],))


def init_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        _apply_migrations(conn)
        _seed_users(conn)
        _seed_products(conn)
        _seed_orders(conn)


def reset_database() -> None:
    with connection() as conn:
        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM sqlite_sequence")
        _seed_users(conn)
        _seed_products(conn)
        _seed_orders(conn)


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(
    username: str, password: str, display_name: str | None
) -> sqlite3.Row:
    now = utc_now_iso()
    try:
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO users
                    (username, password_hash, display_name, role, created_at)
                VALUES (?, ?, ?, 'customer', ?)
                """,
                (
                    username,
                    hash_password(password),
                    display_name or username,
                    now,
                ),
            )
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise OrderError(409, "That username is already registered") from exc


def _product_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["price"] = round(data.pop("price_cents") / 100, 2)
    return data


def list_products(
    search: str | None,
    category: str | None,
    sort: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if search:
        clauses.append("(name LIKE ? OR sku LIKE ? OR description LIKE ?)")
        term = f"%{search.strip()}%"
        values.extend([term, term, term])
    if category:
        clauses.append("category = ?")
        values.append(category)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_by = {
        "name": "name ASC",
        "price_asc": "price_cents ASC",
        "price_desc": "price_cents DESC",
        "rating": "rating DESC",
        "newest": "id DESC",
    }.get(sort, "id ASC")
    offset = (page - 1) * page_size
    with connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM products {where}", values
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM products {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            [*values, page_size, offset],
        ).fetchall()
        categories = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT category FROM products ORDER BY category"
            ).fetchall()
        ]
    return {
        "items": [_product_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
        "categories": categories,
    }


def get_product(product_id: int) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return _product_dict(row) if row else None


def _order_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    item_rows = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (row["id"],)
    ).fetchall()
    username = conn.execute(
        "SELECT username FROM users WHERE id = ?", (row["user_id"],)
    ).fetchone()[0]
    subtotal = row["subtotal_cents"] / 100
    tax = row["tax_cents"] / 100
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "username": username,
        "status": row["status"],
        "items": [
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "unit_price": round(item["unit_price_cents"] / 100, 2),
                "quantity": item["quantity"],
                "line_total": round(
                    item["unit_price_cents"] * item["quantity"] / 100, 2
                ),
            }
            for item in item_rows
        ],
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(row["total_cents"] / 100, 2),
        "payment_method": row["payment_method"],
        "payment_status": row["payment_status"],
        "note": row["note"],
        "idempotency_key": row["idempotency_key"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_order(order_id: str, user_id: int, is_admin: bool) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row or (not is_admin and row["user_id"] != user_id):
            return None
        return _order_dict(conn, row)


def create_order(
    user_id: int,
    items: Sequence[dict[str, int]],
    note: str | None,
    idempotency_key: str | None,
    payment_method: str,
) -> tuple[dict[str, Any], bool]:
    now = utc_now_iso()
    safe_key = idempotency_key.strip()[:128] if idempotency_key else None
    with connection() as conn:
        if safe_key:
            existing = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? AND idempotency_key = ?",
                (user_id, safe_key),
            ).fetchone()
            if existing:
                return _order_dict(conn, existing), False

        product_rows: dict[int, sqlite3.Row] = {}
        subtotal_cents = 0
        for item in items:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
            row = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if row is None:
                raise OrderError(404, f"Product {product_id} was not found")
            if row["stock"] < quantity:
                raise OrderError(
                    409,
                    f"Insufficient stock for {row['name']}: {row['stock']} available",
                )
            product_rows[product_id] = row
            subtotal_cents += row["price_cents"] * quantity

        tax_cents = round(subtotal_cents * 0.06)
        order_id = (
            "ORD-"
            + datetime.now(timezone.utc).strftime("%Y%m%d")
            + "-"
            + uuid.uuid4().hex[:8].upper()
        )
        try:
            conn.execute(
                """
                INSERT INTO orders
                    (id, user_id, status, subtotal_cents, tax_cents, total_cents,
                     payment_method, payment_status, note, idempotency_key,
                     created_at, updated_at)
                VALUES (?, ?, 'confirmed', ?, ?, ?, ?, 'paid', ?, ?, ?, ?)
                """,
                (
                    order_id,
                    user_id,
                    subtotal_cents,
                    tax_cents,
                    subtotal_cents + tax_cents,
                    payment_method,
                    note,
                    safe_key,
                    now,
                    now,
                ),
            )
        except sqlite3.IntegrityError:
            existing = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? AND idempotency_key = ?",
                (user_id, safe_key),
            ).fetchone()
            if existing:
                return _order_dict(conn, existing), False
            raise

        for item in items:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
            product = product_rows[product_id]
            changed = conn.execute(
                """
                UPDATE products SET stock = stock - ?
                WHERE id = ? AND stock >= ?
                """,
                (quantity, product_id, quantity),
            )
            if changed.rowcount != 1:
                raise OrderError(
                    409, f"Insufficient stock for {product['name']}"
                )
            conn.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, product_name, unit_price_cents, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    product_id,
                    product["name"],
                    product["price_cents"],
                    quantity,
                ),
            )
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _order_dict(conn, row), True


def list_orders(
    user_id: int,
    is_admin: bool,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if not is_admin:
        clauses.append("user_id = ?")
        values.append(user_id)
    if status:
        clauses.append("status = ?")
        values.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = (page - 1) * page_size
    with connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM orders {where}", values
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM orders {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*values, page_size, offset],
        ).fetchall()
        items = [_order_dict(conn, row) for row in rows]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


def update_order_status(order_id: str, status: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status, utc_now_iso(), order_id),
        )
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _order_dict(conn, row)

