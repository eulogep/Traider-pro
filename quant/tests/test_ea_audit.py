"""EA audit (ea_audit/): reading of MT5 deal reports and detection of grid / martingale mechanisms.

Fixtures are CONSTRUCTED deal lists written in the documented MT5 report layout (they are not reports from a
real EA). Each behaviour is built from its definition, so the expected verdict is known in advance.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ai_trader_optimizer.ea_audit import ReportFormatError, analyse, parse_report
from ai_trader_optimizer.ea_audit.report import parse_number

CS = 100.0  # XAUUSD hypothesis: 100 oz per lot
T0 = datetime(2026, 1, 5, 8, 0)
FR_HEADER = ["Heure", "Transaction", "Symbole", "Type", "Direction", "Volume", "Prix", "Ordre", "Commission",
             "Swap", "Profit", "Solde", "Commentaire"]
EN_HEADER = ["Time", "Deal", "Symbol", "Type", "Direction", "Volume", "Price", "Order", "Commission", "Swap",
             "Profit", "Balance", "Comment"]


class Book:
    """Builds a deal list with FIFO profits, like MT5 would report them (hedging account, one symbol)."""

    def __init__(self, deposit: float = 10_000.0):
        self.rows: list[list[str]] = []
        self.t = T0
        self.balance = deposit
        self.open: list[tuple[str, float, float]] = []  # (side, volume, price)
        self._row("balance", "", 0.0, 0.0, deposit)

    def _row(self, kind, direction, vol, price, profit):
        self.t += timedelta(minutes=7)
        if kind == "balance":
            pass
        else:
            self.balance += profit
        n = len(self.rows) + 1
        self.rows.append([self.t.strftime("%Y.%m.%d %H:%M:%S"), str(n), "" if kind == "balance" else "XAUUSD",
                          kind, direction, "" if kind == "balance" else f"{vol:.2f}",
                          "" if kind == "balance" else f"{price:.2f}", str(n), "0.00", "0.00",
                          f"{profit:,.2f}".replace(",", " "), f"{self.balance:,.2f}".replace(",", " "), ""])

    def buy(self, vol, price):
        self.open.append(("buy", vol, price))
        self._row("buy", "in", vol, price, 0.0)

    def sell(self, vol, price):
        self.open.append(("sell", vol, price))
        self._row("sell", "in", vol, price, 0.0)

    def close_all(self, price):
        for side, vol, entry in list(self.open):
            pnl = (price - entry) * vol * CS * (1 if side == "buy" else -1)
            self._row("sell" if side == "buy" else "buy", "out", vol, price, round(pnl, 2))
        self.open.clear()


def html(rows, header=FR_HEADER, encoding="utf-16") -> bytes:
    cells = lambda r, tag="td": "".join(f"<{tag}>{c}</{tag}>" for c in r)  # noqa: E731
    body = ("<html><body><table>"
            "<tr><td colspan=\"13\"><b>Résultats</b></td></tr><tr><td>Dépôt initial</td><td>10 000.00</td></tr>"
            "<tr><td colspan=\"13\"><b>Transactions</b></td></tr>"
            f"<tr>{cells(header)}</tr>" + "".join(f"<tr>{cells(r)}</tr>" for r in rows) +
            "<tr><td colspan=\"8\"></td><td>0.00</td><td>0.00</td><td>123.00</td><td>10 123.00</td></tr>"
            "</table></body></html>")
    return body.encode(encoding)


def martingale_grid() -> Book:
    b = Book()
    for k in range(6):
        base = 2000 + 3 * k
        for i, vol in enumerate((0.01, 0.02, 0.04, 0.08)):
            b.buy(vol, base - 5 * i)
        b.close_all(base - 8)  # basket closed in profit after the bounce
    return b


def run(raw: bytes) -> dict:
    return analyse(parse_report(raw), CS, "hypothèse test")


def test_martingale_grid_is_detected_from_an_mt5_utf16_french_report():
    out = run(html(martingale_grid().rows))
    assert out["source"]["format"] == "html" and out["source"]["encoding"] == "utf-16"
    assert out["source"]["rows_rejected"] == 0
    codes = {f["code"] for f in out["flags"]}
    assert {"STACKING", "AVERAGING_DOWN", "LOT_ESCALATION"} <= codes
    assert out["verdict"]["code"] == "MARTINGALE"
    assert out["exposure"]["max_positions_same_direction"] == 4
    assert out["exposure"]["median_add_ratio"] == pytest.approx(2.0)
    assert out["counts"]["baskets_closed"] == 6 and out["counts"]["unmatched_close_volume"] == 0


def test_grid_with_constant_lots_is_a_grid_not_a_martingale():
    b = Book()
    for k in range(6):
        for i in range(4):
            b.sell(0.05, 2000 + 4 * i + k)  # adds while price rises against the shorts
        b.close_all(2005 + k)
    out = run(html(b.rows, header=EN_HEADER, encoding="utf-8"))
    codes = {f["code"] for f in out["flags"]}
    assert "AVERAGING_DOWN" in codes and "STACKING" in codes and "LOT_ESCALATION" not in codes
    assert out["verdict"]["code"] == "GRID"


def test_lot_doubled_after_each_loss_is_a_martingale_even_with_one_position_at_a_time():
    b = Book()
    lot, price = 0.01, 2000.0
    pattern = [False, False, True, False, True, False, False, True, False, True, False, True]  # True = win
    for win in pattern:
        b.buy(lot, price)
        exit_price = price + 3 if win else price - 3
        b.close_all(exit_price)
        lot = 0.01 if win else round(lot * 2, 2)
        price = exit_price
    out = run(html(b.rows))
    assert out["exposure"]["max_positions_same_direction"] == 1
    assert "MARTINGALE_AFTER_LOSS" in {f["code"] for f in out["flags"]}
    assert out["verdict"]["code"] == "MARTINGALE"


def test_a_plain_fixed_lot_strategy_shows_no_signature_and_says_it_is_not_a_proof():
    b = Book()
    price = 2000.0
    for i in range(14):
        b.buy(0.10, price) if i % 2 == 0 else b.sell(0.10, price)
        price += (4 if i % 3 else -3) * (1 if i % 2 == 0 else -1)
        b.close_all(price)
    out = run(html(b.rows))
    assert out["flags"] == []
    assert out["verdict"]["code"] == "NO_SIGNATURE"
    assert "pas une preuve" in out["verdict"]["text"]


def test_stress_gives_the_adverse_move_that_empties_the_account_at_peak_exposure():
    b = Book(deposit=1_000.0)
    for vol, price in ((0.05, 2000.0), (0.10, 1990.0)):
        b.buy(vol, price)
    b.close_all(1995.0)
    s = run(html(b.rows))["stress"]
    assert s["net_lots"] == pytest.approx(0.15)
    assert s["loss_per_price_unit"] == pytest.approx(15.0)  # 0.15 lot × 100 oz: 15 $ per $1 move
    # at the second entry (price 1990): floating = (1990-2000)·0.05·100 = −50 → equity 950
    assert s["equity_estimate"] == pytest.approx(950.0)
    assert s["adverse_move_to_zero"] == pytest.approx(950.0 / 15.0)
    assert s["adverse_move_to_lose_half"] == pytest.approx((950.0 - 500.0) / 15.0)
    assert s["direction"] == "baisse"


def test_short_reports_are_insufficient():
    b = Book()
    b.buy(0.01, 2000)
    b.close_all(2001)
    assert run(html(b.rows))["verdict"]["code"] == "INSUFFICIENT"


def test_unreadable_rows_are_counted_and_never_guessed():
    rows = martingale_grid().rows
    rows[3][6] = "1,990.50"  # thousands comma + decimal point: ambiguous -> refused
    rows[5][4] = "sideways"  # unknown direction -> refused
    out = run(html(rows))
    assert out["source"]["rows_rejected"] == 2
    reasons = " ".join(r["reason"] for r in out["source"]["rejected_examples"])
    assert "ambigu" in reasons and "sens" in reasons


def test_csv_with_semicolons_and_decimal_commas():
    rows = martingale_grid().rows
    lines = [";".join(EN_HEADER)] + [";".join(c.replace(".", ",") if i in (5, 6) else c for i, c in enumerate(r))
                                      for r in rows]
    out = run("\n".join(lines).encode("utf-8"))
    assert out["source"]["format"] == "csv" and out["verdict"]["code"] == "MARTINGALE"


def test_numbers_follow_mt5_conventions():
    assert parse_number("10 000.50") == 10000.5
    assert parse_number("-1 234.00") == -1234.0
    assert parse_number("0,25") == 0.25
    assert parse_number("0.10 / 0.10") == 0.10
    for bad in ("1,000.00", "abc", "1e309", "nan"):
        with pytest.raises(ValueError):
            parse_number(bad)


def test_a_file_without_a_deal_table_is_refused():
    with pytest.raises(ReportFormatError):
        parse_report(b"<html><table><tr><td>Rapport</td></tr></table></html>")
    with pytest.raises(ReportFormatError):
        parse_report(b"a;b;c\n1;2;3\n")


def test_closes_without_a_known_opening_are_reported():
    rows = martingale_grid().rows
    out = run(html([rows[0]] + rows[5:]))  # report starts in the middle of the first basket
    assert out["counts"]["unmatched_close_volume"] > 0


# ---------------------------------------------------------------- API
@pytest.fixture
def client(lab_dir):
    from ai_trader_optimizer.api.app import create_app
    from ai_trader_optimizer.storage import LabCatalog

    from conftest import LocalClient
    return LocalClient(create_app(LabCatalog()))


def test_api_analyses_an_uploaded_report_without_storing_anything(client, lab_dir):
    before = sorted(p.name for p in lab_dir.rglob("*")) if lab_dir.exists() else []
    files = {"file": ("ReportTester-123.html", html(martingale_grid().rows), "text/html")}
    r = client.post("/api/v1/ea-reports/analyze", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"]["code"] == "MARTINGALE" and body["stored"] is False
    assert body["contract"]["contract_size"] == 100.0 and "hypothèse" in body["contract"]["note"]
    after = sorted(p.name for p in lab_dir.rglob("*")) if lab_dir.exists() else []
    assert [p for p in after if p not in before and not p.endswith((".db", ".lock", "-journal"))] == []


def test_api_uses_a_declared_contract_size(client):
    files = {"file": ("deals.csv", "\n".join(";".join(r) for r in [EN_HEADER] + martingale_grid().rows).encode(),
                      "text/csv")}
    r = client.post("/api/v1/ea-reports/analyze", files=files, data={"contract_size": "10"})
    assert r.status_code == 200, r.text
    assert r.json()["contract"]["contract_size"] == 10.0


@pytest.mark.parametrize("name,content,status", [
    ("report.ex5", b"MZ\x00binary", 415),
    ("report.html", b"<html><table><tr><td>x</td></tr></table></html>", 422),
])
def test_api_refuses_binaries_and_files_without_deals(client, name, content, status):
    r = client.post("/api/v1/ea-reports/analyze", files={"file": (name, content, "application/octet-stream")})
    assert r.status_code == status


def test_api_requires_the_local_mutation_header(lab_dir):
    from ai_trader_optimizer.api.app import create_app
    from ai_trader_optimizer.storage import LabCatalog

    from conftest import LocalClient
    naive = LocalClient(create_app(LabCatalog()), local_header=False)
    files = {"file": ("r.html", html(martingale_grid().rows), "text/html")}
    assert naive.post("/api/v1/ea-reports/analyze", files=files).status_code == 403


def test_a_broker_stop_out_is_the_first_thing_reported():
    b = martingale_grid()
    for i in range(4):
        b.buy(0.10, 1990 - 10 * i)
    b.close_all(1900)
    for r in b.rows[-4:-1]:
        r[12] = "so 12.43%"  # MT5 comment of a stop-out close
    b.rows[-1][12] = "end of test"
    out = run(html(b.rows))
    assert out["verdict"]["code"] == "STOP_OUT"
    assert out["flags"][0]["code"] == "STOP_OUT" and "so 12.43%" in out["flags"][0]["detail"]
    assert out["counts"]["stop_out_closes"] == 3 and out["counts"]["end_of_test_closes"] == 1
    assert "END_OF_TEST_CLOSE" in {f["code"] for f in out["flags"]}


REAL_REPORT = os.environ.get("ATO_REAL_MT5_REPORT") or str(
    Path(__file__).parent / "fixtures" / "mt5" / "Gold_Grid_V370_MT5_Baseline_2026.html")


def test_real_gold_grid_v370_report_matches_the_mt5_summary():
    """Real Strategy Tester report of « Gold Grid Strategy V3.70 EA » (SHA-256 9048261e…, kept outside the repo).
    Figures checked against the summary MT5 prints in the same file: Total Net Profit −5 238.26, 314 trades."""
    raw = open(REAL_REPORT, "rb").read()
    assert hashlib.sha256(raw).hexdigest().startswith("9048261e1d5016dd")
    out = run(raw)
    assert out["source"]["rows_rejected"] == 0 and out["source"]["deals_read"] == 629
    assert out["baskets"]["net_total"] == pytest.approx(-5238.26, abs=0.01)
    assert out["counts"]["entries"] == 314
    assert out["verdict"]["code"] == "STOP_OUT"
    assert {"STACKING", "AVERAGING_DOWN"} <= {f["code"] for f in out["flags"]}


# ---------------------------------------------------------------- local MT5 bridge (read-only)
def _fake_mt5(tmp_path, monkeypatch):
    drive = tmp_path / "drive_c"
    docs = drive / "users" / "user" / "Documents"
    files = drive / "Program Files" / "MetaTrader 5" / "MQL5" / "Files"
    cfg = drive / "Program Files" / "MetaTrader 5" / "config"
    for d in (docs, files, cfg):
        d.mkdir(parents=True)
    (docs / "ReportTester-1.html").write_bytes(html(martingale_grid().rows))
    (docs / "notes.txt").write_text("pas un rapport")
    (cfg / "accounts.dat").write_bytes(b"secret")  # must never be listed
    outside = tmp_path / "outside.html"
    outside.write_bytes(html(martingale_grid().rows))
    (files / "link.html").symlink_to(outside)  # symlink leaving the folder: not followed
    monkeypatch.setenv("ATO_MT5_DIR", str(drive))
    return drive


def test_local_mt5_files_are_listed_read_only_without_config_or_symlinks(client, tmp_path, monkeypatch):
    _fake_mt5(tmp_path, monkeypatch)
    body = client.get("/api/v1/mt5/local-files").json()
    assert body["available"] is True
    names = [f["name"] for f in body["files"]]
    assert names == ["ReportTester-1.html"]
    assert all("_path" not in f for f in body["files"])
    fid = body["files"][0]["id"]
    r = client.post(f"/api/v1/mt5/local-files/{fid}/analyze")
    assert r.status_code == 200, r.text
    assert r.json()["verdict"]["code"] == "MARTINGALE" and "lecture seule" in r.json()["note"]


def test_local_mt5_unknown_ids_and_paths_are_refused(client, tmp_path, monkeypatch):
    _fake_mt5(tmp_path, monkeypatch)
    assert client.post("/api/v1/mt5/local-files/0123456789abcdef/analyze").status_code == 404
    assert client.post("/api/v1/mt5/local-files/..%2F..%2Fetc/analyze").status_code in (404, 422)


def test_no_terminal_is_reported_as_unavailable(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ATO_MT5_DIR", str(tmp_path / "absent"))
    body = client.get("/api/v1/mt5/local-files").json()
    assert body["available"] is False and body["files"] == []


def test_api_accepts_a_real_sized_report_on_the_audit_route(client):
    """Regression: the guard capped this route at the 256 KB JSON limit; the real MT5 report is 637 KB."""
    raw = open(REAL_REPORT, "rb").read()
    assert len(raw) > 300 * 1024
    r = client.post("/api/v1/ea-reports/analyze", files={"file": ("Gold_Grid_V370.html", raw, "text/html")})
    assert r.status_code == 200, r.text
    assert r.json()["verdict"]["code"] == "STOP_OUT"
