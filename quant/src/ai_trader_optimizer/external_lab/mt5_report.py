"""Reading of MetaTrader 5 Strategy Tester reports as UNTRUSTED DATA (HTML, XLSX, CSV, ZIP of those).

Every format is first turned into a GRID (rows of cell texts); the same extractors then read
1. the metadata block ("Expert:", "Symbol:", "Period:", …, label in one cell, value in the next non-empty one),
2. the robot's input parameters ("Inputs:" followed by ``name=value`` cells),
3. the MT5 summary figures ("Total Net Profit:", "Profit Factor:", …) — kept as REPORTED, never as computed,
4. the Orders table and the Deals table, located by their header rows.

Safety: no macro, script, formula or external entity is ever evaluated. XLSX = ZIP of XML read with the standard
library; a DOCTYPE/ENTITY declaration is refused. ZIP archives: one level, bounded member count, sizes and
compression ratio, no absolute / parent paths, no symlinks. Nothing is written by this module.
"""

from __future__ import annotations

import csv
import io
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import datetime

from ..ea_audit.report import (
    COLUMNS as DEAL_COLUMNS,
)
from ..ea_audit.report import (
    DIRECTIONS,
    TYPES,
    Deal,
    ReportFormatError,
    _decode,
    _norm,
    _Tables,
    parse_number,
    parse_time,
)

PARSER_VERSION = "mt5-report/1"
MAX_ARCHIVE_MEMBERS = 20
MAX_MEMBER_BYTES = 60 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 120 * 1024 * 1024
MAX_RATIO = 200
MAX_ROWS = 400_000
REPORT_EXT = (".htm", ".html", ".xlsx", ".csv")

ORDER_COLUMNS: dict[str, tuple[str, ...]] = {
    "open_time": ("opentime", "heuredouverture", "ouverture"),
    "order": ("order", "ordre", "orderid", "ticket"),
    "symbol": ("symbol", "symbole"),
    "type": ("type",),
    "volume": ("volume",),
    "price": ("price", "prix"),
    "sl": ("sl",),
    "tp": ("tp",),
    "time": ("time", "heure", "executiontime"),
    "state": ("state", "etat", "statut"),
    "comment": ("comment", "commentaire"),
}
ORDER_REQUIRED = ("order", "type", "volume", "state")
DEALS = {**DEAL_COLUMNS, "deal": DEAL_COLUMNS["deal"] + ("dealid",), "order": DEAL_COLUMNS["order"] + ("orderid",),
         "position": ("position", "positionid")}
DEAL_REQUIRED = ("time", "type", "direction", "volume", "price", "profit")

# summary labels (normalised) -> key. Values stay strings + parsed numbers when unambiguous.
SUMMARY = {
    "totalnetprofit": "net_profit", "grossprofit": "gross_profit", "grossloss": "gross_loss",
    "profitfactor": "profit_factor", "expectedpayoff": "expected_payoff", "recoveryfactor": "recovery_factor",
    "sharperatio": "sharpe_ratio", "balancedrawdownabsolute": "balance_dd_absolute",
    "balancedrawdownmaximal": "balance_dd_maximal", "balancedrawdownrelative": "balance_dd_relative",
    "equitydrawdownabsolute": "equity_dd_absolute", "equitydrawdownmaximal": "equity_dd_maximal",
    "equitydrawdownrelative": "equity_dd_relative", "totaltrades": "total_trades", "totaldeals": "total_deals",
    "shorttradeswon": "short_trades", "longtradeswon": "long_trades", "profittradesoftotal": "profit_trades",
    "losstradesoftotal": "loss_trades", "largestprofittrade": "largest_profit_trade",
    "largestlosstrade": "largest_loss_trade", "averageprofittrade": "average_profit_trade",
    "averagelosstrade": "average_loss_trade", "maximumconsecutivewins": "max_consecutive_wins",
    "maximumconsecutivelosses": "max_consecutive_losses", "historyquality": "history_quality",
    "bars": "bars", "ticks": "ticks", "symbols": "symbols", "initialdeposit": "initial_deposit",
    "leverage": "leverage", "currency": "currency", "company": "company", "expert": "expert",
    "symbol": "symbol", "period": "period", "broker": "broker", "ahpr": "ahpr", "ghpr": "ghpr",
    "lrcorrelation": "lr_correlation", "zscore": "z_score", "ontesterresult": "ontester_result",
    "marginlevel": "margin_level", "averageconsecutivewins": "avg_consecutive_wins",
    "averageconsecutivelosses": "avg_consecutive_losses",
}


