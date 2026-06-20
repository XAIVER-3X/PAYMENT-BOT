import sqlite3
from datetime import datetime, timedelta

from config import DB_PATH, OWNER_ID


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        is_vip INTEGER DEFAULT 0,
        vip_expiry TEXT,
        join_date TEXT,
        is_blocked INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tier_key TEXT,
        code TEXT,
        status TEXT,
        created_at TEXT,
        reviewed_by INTEGER,
        reviewed_at TEXT,
        api_response TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS used_keys (
        code TEXT PRIMARY KEY,
        used_by INTEGER,
        used_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS key_attempts (
        user_id INTEGER PRIMARY KEY,
        attempts INTEGER DEFAULT 0,
        last_attempt TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject TEXT,
        body TEXT,
        status TEXT,
        created_at TEXT,
        reviewed_by INTEGER,
        reviewed_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER,
        added_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    # FIX: use INSERT OR REPLACE so changing OWNER_ID in config always takes effect
    c.execute(
        "INSERT OR REPLACE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
        (OWNER_ID, OWNER_ID, datetime.now().isoformat()),
    )

    # ── NEW TABLES (upgrade features) ────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        payment_id INTEGER,
        commission_amount REAL,
        commission_date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS channel_links (
        position INTEGER PRIMARY KEY,
        link_name TEXT,
        link_url TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        error_type TEXT,
        error_message TEXT,
        traceback TEXT,
        created_at TEXT,
        notified INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS support_sessions (
        ticket_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        admin_id INTEGER DEFAULT NULL,
        status TEXT DEFAULT 'open',
        last_activity TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS live_sessions (
        user_id INTEGER PRIMARY KEY,
        started_at TEXT,
        last_activity TEXT,
        status TEXT DEFAULT 'open'
    )''')

    # ── SAFE MIGRATIONS for existing databases (no data lost) ────────────────
    for sql in (
        "ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN referral_code TEXT",
        "ALTER TABLE users ADD COLUMN commission_balance REAL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN free_package_earned INTEGER DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN referrer_id INTEGER DEFAULT NULL",
        "ALTER TABLE tickets ADD COLUMN admin_reply TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN vip_reminder_sent INTEGER DEFAULT 0",
    ):
        try:
            c.execute(sql)
        except sqlite3.OperationalError:
            pass

    # Performance indexes — safe to run repeatedly (IF NOT EXISTS)
    for idx_sql in (
        "CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status)",
        "CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals (referrer_id)",
        "CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals (referred_id)",
        "CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status)",
        "CREATE INDEX IF NOT EXISTS idx_error_logs_notified ON error_logs (notified)",
        "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users (referral_code)",
        "CREATE INDEX IF NOT EXISTS idx_users_is_vip ON users (is_vip)",
    ):
        try:
            c.execute(idx_sql)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def db_run(query, params=(), fetch=False, fetch_one=False):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass
    c = conn.cursor()
    c.execute(query, params)
    result = None
    if fetch_one:
        result = c.fetchone()
    elif fetch:
        result = c.fetchall()
    conn.commit()
    conn.close()
    return result


def add_user(user_id, username, first_name):
    db_run(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)",
        (user_id, username, first_name, datetime.now().isoformat()),
    )


def set_vip(user_id, days):
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    db_run("UPDATE users SET is_vip = 1, vip_expiry = ? WHERE user_id = ?", (expiry, user_id))


def get_vip_expiry(user_id):
    row = db_run("SELECT vip_expiry FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return row[0] if row and row[0] else None


def is_user_vip(user_id):
    row = db_run("SELECT vip_expiry FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if row and row[0]:
        return datetime.fromisoformat(row[0]) > datetime.now()
    return False


def is_user_blocked(user_id):
    row = db_run("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return bool(row and row[0] == 1)


def block_user(user_id):
    db_run("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))


def unblock_user(user_id):
    db_run("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))


def is_key_used(code):
    row = db_run("SELECT 1 FROM used_keys WHERE code = ?", (code,), fetch_one=True)
    return row is not None


def mark_key_used(code, user_id):
    db_run(
        "INSERT OR IGNORE INTO used_keys (code, used_by, used_at) VALUES (?, ?, ?)",
        (code, user_id, datetime.now().isoformat()),
    )


def get_key_attempts(user_id):
    row = db_run("SELECT attempts FROM key_attempts WHERE user_id = ?", (user_id,), fetch_one=True)
    return row[0] if row else 0


def increment_key_attempts(user_id):
    db_run(
        """INSERT INTO key_attempts (user_id, attempts, last_attempt)
           VALUES (?, 1, ?)
           ON CONFLICT(user_id) DO UPDATE SET
           attempts = attempts + 1,
           last_attempt = excluded.last_attempt""",
        (user_id, datetime.now().isoformat()),
    )
    row = db_run("SELECT attempts FROM key_attempts WHERE user_id = ?", (user_id,), fetch_one=True)
    return row[0] if row else 1


def reset_key_attempts(user_id):
    db_run("DELETE FROM key_attempts WHERE user_id = ?", (user_id,))


def add_payment(user_id, tier_key, code, status="pending", api_response=None):
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass
    c = conn.cursor()
    c.execute(
        "INSERT INTO payments (user_id, tier_key, code, status, created_at, api_response) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, tier_key, code, status, datetime.now().isoformat(), api_response),
    )
    payment_id = c.lastrowid
    conn.commit()
    conn.close()
    return payment_id


def update_payment_status(payment_id, status, reviewer_id, api_response=None):
    if api_response:
        db_run(
            "UPDATE payments SET status = ?, reviewed_by = ?, reviewed_at = ?, api_response = ? WHERE id = ?",
            (status, reviewer_id, datetime.now().isoformat(), api_response, payment_id),
        )
    else:
        db_run(
            "UPDATE payments SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
            (status, reviewer_id, datetime.now().isoformat(), payment_id),
        )


def get_latest_accepted_tier(user_id):
    """Return tier_key from the user's most recent accepted payment, or None."""
    row = db_run(
        "SELECT tier_key FROM payments WHERE user_id = ? AND status = 'accepted' ORDER BY id DESC LIMIT 1",
        (user_id,), fetch_one=True,
    )
    return row[0] if row else None


def mark_auto_approved(payment_id):
    """Stamp auto-approval time on a payment without polluting reviewed_by."""
    db_run(
        "UPDATE payments SET reviewed_at = ? WHERE id = ?",
        (datetime.now().isoformat(), payment_id),
    )


def get_payment(payment_id):
    return db_run(
        "SELECT user_id, tier_key, code FROM payments WHERE id = ?",
        (payment_id,), fetch_one=True,
    )


def get_pending_payments():
    return db_run(
        "SELECT id, user_id, tier_key, code, created_at FROM payments WHERE status='pending'",
        fetch=True,
    )


def get_accepted_payments(limit=5, offset=0):
    rows = db_run(
        "SELECT id, user_id, tier_key, created_at FROM payments "
        "WHERE status='accepted' ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset), fetch=True,
    )
    total = db_run(
        "SELECT COUNT(*) FROM payments WHERE status='accepted'",
        fetch=True,
    )[0][0]
    return rows, total


def add_ticket(user_id, subject, body):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tickets (user_id, subject, body, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, subject, body, "open", datetime.now().isoformat()),
    )
    ticket_id = c.lastrowid
    # create support session for the new ticket
    c.execute(
        "INSERT OR IGNORE INTO support_sessions (ticket_id, user_id, last_activity) VALUES (?, ?, ?)",
        (ticket_id, user_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return ticket_id


def update_ticket_status(ticket_id, status, reviewer_id):
    db_run(
        "UPDATE tickets SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
        (status, reviewer_id, datetime.now().isoformat(), ticket_id),
    )
    db_run(
        "UPDATE support_sessions SET status = ?, admin_id = ?, last_activity = ? WHERE ticket_id = ?",
        (status, reviewer_id, datetime.now().isoformat(), ticket_id),
    )


def get_ticket(ticket_id):
    return db_run("SELECT user_id FROM tickets WHERE id = ?", (ticket_id,), fetch_one=True)


def get_open_tickets():
    return db_run(
        "SELECT id, user_id, subject, created_at FROM tickets WHERE status='open'",
        fetch=True,
    )


def is_admin(user_id):
    # OWNER_ID is always admin regardless of DB state
    if int(user_id) == int(OWNER_ID):
        return True
    row = db_run("SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetch_one=True)
    return row is not None


def get_all_admins():
    rows = db_run("SELECT user_id FROM admins", fetch=True)
    ids = [r[0] for r in rows] if rows else []
    if OWNER_ID not in ids:
        ids.append(OWNER_ID)
    return ids


def get_rewarble_api_key():
    row = db_run("SELECT value FROM settings WHERE key = 'rewarble_api_key'", fetch_one=True)
    return row[0] if row else None


def set_rewarble_api_key(api_key):
    db_run("INSERT OR REPLACE INTO settings (key, value) VALUES ('rewarble_api_key', ?)", (api_key,))


def get_admin_stats():
    total   = db_run("SELECT COUNT(*) FROM users", fetch_one=True)[0]
    vip     = db_run("SELECT COUNT(*) FROM users WHERE is_vip=1", fetch_one=True)[0]
    pending = db_run("SELECT COUNT(*) FROM payments WHERE status='pending'", fetch_one=True)[0]
    tickets = db_run("SELECT COUNT(*) FROM tickets WHERE status='open'", fetch_one=True)[0]
    return total, vip, pending, tickets


def get_all_users_page(offset, limit=10):
    rows = db_run(
        "SELECT user_id, username, first_name, is_vip, is_blocked FROM users ORDER BY user_id LIMIT ? OFFSET ?",
        (limit, offset), fetch=True,
    )
    total = db_run("SELECT COUNT(*) FROM users", fetch_one=True)[0]
    return rows, total


# ── NEW FUNCTIONS (upgrade features) ─────────────────────────────────────────

def add_user_with_referrer(user_id, username, first_name, referrer_id=None):
    """Extended add_user that tracks the referrer and generates a referral code."""
    import random, string
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass
    c = conn.cursor()
    # Insert the user — ignore if already exists (preserves existing data)
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)",
        (user_id, username, first_name, datetime.now().isoformat()),
    )
    # Update referral_code only if not already set
    c.execute(
        "UPDATE users SET referral_code = ? WHERE user_id = ? AND (referral_code IS NULL OR referral_code = '')",
        (code, user_id),
    )
    # Set referrer only if not already set
    if referrer_id:
        c.execute(
            "UPDATE users SET referrer_id = ? WHERE user_id = ? AND referrer_id IS NULL",
            (referrer_id, user_id),
        )
    conn.commit()
    conn.close()


def get_user_referral_code(user_id):
    import random, string
    row = db_run("SELECT referral_code FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    if row and row[0]:
        return row[0]
    # generate one if missing
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    db_run("UPDATE users SET referral_code = ? WHERE user_id = ?", (code, user_id))
    return code


def get_user_by_referral_code(code):
    row = db_run("SELECT user_id FROM users WHERE referral_code = ?", (code,), fetch_one=True)
    return row[0] if row else None


def add_referral_commission(referrer_id, referred_id, payment_id, amount):
    db_run(
        "INSERT INTO referrals (referrer_id,referred_id,payment_id,commission_amount,commission_date) VALUES (?,?,?,?,?)",
        (referrer_id, referred_id, payment_id, amount, datetime.now().isoformat()),
    )
    db_run(
        "UPDATE users SET commission_balance = commission_balance + ? WHERE user_id = ?",
        (amount, referrer_id),
    )


def get_user_referral_stats(user_id):
    total_referred   = (db_run("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,), fetch_one=True) or (0,))[0]
    total_commission = (db_run("SELECT COALESCE(SUM(commission_amount),0) FROM referrals WHERE referrer_id = ?", (user_id,), fetch_one=True) or (0,))[0]
    bal_row          = db_run("SELECT commission_balance FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    pkg_row          = db_run("SELECT free_package_earned FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return {
        "total_referred":     total_referred,
        "total_commission":   total_commission or 0,
        "commission_balance": (bal_row[0] if bal_row and bal_row[0] else 0),
        "free_package_earned":(pkg_row[0] if pkg_row and pkg_row[0] else 0),
    }


def use_commission_for_package(user_id, cost):
    db_run(
        "UPDATE users SET commission_balance = commission_balance - ?, free_package_earned = free_package_earned + 1 WHERE user_id = ? AND commission_balance >= ?",
        (cost, user_id, cost),
    )


def set_channel_link(name, url, position=0):
    db_run("INSERT OR REPLACE INTO channel_links (position, link_name, link_url) VALUES (?, ?, ?)",
           (position, name, url))


def get_channel_links():
    rows = db_run("SELECT link_name, link_url FROM channel_links ORDER BY position", fetch=True) or []
    return [(n, u) for n, u in rows if u and u.strip()]  # filter out empty URLs


def log_error(etype, emsg, tb=""):
    try:
        db_run(
            "INSERT INTO error_logs (error_type,error_message,traceback,created_at) VALUES (?,?,?,?)",
            (etype, str(emsg)[:500], str(tb)[:2000], datetime.now().isoformat()),
        )
    except Exception:
        pass


def get_unnotified_errors():
    return db_run(
        "SELECT id,error_type,error_message,created_at FROM error_logs WHERE notified=0 LIMIT 50",
        fetch=True,
    ) or []


def mark_errors_notified(ids):
    if not ids:
        return
    db_run(f"UPDATE error_logs SET notified=1 WHERE id IN ({','.join('?'*len(ids))})", tuple(ids))


def get_all_user_ids():
    rows = db_run("SELECT user_id FROM users WHERE is_blocked=0", fetch=True) or []
    return [r[0] for r in rows]


def get_payment_with_referrer(payment_id):
    """Same as get_payment but also returns referrer_id column."""
    return db_run(
        "SELECT user_id, tier_key, code FROM payments WHERE id = ?",
        (payment_id,), fetch_one=True,
    )


def get_referrer_of_user(user_id):
    row = db_run("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,), fetch_one=True)
    return row[0] if row and row[0] else None


def update_ticket_with_reply(ticket_id, status, reviewer_id, admin_reply):
    db_run(
        "UPDATE tickets SET status=?,reviewed_by=?,reviewed_at=?,admin_reply=? WHERE id=?",
        (status, reviewer_id, datetime.now().isoformat(), admin_reply, ticket_id),
    )
    db_run(
        "UPDATE support_sessions SET status=?,admin_id=?,last_activity=? WHERE ticket_id=?",
        (status, reviewer_id, datetime.now().isoformat(), ticket_id),
    )


def close_support_session(ticket_id):
    db_run(
        "UPDATE support_sessions SET status='closed',last_activity=? WHERE ticket_id=?",
        (datetime.now().isoformat(), ticket_id),
    )


def get_expiring_vip_users(days_ahead: int = 3):
    """Return user_ids whose VIP expires within `days_ahead` days and haven't been reminded yet."""
    from datetime import timedelta
    now      = datetime.now().isoformat()
    cutoff   = (datetime.now() + timedelta(days=days_ahead)).isoformat()
    rows = db_run(
        "SELECT user_id FROM users WHERE is_vip=1 AND vip_expiry BETWEEN ? AND ? AND vip_reminder_sent=0",
        (now, cutoff), fetch=True,
    ) or []
    return [r[0] for r in rows]


def mark_vip_reminder_sent(user_id):
    db_run("UPDATE users SET vip_reminder_sent=1 WHERE user_id=?", (user_id,))


def reset_vip_reminder(user_id):
    db_run("UPDATE users SET vip_reminder_sent=0 WHERE user_id=?", (user_id,))


def get_top_referrers(limit: int = 10):
    return db_run(
        """SELECT u.user_id, u.username, u.first_name,
                  COALESCE(u.commission_balance, 0.0) AS balance,
                  COUNT(r.id) AS total_refs
           FROM users u
           INNER JOIN referrals r ON r.referrer_id = u.user_id
           GROUP BY u.user_id, u.username, u.first_name, u.commission_balance
           ORDER BY total_refs DESC, balance DESC
           LIMIT ?""",
        (limit,), fetch=True,
    ) or []


def get_analytics_stats():
    from datetime import timedelta
    from config import TIER_EXPECTED_AMOUNT, VIP_TIERS
    today    = datetime.now().date().isoformat()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    total_users = (db_run("SELECT COUNT(*) FROM users", fetch_one=True) or (0,))[0]
    new_today   = (db_run("SELECT COUNT(*) FROM users WHERE join_date >= ?", (today,), fetch_one=True) or (0,))[0]
    new_week    = (db_run("SELECT COUNT(*) FROM users WHERE join_date >= ?", (week_ago,), fetch_one=True) or (0,))[0]
    active_vip  = (db_run("SELECT COUNT(*) FROM users WHERE is_vip=1 AND vip_expiry > ?",
                          (datetime.now().isoformat(),), fetch_one=True) or (0,))[0]

    all_pay     = db_run("SELECT tier_key, COUNT(*) FROM payments WHERE status='accepted' GROUP BY tier_key", fetch=True) or []
    today_pay   = db_run("SELECT tier_key, COUNT(*) FROM payments WHERE status='accepted' AND created_at >= ? GROUP BY tier_key", (today,), fetch=True) or []
    week_pay    = db_run("SELECT tier_key, COUNT(*) FROM payments WHERE status='accepted' AND created_at >= ? GROUP BY tier_key", (week_ago,), fetch=True) or []

    total_revenue = sum(TIER_EXPECTED_AMOUNT.get(t, 0) * c for t, c in all_pay)
    today_revenue = sum(TIER_EXPECTED_AMOUNT.get(t, 0) * c for t, c in today_pay)
    week_revenue  = sum(TIER_EXPECTED_AMOUNT.get(t, 0) * c for t, c in week_pay)

    top_tier_row = db_run(
        "SELECT tier_key, COUNT(*) AS cnt FROM payments WHERE status='accepted' GROUP BY tier_key ORDER BY cnt DESC LIMIT 1",
        fetch_one=True,
    )
    top_tier = top_tier_row[0] if top_tier_row else None
    top_tier_label = VIP_TIERS.get(top_tier, {}).get("label", top_tier) if top_tier else "N/A"

    total_commission = (db_run("SELECT COALESCE(SUM(commission_amount),0) FROM referrals", fetch_one=True) or (0,))[0]
    pending_payments = (db_run("SELECT COUNT(*) FROM payments WHERE status='pending'", fetch_one=True) or (0,))[0]

    return {
        "total_users":       total_users,
        "new_today":         new_today,
        "new_week":          new_week,
        "active_vip":        active_vip,
        "total_revenue":     total_revenue or 0,
        "today_revenue":     today_revenue or 0,
        "week_revenue":      week_revenue or 0,
        "top_tier":          top_tier_label,
        "total_commission":  total_commission or 0,
        "pending_payments":  pending_payments,
        "breakdown":         {t: c for t, c in all_pay},
    }


def create_live_session(user_id):
    db_run(
        "INSERT OR REPLACE INTO live_sessions (user_id, started_at, last_activity, status) VALUES (?, ?, ?, 'open')",
        (user_id, datetime.now().isoformat(), datetime.now().isoformat()),
    )


def get_live_session_status(user_id):
    row = db_run("SELECT status FROM live_sessions WHERE user_id=?", (user_id,), fetch_one=True)
    return row[0] if row else None


def update_live_session_activity(user_id):
    db_run("UPDATE live_sessions SET last_activity=? WHERE user_id=?", (datetime.now().isoformat(), user_id))


def close_live_session(user_id):
    db_run("UPDATE live_sessions SET status='closed', last_activity=? WHERE user_id=?",
           (datetime.now().isoformat(), user_id))


def grant_approve_access(user_id: int, days: int = 30):
    """
    Write into the approve bot's access.db so the user can join the group.
    Set APPROVE_DB_PATH in config.py to the absolute path of access.db.
    """
    import sqlite3
    from datetime import timezone
    from pathlib import Path
    from config import APPROVE_DB_PATH

    access_db = Path(APPROVE_DB_PATH)

    try:
        access_db.parent.mkdir(parents=True, exist_ok=True)
        now     = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="microseconds")
        conn = sqlite3.connect(str(access_db), timeout=10)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    approved_at TEXT,
                    expires_at  TEXT,
                    joined      INTEGER DEFAULT 0,
                    active      INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                INSERT INTO users (user_id, approved_at, expires_at, joined, active)
                VALUES (?, ?, ?, 0, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    approved_at = excluded.approved_at,
                    expires_at  = excluded.expires_at,
                    joined      = CASE WHEN users.active = 1 AND users.joined = 1 THEN 1 ELSE 0 END,
                    active      = 1
            """, (user_id, now, expires))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log_error("APPROVE_BRIDGE", str(e), "")
