#!/usr/bin/env python3

from __future__ import annotations

import os
import smtplib
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable, List

import humanize
import pytz
from dotenv import load_dotenv

# ── Configuration ────────────────────────────────────────────────────────────
load_dotenv()                                   # read .env if present

DB_PATH       = os.getenv("AO_DB", "arbitrage_opportunities.db")
TIMEZONE      = pytz.timezone(os.getenv("AO_TZ", "America/Detroit"))

EMAIL_SENDER  = os.getenv("AO_EMAIL_SENDER")
EMAIL_PASS    = os.getenv("AO_EMAIL_PASSWORD")
EMAIL_TO      = os.getenv("AO_EMAIL_RECEIVER", EMAIL_SENDER)

SMTP_SERVER   = os.getenv("AO_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("AO_SMTP_PORT", 587))

CHECK_MIN     = int(os.getenv("AO_CHECK_MINUTES", 10))
STATE         = os.getenv("AO_STATE", "mi")

MIN_PROFIT    = float(os.getenv("AO_MIN_PROFIT", 0.5))
MAX_PROFIT    = float(os.getenv("AO_MAX_PROFIT", 10.0))

# ── Helpers ──────────────────────────────────────────────────────────────────
@dataclass
class Opportunity:
    id: int
    event: str
    sport: str
    league: str
    market: str
    team1: str
    team2: str
    bet_type: str
    bookmaker1: str
    bookmaker2: str
    odds1: float
    odds2: float
    bet1: str
    bet2: str
    odds1_link: str
    odds2_link: str
    profit_margin: float
    bookmaker1_link: str
    bookmaker2_link: str
    total_line: str
    timestamp: str
    commence_time: str

    @property
    def commence_dt(self) -> datetime:
        return datetime.strptime(self.commence_time, "%Y-%m-%d %H:%M:%S%z")

    @staticmethod
    def _american(decimal_odds: float) -> int:
        return int(round((decimal_odds - 1) * 100)) if decimal_odds >= 2 else int(
            round(-100 / (decimal_odds - 1))
        )

    @property
    def roi(self) -> float:
        T = 1
        p1, p2 = 1 / self.odds1, 1 / self.odds2
        stake_1 = T * p1 / (p1 + p2)
        payout = stake_1 * self.odds1       # same as stake_2 * odds2
        return (payout - T) * 100

    def _link(self, odds_link: str, fallback: str) -> str:
        odds_link = (odds_link or "").replace("{state}", STATE)
        return odds_link or fallback

    def as_html(self) -> str:
        now = datetime.now(TIMEZONE)
        when = humanize.naturaltime(now - self.commence_dt)
        return f"""
<b>{self.sport}</b> | {self.team1} vs {self.team2} | {self.bet_type}<br>
1: <a href="{self._link(self.odds1_link, self.bookmaker1_link)}">{self.bookmaker1}</a>
   ({self.bet1} @ {self._american(self.odds1)})<br>
2: <a href="{self._link(self.odds2_link, self.bookmaker2_link)}">{self.bookmaker2}</a>
   ({self.bet2} @ {self._american(self.odds2)})<br>
ROI: {self.roi:.2f}%<br>
Start{"s" if (now-self.commence_dt).seconds < 0 else "ed"} {when} ({self.commence_dt.strftime('%I:%M %p %Z')})<br>
<hr>
"""

# ── Core functions ───────────────────────────────────────────────────────────
def fetch_opportunities() -> List[Opportunity]:
    sql = """
        SELECT *
        FROM opportunities
        WHERE profit_margin BETWEEN ? AND ?
        ORDER BY profit_margin DESC
    """
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cur:
            rows = cur.execute(sql, (MIN_PROFIT, MAX_PROFIT)).fetchall()
    return [Opportunity(**row) for row in rows]

def send_email(opps: Iterable[Opportunity]) -> None:
    opps = list(opps)
    if not opps:
        return

    msg = MIMEMultipart("alternative")
    msg["From"], msg["To"] = EMAIL_SENDER, EMAIL_TO
    msg["Subject"] = f"A.O. Alert – {len(opps)} match{'es' if len(opps) != 1 else ''}"

    html_body = "".join(o.as_html() for o in opps)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_SENDER, EMAIL_PASS)
        smtp.send_message(msg)

def run_once() -> None:
    opps = fetch_opportunities()
    if opps:
        print(f"Sending {len(opps)} opportunity(ies)…")
        send_email(opps)
    else:
        print("No opportunities in the desired profit range.")

# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    if not (EMAIL_SENDER and EMAIL_PASS):
        raise SystemExit("Set AO_EMAIL_SENDER and AO_EMAIL_PASSWORD environment variables.")

    interval = CHECK_MIN * 60
    print(f"Arbitrage notifier running every {CHECK_MIN} min "
          f"({MIN_PROFIT}% ≤ profit ≤ {MAX_PROFIT}%) – Ctrl‑C to stop")

    try:
        while True:
            run_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()