@dataclass
class Grid:
    name: str
    fmt: str
    encoding: str
    rows: list[list[str]]
    spans: list[list[int]] | None = None  # HTML colspan per cell (section titles / totals)


@dataclass
class Order:
    order_id: str
    open_time: datetime | None
    time: datetime | None
    symbol: str
    kind: str
    volume_requested: float | None
    volume_filled: float | None
    price: float | None
    sl: float | None
    tp: float | None
    state: str
    comment: str


@dataclass
class Report:
    source_name: str
    source_format: str
    encoding: str
    title_lines: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)  # every "Label:" -> value seen in the report
    inputs: list[dict] = field(default_factory=list)  # [{"name", "value"}] in report order
    summary: dict[str, dict] = field(default_factory=dict)  # key -> {"label", "raw", "value", "pct"}
    orders: list[Order] = field(default_factory=list)
    deals: list[Deal] = field(default_factory=list)
    deal_header: list[str] = field(default_factory=list)
    order_header: list[str] = field(default_factory=list)
    has_position_ids: bool = False
    position_ids: dict[int, str] = field(default_factory=dict)  # deal seq -> position id when the report has it
    rejected: list[dict] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------------------------- inputs → grids
def _zip_members(raw: bytes) -> list[tuple[str, bytes]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ReportFormatError("Archive ZIP illisible ou corrompue.") from exc
    infos = [i for i in z.infolist() if not i.is_dir()]
    if len(infos) > MAX_ARCHIVE_MEMBERS:
        raise ReportFormatError(f"Archive refusée : plus de {MAX_ARCHIVE_MEMBERS} fichiers.")
    total, out = 0, []
    for i in infos:
        name = i.filename.replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/") or re.match(r"^[A-Za-z]:", name):
            raise ReportFormatError(f"Archive refusée : chemin dangereux « {i.filename} ».")
        if stat.S_ISLNK(i.external_attr >> 16):
            raise ReportFormatError(f"Archive refusée : lien symbolique « {i.filename} ».")
        if i.file_size > MAX_MEMBER_BYTES or (i.compress_size and i.file_size / max(i.compress_size, 1) > MAX_RATIO):
            raise ReportFormatError(f"Archive refusée : « {i.filename} » trop volumineux une fois décompressé.")
        total += i.file_size
        if total > MAX_TOTAL_UNCOMPRESSED:
            raise ReportFormatError("Archive refusée : volume décompressé trop important.")
        with z.open(i) as f:
            data = f.read(MAX_MEMBER_BYTES + 1)  # never trust the declared size
        if len(data) > MAX_MEMBER_BYTES or len(data) != i.file_size:
            raise ReportFormatError(f"Archive refusée : taille réelle de « {i.filename} » incohérente.")
        out.append((name, data))
    return out


_XML_FORBIDDEN = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I)
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _xml(data: bytes):
    if _XML_FORBIDDEN.search(data[:4096]) or _XML_FORBIDDEN.search(data):
        raise ReportFormatError("XLSX refusé : déclaration DOCTYPE/ENTITY (contenu actif interdit).")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ReportFormatError(f"XLSX corrompu : {exc}") from exc


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref or "")
    n = 0
    for ch in letters.group(0) if letters else "A":
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _xlsx_grid(name: str, raw: bytes) -> Grid:
    members = dict(_zip_members(raw))
    if "xl/workbook.xml" not in members:
        raise ReportFormatError("XLSX invalide : classeur absent.")
    shared: list[str] = []
    if "xl/sharedStrings.xml" in members:
        for si in _xml(members["xl/sharedStrings.xml"]).findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
    sheets = sorted(k for k in members if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", k))
    if not sheets:
        raise ReportFormatError("XLSX invalide : aucune feuille.")
    rows: list[list[str]] = []
    for sheet in sheets[:1]:  # MT5 writes the whole report on the first sheet
        data = _xml(members[sheet]).find(f"{_NS}sheetData")
        for r in (data.findall(f"{_NS}row") if data is not None else []):
            cells: dict[int, str] = {}
            for c in r.findall(f"{_NS}c"):
                t, v = c.get("t"), c.find(f"{_NS}v")
                if t == "s" and v is not None and v.text is not None:
                    idx = int(v.text)
                    text = shared[idx] if 0 <= idx < len(shared) else ""
                elif t == "inlineStr":
                    text = "".join(x.text or "" for x in c.iter(f"{_NS}t"))
                else:  # number / boolean / cached formula RESULT (the formula itself is never evaluated)
                    text = v.text if v is not None and v.text is not None else ""
                cells[_col_index(c.get("r", ""))] = " ".join(text.split())
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
            if len(rows) > MAX_ROWS:
                raise ReportFormatError("XLSX refusé : trop de lignes.")
    return Grid(name, "xlsx", "xml", rows)


def _html_grid(name: str, raw: bytes) -> Grid:
    text, enc = _decode(raw)
    p = _Tables()
    p.feed(text)
    if len(p.rows) > MAX_ROWS:
        raise ReportFormatError("HTML refusé : trop de lignes.")
    return Grid(name, "html", enc, [[c for c, _ in r] for r in p.rows], [[s for _, s in r] for r in p.rows])


def _csv_grid(name: str, raw: bytes) -> Grid:
    text, enc = _decode(raw)
    text = text.lstrip("﻿")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    sample = "\n".join(lines[:20])
    delim = max([";", "\t", ","], key=lambda d: sample.count(d))
    rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
    if len(rows) > MAX_ROWS:
        raise ReportFormatError("CSV refusé : trop de lignes.")
    return Grid(name, "csv", enc, rows)


def grids_from_upload(filename: str, raw: bytes) -> tuple[list[Grid], list[dict]]:
    """Grids of every report file in the upload, plus the list of archive members (name, bytes, kept/ignored)."""
    low = filename.lower()
    members = _zip_members(raw) if low.endswith(".zip") else [(filename, raw)]
    grids, listing = [], []
    for name, data in members:
        ext = "." + name.lower().rsplit(".", 1)[-1] if "." in name else ""
        kept = ext in REPORT_EXT
        listing.append({"name": name, "bytes": len(data), "used": kept})
        if not kept:
            continue
        if ext == ".xlsx":
            grids.append(_xlsx_grid(name, data))
        elif ext in (".htm", ".html"):
            grids.append(_html_grid(name, data))
        else:
            grids.append(_csv_grid(name, data))
    if not grids:
        raise ReportFormatError("Aucun rapport MT5 (.html, .xlsx, .csv) dans le fichier envoyé.")
    return grids, listing


# ---------------------------------------------------------------------------------------------- extraction
def _header(cells: list[str], columns: dict, required: tuple[str, ...]) -> dict[str, int] | None:
    found: dict[str, int] = {}
    for i, c in enumerate(cells):
        n = _norm(c)
        if not n:
            continue
        for col, names in columns.items():
            if col not in found and n in names:
                found[col] = i
                break
    return found if all(c in found for c in required) else None


def _is_label(cell: str) -> bool:
    return bool(cell) and cell.endswith(":") and len(cell) <= 80


def _metadata(grid: Grid, rep: Report, stop_at: int) -> None:
    rows = grid.rows[:stop_at]
    in_inputs = False
    for r in rows:
        nonempty = [(i, c) for i, c in enumerate(r) if c.strip()]
        if not nonempty:
            continue
        if not any(_is_label(c) for _, c in nonempty):
            if in_inputs and all("=" in c for _, c in nonempty):
                for _, c in nonempty:
                    k, _, v = c.partition("=")
                    rep.inputs.append({"name": k.strip(), "value": v.strip()})
                continue
            if len(nonempty) == 1 and not rep.metadata and len(rep.title_lines) < 4:
                rep.title_lines.append(nonempty[0][1])
            in_inputs = False
            continue
        in_inputs = False
        for j, (_i, c) in enumerate(nonempty):
            if not _is_label(c):
                continue
            nxt = nonempty[j + 1][1] if j + 1 < len(nonempty) and not _is_label(nonempty[j + 1][1]) else ""
            label = c[:-1].strip()
            key = _norm(label)
            if key == "inputs":
                in_inputs = True
                if "=" in nxt:
                    k, _, v = nxt.partition("=")
                    rep.inputs.append({"name": k.strip(), "value": v.strip()})
                continue
            rep.metadata.setdefault(label, nxt)
            if key in SUMMARY:
                rep.summary.setdefault(SUMMARY[key], _summary_value(label, nxt))


_PCT = re.compile(r"\(([-+\d.,\s]+)%\)|^([-+\d.,\s]+)%$")


def _summary_value(label: str, raw: str) -> dict:
    """'52 040.35 (91.62%)' -> value 52040.35, pct 91.62 ; '91.61% (51 990.13)' -> pct 91.61, value 51990.13."""
    out = {"label": label, "raw": raw, "value": None, "pct": None}
    s = raw.strip()
    m = re.fullmatch(r"([-+\d.,\s  ]+?)\s*\(([-+\d.,\s]+)%\)", s)
    m2 = re.fullmatch(r"([-+\d.,\s]+)%\s*\(([-+\d.,\s  ]+)\)", s)
    m3 = re.fullmatch(r"([-+\d.,\s  ]+?)\s*\(([-+\d.,\s]+)\)", s)
    try:
        if m:
            out["value"], out["pct"] = parse_number(m.group(1)), parse_number(m.group(2))
        elif m2:
            out["pct"], out["value"] = parse_number(m2.group(1)), parse_number(m2.group(2))
        elif m3:  # "314 (82.80%)" handled above; "4 (1 234.00)" = count (amount)
            out["value"], out["pct"] = parse_number(m3.group(1)), None
            out["amount"] = parse_number(m3.group(2))
        elif s.endswith("%"):
            out["pct"] = parse_number(s[:-1])
        else:
            out["value"] = parse_number(s)
    except ValueError:
        pass  # not numeric (names, "1:100", "M15 (…)") — raw kept, never guessed
    return out


def _table_rows(grid: Grid, start: int) -> list[tuple[int, list[str]]]:
    """Data rows under the header at ``start``. A row with too few filled cells (section title such as « Deals »,
    totals row) ends the table; a new header ends it too. Spans are NOT used: MT5 spans data cells as well."""
    width = sum(1 for c in grid.rows[start] if c.strip())
    minimum = max(3, width // 2)
    body = []
    for k in range(start + 1, len(grid.rows)):
        r = grid.rows[k]
        filled = sum(1 for c in r if c.strip())
        if filled == 0:
            continue
        if filled < minimum or _header(r, DEALS, DEAL_REQUIRED) or _header(r, ORDER_COLUMNS, ORDER_REQUIRED):
            if body:
                break
            continue
        body.append((k, r))
    return body


def _opt_number(text: str) -> float | None:
    try:
        return parse_number(text) if text and text.strip() else None
    except ValueError:
        return None


def _read_orders(grid: Grid, rep: Report, start: int, hmap: dict) -> None:
    for k, r in _table_rows(grid, start):
        get = lambda c, r=r: r[hmap[c]].strip() if c in hmap and hmap[c] < len(r) else ""  # noqa: E731
        try:
            vol = get("volume")
            req, _, fill = vol.partition("/")
            rep.orders.append(Order(
                order_id=get("order"),
                open_time=parse_time(get("open_time")) if get("open_time") else None,
                time=parse_time(get("time")) if get("time") else None,
                symbol=get("symbol").upper(), kind=_norm(get("type")),
                volume_requested=parse_number(req), volume_filled=parse_number(fill) if fill.strip() else None,
                price=_opt_number(get("price")), sl=_opt_number(get("sl")), tp=_opt_number(get("tp")),
                state=_norm(get("state")), comment=get("comment")[:200]))
        except ValueError as exc:
            rep.rejected.append({"table": "orders", "row": k + 1, "reason": str(exc), "cells": r[:12]})


def _read_deals(grid: Grid, rep: Report, start: int, hmap: dict) -> None:
    seen: set[str] = set()
    for k, r in _table_rows(grid, start):
        if len(r) <= max(hmap[c] for c in DEAL_REQUIRED):  # trailing empty cells (comment…) may be absent in XLSX
            continue
        get = lambda c, r=r: r[hmap[c]].strip() if c in hmap and hmap[c] < len(r) else ""  # noqa: E731
        try:
            kind = TYPES.get(_norm(get("type")), "other")
            direction = DIRECTIONS.get(_norm(get("direction")), "")
            if kind in ("buy", "sell") and not direction:
                raise ValueError(f"sens d'opération inconnu : {get('direction')!r}")
            fees = parse_number(get("fee"), empty=0.0) if "fee" in hmap else 0.0
            deal = Deal(time=parse_time(get("time")), seq=len(rep.deals), deal_id=get("deal"),
                        symbol=get("symbol").upper(), kind=kind,
                        direction=direction if kind in ("buy", "sell") else "",
                        volume=parse_number(get("volume"), empty=0.0 if kind == "balance" else None),
                        price=parse_number(get("price"), empty=0.0 if kind == "balance" else None),
                        commission=parse_number(get("commission"), empty=0.0) + fees,
                        swap=parse_number(get("swap"), empty=0.0), profit=parse_number(get("profit"), empty=0.0),
                        balance=parse_number(get("balance")) if get("balance") else None,
                        comment=get("comment")[:200])
            if deal.kind in ("buy", "sell") and (deal.volume <= 0 or deal.price <= 0):
                raise ValueError("volume ou prix non positif")
        except ValueError as exc:
            rep.rejected.append({"table": "deals", "row": k + 1, "reason": str(exc), "cells": r[:14]})
            continue
        if deal.deal_id:
            if deal.deal_id in seen:
                rep.duplicates.append(deal.deal_id)
                continue
            seen.add(deal.deal_id)
        if "position" in hmap and get("position"):
            rep.has_position_ids = True
            rep.position_ids[deal.seq] = get("position")
        rep.deals.append(deal)


def read_grid(grid: Grid) -> Report:
    rep = Report(source_name=grid.name, source_format=grid.fmt, encoding=grid.encoding)
    first_table = len(grid.rows)
    for i, r in enumerate(grid.rows):
        dmap = _header(r, DEALS, DEAL_REQUIRED)
        omap = None if dmap else _header(r, ORDER_COLUMNS, ORDER_REQUIRED)
        if dmap and not rep.deals:
            first_table = min(first_table, i)
            rep.deal_header = [c for c in r if c]
            _read_deals(grid, rep, i, dmap)
        elif omap and not rep.orders and "direction" not in [_norm(c) for c in r]:
            first_table = min(first_table, i)
            rep.order_header = [c for c in r if c]
            _read_orders(grid, rep, i, omap)
    _metadata(grid, rep, first_table)
    return rep


def read_upload(filename: str, raw: bytes) -> tuple[list[Report], list[dict]]:
    grids, listing = grids_from_upload(filename, raw)
    reports = [read_grid(g) for g in grids]
    return reports, listing


def read_members(filename: str, raw: bytes) -> tuple[list[Report], list[tuple[str, bytes]]]:
    """Reports of the upload and its members (name, bytes) — a ZIP is opened once, with the archive limits."""
    members = _zip_members(raw) if filename.lower().endswith(".zip") else [(filename, raw)]
    reports = []
    for name, data in members:
        low = name.lower()
        if low.endswith(".xlsx"):
            reports.append(read_grid(_xlsx_grid(name, data)))
        elif low.endswith((".htm", ".html")):
            reports.append(read_grid(_html_grid(name, data)))
        elif low.endswith((".csv", ".txt")):
            reports.append(read_grid(_csv_grid(name, data)))
    if not reports:
        raise ReportFormatError("Aucun rapport MT5 (.html, .xlsx, .csv) dans le fichier envoyé.")
    return reports, members
