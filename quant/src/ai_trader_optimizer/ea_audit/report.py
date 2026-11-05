"""Reading of a MetaTrader 5 deal list (Strategy Tester report or account history), offline.

The owner exports the report from MT5 (Strategy Tester → Backtest → right click → Report → HTML, or the
"Deals" history saved as HTML/CSV) and uploads the FILE. Nothing here talks to a terminal or a broker.

Accepted inputs: HTML (UTF-16 as written by MT5, or UTF-8) or CSV/TSV, English or French headers. The deal
table is located by its HEADER (≥ the required columns), never by position. Every row that cannot be read
exactly is counted and reported — values are never guessed.

Layout assumed (MT5 « Deals / Transactions » table, documented by MetaQuotes): Time | Deal | Symbol | Type |
Direction | Volume | Price | Order | Commission | Swap | Profit | Balance | Comment. Built from the documented
layout, not yet checked against a report from the pilot trader's terminal: unknown variants are refused.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser

MAX_DEALS = 200_000

COLUMNS: dict[str, tuple[str, ...]] = {
    "time": ("time", "heure", "date", "dateheure", "temps", "opentime"),
    "deal": ("deal", "transaction", "ticket"),
    "symbol": ("symbol", "symbole", "instrument"),
    "type": ("type",),
    "direction": ("direction", "sens", "entry", "entree"),
    "volume": ("volume", "lots", "lot", "taille"),
    "price": ("price", "prix"),
    "order": ("order", "ordre"),
    "commission": ("commission", "commissions"),
    "fee": ("fee", "frais"),
    "swap": ("swap", "swaps"),
    "profit": ("profit", "benefice", "resultat", "gain", "pl"),
    "balance": ("balance", "solde"),
    "comment": ("comment", "commentaire"),
}
REQUIRED = ("time", "type", "direction", "volume", "price", "profit")

TYPES = {"buy": "buy", "achat": "buy", "sell": "sell", "vente": "sell",
         "balance": "balance", "solde": "balance", "deposit": "balance", "depot": "balance",
         "credit": "balance", "withdrawal": "balance", "retrait": "balance"}
DIRECTIONS = {"in": "in", "entree": "in", "entry": "in", "out": "out", "sortie": "out", "exit": "out",
              "outby": "out", "inout": "inout", "entreesortie": "inout", "reverse": "inout"}
TIME_FORMATS = ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y.%m.%d")


class ReportFormatError(ValueError):
    """The file does not contain a readable MT5 deal table."""


@dataclass(frozen=True)
class Deal:
    time: datetime
    seq: int  # order in the file (MT5 lists deals chronologically; ties keep file order)
    deal_id: str
    symbol: str
    kind: str  # buy | sell | balance | other
    direction: str  # in | out | inout | "" (balance)
    volume: float
    price: float
    commission: float
    swap: float
    profit: float
    balance: float | None
    comment: str

    @property
    def net(self) -> float:
        return self.profit + self.commission + self.swap


@dataclass
class ParsedReport:
    deals: list[Deal]
    source_format: str
    encoding: str
    header: list[str]
    rejected_rows: list[dict] = field(default_factory=list)
    ignored_rows: int = 0


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def _decode(raw: bytes) -> tuple[str, str]:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8-sig"
    head = raw[:4000]
    if head and head.count(b"\x00") > len(head) // 4:  # UTF-16 without BOM
        return raw.decode("utf-16-le" if head[1:2] == b"\x00" else "utf-16-be"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


class _Tables(HTMLParser):
    """Rows of every table cell by cell (``colspan`` kept so summary rows can be recognised)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, int]]] = []
        self._row: list[tuple[str, int]] | None = None
        self._cell: list[str] | None = None
        self._span = 1

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell, span = [], dict(attrs).get("colspan") or "1"
            self._span = int(span) if str(span).isdigit() else 1
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append((" ".join("".join(self._cell).split()), self._span))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _header_map(cells: list[str]) -> dict[str, int] | None:
    found: dict[str, int] = {}
    for i, c in enumerate(cells):
        n = _norm(c)
        for col, names in COLUMNS.items():
            if col not in found and n in names:
                found[col] = i
                break
    return found if all(c in found for c in REQUIRED) else None


_NUM_SPACES = re.compile(r"[\s   ']")


def parse_number(text: str, *, empty: float | None = None) -> float:
    """Exact reading of an MT5 number: spaces (incl. narrow no-break) are thousands separators, ``.`` is the
    decimal point; a single ``,`` with no ``.`` is accepted as a decimal comma. Anything else is refused."""
    t = _NUM_SPACES.sub("", text or "")
    if t in ("", "-", "—"):
        if empty is None:
            raise ValueError("valeur numérique manquante")
        return empty
    if "/" in t:  # "0.10 / 0.10" (requested / filled) in some order tables: keep the filled volume
        t = t.split("/")[-1]
    if "," in t and "." in t:
        raise ValueError(f"séparateurs ambigus : {text!r}")
    if t.count(",") == 1:
        t = t.replace(",", ".")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", t):
        raise ValueError(f"nombre illisible : {text!r}")
    v = float(t)
    if v != v or v in (float("inf"), float("-inf")):
        raise ValueError("valeur non finie")
    return v


def parse_time(text: str) -> datetime:
    t = " ".join((text or "").split())
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(t, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"date illisible : {text!r}")


def _rows_to_deals(header_cells: list[str], hmap: dict[str, int], rows: list[list[str]], fmt: str,
                   enc: str) -> ParsedReport:
    out = ParsedReport(deals=[], source_format=fmt, encoding=enc, header=header_cells)
    width = max(hmap.values()) + 1
    for n, cells in enumerate(rows):
        if len(cells) < width or not any(c.strip() for c in cells):
            out.ignored_rows += 1
            continue
        get = lambda k, c=cells: c[hmap[k]].strip() if k in hmap else ""  # noqa: E731
        try:
            kind_raw = _norm(get("type"))
            kind = TYPES.get(kind_raw)
            if kind is None:
                kind = "other"
            direction = DIRECTIONS.get(_norm(get("direction")), "")
            if kind in ("buy", "sell") and not direction:
                raise ValueError(f"sens d'opération inconnu : {get('direction')!r}")
            fees = parse_number(get("fee"), empty=0.0) if "fee" in hmap else 0.0
            deal = Deal(
                time=parse_time(get("time")), seq=n, deal_id=get("deal"), symbol=get("symbol").upper(),
                kind=kind, direction=direction if kind in ("buy", "sell") else "",
                volume=parse_number(get("volume"), empty=0.0 if kind == "balance" else None),
                price=parse_number(get("price"), empty=0.0 if kind == "balance" else None),
                commission=parse_number(get("commission"), empty=0.0) + fees,
                swap=parse_number(get("swap"), empty=0.0),
                profit=parse_number(get("profit"), empty=0.0),
                balance=parse_number(get("balance"), empty=0.0) if get("balance") else None,
                comment=get("comment")[:200])
            if deal.kind in ("buy", "sell") and (deal.volume <= 0 or deal.price <= 0):
                raise ValueError("volume ou prix non positif")
        except ValueError as exc:
            out.rejected_rows.append({"row": n + 1, "reason": str(exc), "cells": cells[:width][:14]})
            continue
        out.deals.append(deal)
        if len(out.deals) > MAX_DEALS:
            raise ReportFormatError(f"Plus de {MAX_DEALS} opérations : découpez le rapport.")
    return out


def _parse_html(text: str, enc: str) -> ParsedReport:
    p = _Tables()
    p.feed(text)
    for i, row in enumerate(p.rows):
        cells = [c for c, _ in row]
        hmap = _header_map(cells)
        if hmap is None:
            continue
        body: list[list[str]] = []
        for r in p.rows[i + 1:]:
            if any(span > 1 for _, span in r) or _header_map([c for c, _ in r]) is not None:
                if body:  # end of the deal table (section title, totals or another header)
                    break
                continue
            body.append([c for c, _ in r])
        parsed = _rows_to_deals(cells, hmap, body, "html", enc)
        if parsed.deals:
            return parsed
    raise ReportFormatError("Aucun tableau d'opérations MT5 reconnu (colonnes Heure/Time, Type, Direction, Volume, "
                            "Prix/Price, Profit attendues).")


def _parse_csv(text: str, enc: str) -> ParsedReport:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ReportFormatError("Fichier vide.")
    sample = "\n".join(lines[:20])
    delim = max([";", "\t", ","], key=lambda d: sample.count(d))
    rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
    for i, cells in enumerate(rows[:50]):
        hmap = _header_map(cells)
        if hmap is not None:
            return _rows_to_deals(cells, hmap, rows[i + 1:], "csv", enc)
    raise ReportFormatError("En-tête d'opérations introuvable dans le CSV (colonnes Heure/Time, Type, Direction, "
                            "Volume, Prix/Price, Profit attendues).")


def parse_report(raw: bytes) -> ParsedReport:
    text, enc = _decode(raw)
    if re.search(r"<\s*(table|html|tr)\b", text[:200_000], re.I):
        parsed = _parse_html(text, enc)
    else:
        parsed = _parse_csv(text, enc)
    if not parsed.deals:
        raise ReportFormatError("Aucune opération lisible dans le fichier.")
    parsed.deals.sort(key=lambda d: (d.time, d.seq))
    return parsed
