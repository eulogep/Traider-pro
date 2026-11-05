"""External Bot Analysis & Optimization Lab (v0.5): MT5 import → validation → immutable catalogue → API.

Reference fixture: the REAL Strategy Tester report of « Gold Grid Strategy V3.70 EA » (tests/fixtures/mt5/,
SHA-256 checked). Other cases use CONSTRUCTED reports in the MT5 layout, built so the expected answer is known.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import zipfile
from pathlib import Path

import pytest

from ai_trader_optimizer.ea_audit.report import ReportFormatError
from ai_trader_optimizer.external_lab import catalog as C
from ai_trader_optimizer.external_lab import whatif as W
from ai_trader_optimizer.external_lab.catalog import ExternalSimConflictError, ExternalSimIntegrityError
from ai_trader_optimizer.external_lab.mt5_report import read_members

FIX = Path(__file__).parent / "fixtures" / "mt5"
REAL_HTML = FIX / "Gold_Grid_V370_MT5_Baseline_2026.html"
REAL_XLSX = FIX / "Gold_Grid_V370_MT5_Baseline_2026.xlsx"
DEALS_HEAD = ["Time", "Deal", "Symbol", "Type", "Direction", "Volume", "Price", "Order", "Commission", "Swap",
              "Profit", "Balance", "Comment"]
ORDERS_HEAD = ["Open Time", "Order", "Symbol", "Type", "Volume", "Price", "S / L", "T / P", "Time", "State", "Comment"]


@pytest.fixture(scope="module")
def real_html() -> bytes:
    raw = REAL_HTML.read_bytes()
    expected = dict(line.split("  ")[::-1] for line in (FIX / "SHA256SUMS").read_text().splitlines())
    assert hashlib.sha256(raw).hexdigest() == expected[REAL_HTML.name]  # the reference has not changed
    return raw


# ---------------------------------------------------------------- constructed MT5-layout report
def _fmt(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ")


def deals_rows(net_profit_override: float | None = None):
    """Two-position SELL basket closed collectively by BUY deals, then a BUY closed in profit. Contract 100."""
    rows, bal = [], 10_000.0
    rows.append(["2026.01.01 00:00:00", "1", "", "balance", "", "", "", "", "0.00", "0.00", _fmt(10000), _fmt(10000), ""])
    spec = [("2026.01.05 10:00:00", "sell", "in", 0.10, 2000.00, 0.0, ""),
            ("2026.01.05 10:30:00", "sell", "in", 0.20, 2004.00, 0.0, ""),
            ("2026.01.05 12:00:00", "buy", "out", 0.20, 1998.00, (2004 - 1998) * 0.20 * 100, ""),  # closes 2nd SELL
            ("2026.01.05 12:00:00", "buy", "out", 0.10, 1998.00, (2000 - 1998) * 0.10 * 100, ""),  # closes 1st SELL
            ("2026.01.06 09:00:00", "buy", "in", 0.10, 2010.00, 0.0, ""),
            ("2026.01.06 11:00:00", "sell", "out", 0.10, 2015.00, (2015 - 2010) * 0.10 * 100, "tp 2015.00")]
    for k, (t, ty, di, v, p, pr, cm) in enumerate(spec, start=2):
        bal += pr
        rows.append([t, str(k), "XAUUSD", ty, di, f"{v:.2f}", f"{p:.2f}", str(k), "0.00", "0.00", _fmt(pr), _fmt(bal), cm])
    return rows


def mt5_html(deals=None, summary=None, inputs=("InpLots=0.10", "InpDDMode=0"), orders=True) -> bytes:
    deals = deals if deals is not None else deals_rows()
    summary = summary or {"Total Net Profit:": "190.00", "Gross Profit:": "190.00", "Gross Loss:": "0.00",
                          "Total Trades:": "3", "Total Deals:": "6", "Profit Trades (% of total):": "3 (100.00%)",
                          "Largest profit trade:": "120.00", "Initial Deposit:": "10 000.00"}  # = the deals below
    td = lambda cells: "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"  # noqa: E731
    h = ["<html><body><table>", "<tr><td colspan=13>Strategy Tester Report</td></tr>",
         "<tr><td colspan=13>MetaQuotes-Demo (Build 6275)</td></tr>", "<tr><td colspan=13>Settings</td></tr>",
         td(["Expert:", "Test Grid EA"]), td(["Symbol:", "XAUUSD"]), td(["Period:", "M15 (2026.01.01 - 2026.03.31)"])]
    for i, inp in enumerate(inputs):
        h.append(td(["Inputs:" if i == 0 else "", inp]))
    h += [td(["Company:", "MetaQuotes Ltd."]), td(["Currency:", "USD"]), td(["Leverage:", "1:100"])]
    for k, v in summary.items():
        h.append(td([k, v]))
    if orders:
        h.append("<tr><td colspan=13>Orders</td></tr>" + td(ORDERS_HEAD))
        for r in deals[1:]:
            h.append(td([r[0], r[7], "XAUUSD", r[3], f"{r[5]} / {r[5]}", "0.00", "", "", r[0], "filled", r[12]]))
    h.append("<tr><td colspan=13>Deals</td></tr>" + td(DEALS_HEAD))
    h += [td(r) for r in deals]
    h.append("<tr><td colspan=8></td><td>0.00</td><td>0.00</td><td>250.00</td><td>10 250.00</td></tr></table></body></html>")
    return "".join(h).encode("utf-16")


def xlsx_from_rows(rows: list[list[str]], extra: dict[str, bytes] | None = None, doctype: bool = False) -> bytes:
    shared, idx = [], {}

    def s(v):
        if v not in idx:
            idx[v] = len(shared)
            shared.append(v)
        return idx[v]
    cols = "ABCDEFGHIJKLMN"
    sheet = ['<?xml version="1.0" encoding="UTF-8"?>' + ('<!DOCTYPE x [<!ENTITY a "b">]>' if doctype else ""),
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for r, row in enumerate(rows, 1):
        cells = "".join(f'<c r="{cols[c]}{r}" t="s"><v>{s(v)}</v></c>' for c, v in enumerate(row) if v != "")
        sheet.append(f'<row r="{r}">{cells}</row>')
    sheet.append("</sheetData></worksheet>")
    sst = ('<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           + "".join(f"<si><t>{v.replace('&', '&amp;').replace('<', '&lt;')}</t></si>" for v in shared) + "</sst>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", "".join(sheet))
        for k, v in (extra or {}).items():
            z.writestr(k, v)
    return buf.getvalue()


def imp(root, name, raw):
    return C.import_file(root, name, raw, 100.0, "test")


# ---------------------------------------------------------------- 1. HTML / 9. reconciliation / reference case
def test_reference_v370_html_is_imported_and_matches_every_mt5_figure(tmp_path, real_html):
    s = imp(tmp_path, REAL_HTML.name, real_html)["simulation"]
    assert s["validation"]["status"] == "validé"
    recon = {r["metric"]: r for r in s["reconciliation"]}
    assert all(r["status"] == "concordant" for r in recon.values()) and len(recon) >= 20
    assert recon["net_profit"]["reported"] == -5238.26 and recon["total_trades"]["reported"] == 314
    assert s["counts"] == {"orders": 628, "deals": 629, "trading_deals": 628, "positions_opened": 314,
                           "closing_deals": 314, "trades": 314, "balance_operations": 1}
    assert s["pairing"]["closes_matched"] == 314 and s["contract_size"]["value"] == 100.0
    c = s["collapse"]
    assert c["losing_trades"] == 10 and round(c["losing_total"], 2) == -51990.13 and c["lots_involved"] == 9.38
    assert c["close_reasons"] == {"stop-out": 5, "fin du test": 5}
    assert [t["exit_deal"] for t in c["trades"]] == [str(n) for n in range(620, 630)]
    assert round(min(t["net"] for t in c["trades"]), 2) == -6776.72 == recon["largest_loss_trade"]["reported"]
    # requested vs observed period: documented, not ignored
    p = s["period"]
    assert p["requested_end"] == "2026-10-31" and p["last_deal"].startswith("2026-07-30T01:00") and p["ends_early"]
    assert "stop-out" in p["last_instant_close_reasons"]
    # 12. original configuration preserved, in order
    assert s["inputs"][0] == {"name": "InpNoteName", "value": "Quantum Queen MT5 v3.70 (07/06/2026)"}
    assert {"name": "InpDDMode", "value": "0"} in s["inputs"] and len(s["inputs"]) == 41
    assert s["robot"]["self_identification"].startswith("Quantum Queen") and s["environment"]["server"] == "MetaQuotes-Demo"


def test_reference_v370_xlsx_is_the_same_test_as_the_html(tmp_path, real_html):
    a = imp(tmp_path, REAL_HTML.name, real_html)["simulation"]
    b = imp(tmp_path, REAL_XLSX.name, REAL_XLSX.read_bytes())["simulation"]
    assert b["source"]["format"] == "xlsx" and b["validation"]["status"] == "validé"
    assert a["identity"]["deals_sha256"] == b["identity"]["deals_sha256"] and a["test_key"] == b["test_key"]
    assert a["sim_id"] != b["sim_id"]  # two sources, two traceable references
    listing = C.list_simulations(tmp_path)["simulations"]
    assert all(x["same_test_sources"] == 2 and not x["contradictory"] for x in listing)


# ---------------------------------------------------------------- 2. Excel / 10. BUY/SELL vs OPEN/CLOSE / 11. collective close
def test_constructed_xlsx_buy_deals_close_sell_positions_collectively(tmp_path):
    rows = [["Strategy Tester Report"], ["MetaQuotes-Demo (Build 6275)"], ["Expert:", "", "", "Test Grid EA"],
            ["Symbol:", "", "", "XAUUSD"], ["Period:", "", "", "M15 (2026.01.01 - 2026.03.31)"],
            ["Total Net Profit:", "", "", "250.00"], [], ["Deals"], DEALS_HEAD] + deals_rows()
    s = imp(tmp_path, "t.xlsx", xlsx_from_rows(rows))["simulation"]
    assert s["source"]["format"] == "xlsx"
    sides = [(t["side"], t["entry_deal"], t["exit_deal"]) for t in s["trades"]]
    assert ("SELL", "3", "4") in sides and ("SELL", "2", "5") in sides  # BUY deals 4/5 CLOSE the two SELL positions
    assert ("BUY", "6", "7") in sides and s["pairing"]["closes_matched"] == 3
    assert s["counts"]["positions_opened"] == 3 and s["counts"]["closing_deals"] == 3
    assert next(t for t in s["trades"] if t["exit_deal"] == "7")["close_reason"] == "take-profit"


def test_constructed_html_is_validated_and_a_wrong_summary_is_shown_as_a_discrepancy(tmp_path):
    ok = imp(tmp_path, "ok.html", mt5_html())["simulation"]
    assert ok["validation"]["status"] == "validé"
    bad = imp(tmp_path, "bad.html", mt5_html(summary={"Total Net Profit:": "999.00", "Total Trades:": "3"}))["simulation"]
    assert bad["validation"]["status"] == "écarts"
    row = next(r for r in bad["reconciliation"] if r["metric"] == "net_profit")
    assert row["status"] == "écart" and row["reported"] == 999.0 and row["computed"] == pytest.approx(190.0)


# ---------------------------------------------------------------- 3. idempotence / 4. contradictions
def test_the_same_file_imported_twice_is_idempotent(tmp_path):
    raw = mt5_html()
    a, b = imp(tmp_path, "r.html", raw), imp(tmp_path, "r.html", raw)
    assert a["outcome"] == "créée" and b["outcome"] == "déjà importée"
    assert len(list((tmp_path / "external" / "simulations").glob("*.json"))) == 1
    log = [json.loads(x)["entry"]["outcome"] for x in (tmp_path / "external" / "imports.jsonl").read_text().splitlines()]
    assert log == ["créée", "déjà importée"]


def test_same_identifier_with_different_content_is_refused(tmp_path, monkeypatch):
    raw = mt5_html()
    imp(tmp_path, "r.html", raw)
    import ai_trader_optimizer.external_lab.simulation as S
    monkeypatch.setattr(S, "LAB_VERSION", "external-lab/999")  # same file, different analysis output
    with pytest.raises(ExternalSimConflictError):
        imp(tmp_path, "r.html", raw)


def test_same_configuration_with_different_deals_is_flagged_contradictory(tmp_path):
    imp(tmp_path, "a.html", mt5_html())
    rows = deals_rows()
    rows[-1][6] = "2016.00"
    rows[-1][10] = "60.00"
    rows[-1][11] = _fmt(10260)
    imp(tmp_path, "b.html", mt5_html(deals=rows))
    listing = C.list_simulations(tmp_path)["simulations"]
    assert len(listing) == 2 and all(x["contradictory"] for x in listing)


# ---------------------------------------------------------------- 5. corrupt / 6. malicious archives / 7. numbers / 8. incomplete
@pytest.mark.parametrize("name,raw", [
    ("x.zip", b"PK\x03\x04 not a zip"),
    ("x.xlsx", b"PK\x05\x06" + b"\x00" * 18),
    ("x.html", b"<html><table><tr><td>rien</td></tr></table></html>"),
    ("x.csv", b"a;b\n1;2\n"),
])
def test_corrupt_files_are_refused_and_nothing_is_written(tmp_path, name, raw):
    with pytest.raises(ReportFormatError):
        imp(tmp_path, name, raw)
    assert not list((tmp_path / "external" / "simulations").glob("*.json")) if (tmp_path / "external").exists() else True


def _zip(members: dict[str, bytes], symlink: str | None = None, compress=zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compress) as z:
        for k, v in members.items():
            z.writestr(k, v)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "/etc/passwd")
    return buf.getvalue()


@pytest.mark.parametrize("archive,needle", [
    (lambda: _zip({"../evil.html": b"x"}), "chemin dangereux"),
    (lambda: _zip({"/abs.html": b"x"}), "chemin dangereux"),
    (lambda: _zip({"ok.csv": b"a"}, symlink="link.html"), "lien symbolique"),
    (lambda: _zip({f"f{i}.csv": b"a" for i in range(25)}), "plus de"),
    (lambda: _zip({"bomb.csv": b"0" * (5 * 1024 * 1024)}), "trop volumineux"),
])
def test_malicious_archives_are_refused(tmp_path, archive, needle):
    with pytest.raises(ReportFormatError, match=needle):
        imp(tmp_path, "a.zip", archive())


def test_xlsx_with_a_doctype_or_entity_is_refused(tmp_path):
    rows = [["Deals"], DEALS_HEAD] + deals_rows()
    with pytest.raises(ReportFormatError, match="DOCTYPE"):
        imp(tmp_path, "e.xlsx", xlsx_from_rows(rows, doctype=True))


def test_invalid_numbers_are_rejected_rows_not_guesses(tmp_path):
    rows = deals_rows()
    rows[2][6] = "2,004.00"  # thousands comma + decimal point: ambiguous
    rows[3][5] = "nan"
    s = imp(tmp_path, "n.html", mt5_html(deals=rows))["simulation"]
    rej = [r for r in s["validation"]["rejected_rows"] if r["table"] == "deals"]
    assert len(rej) == 2 and s["validation"]["status"] == "écarts"
    assert {"ambigu" in r["reason"] or "illisible" in r["reason"] for r in rej} == {True}


def test_incomplete_transactions_are_reported(tmp_path):
    rows = deals_rows()
    del rows[1]  # the first SELL opening is missing: its close cannot be matched
    s = imp(tmp_path, "i.html", mt5_html(deals=rows, summary={"Total Trades:": "3"}))["simulation"]
    assert s["pairing"]["unmatched_close_volume"] > 0 or s["pairing"]["closes_matched"] < s["pairing"]["closes_checked"]
    assert s["validation"]["status"] == "écarts"


def test_a_deals_only_csv_without_mt5_summary_is_partial(tmp_path):
    csv = "\n".join(",".join(c.replace(" ", "") if 5 <= i <= 11 else c for i, c in enumerate(r))
                    for r in [DEALS_HEAD] + deals_rows()).encode()
    s = imp(tmp_path, "deals.csv", csv)["simulation"]
    assert s["validation"]["status"] == "partiel" and s["reconciliation"] == []
    assert s["availability"]["summary"] is False and s["availability"]["position_ids"] is False


# ---------------------------------------------------------------- 13. integrity after import / immutability
def test_stored_simulation_and_source_are_read_only_and_tampering_is_detected(tmp_path):
    sid = imp(tmp_path, "r.html", mt5_html())["simulation"]["sim_id"]
    sim = tmp_path / "external" / "simulations" / f"{sid}.json"
    src = next((tmp_path / "external" / "sources").glob("*.html"))
    assert not os.access(sim, os.W_OK) and not os.access(src, os.W_OK)
    os.chmod(sim, 0o644)
    doc = json.loads(sim.read_bytes())
    doc["simulation"]["recomputed"]["net_profit"] = 99999.0  # falsified figure, then re-hashed to look consistent
    from ai_trader_optimizer.storage.integrity import canonical_json
    doc["sha256"] = hashlib.sha256(canonical_json(doc["simulation"])).hexdigest()
    sim.write_bytes(canonical_json(doc))
    with pytest.raises(ExternalSimIntegrityError, match="incohérent"):
        C.load(tmp_path, sid)
    assert C.list_simulations(tmp_path)["simulations"][0]["integrity"] == "refusée"


def test_a_modified_source_file_invalidates_the_simulation(tmp_path):
    sid = imp(tmp_path, "r.html", mt5_html())["simulation"]["sim_id"]
    src = next((tmp_path / "external" / "sources").glob("*.html"))
    os.chmod(src, 0o644)
    src.write_bytes(src.read_bytes() + b" ")
    with pytest.raises(ExternalSimIntegrityError, match="source"):
        C.load(tmp_path, sid)


def test_external_simulations_are_isolated_from_engine_runs(tmp_path):
    from ai_trader_optimizer.storage import LabCatalog
    cat = LabCatalog(tmp_path)
    imp(tmp_path, "r.html", mt5_html())
    assert cat.list_runs().empty  # an imported MT5 simulation is never a run of the engine


# ---------------------------------------------------------------- what-if qualifications
def test_what_if_rules_are_always_qualified(tmp_path, real_html):
    s = imp(tmp_path, REAL_HTML.name, real_html)["simulation"]
    q = {r: W.run(s, r, None)["qualification"] for r in W.RULES}
    assert q["stop_after_realised_dd"] == "exact" and q["volatility_reduction"] == "non_simulable"
    assert all(v == "approximation" for k, v in q.items() if k not in ("stop_after_realised_dd", "volatility_reduction"))
    dd = W.run(s, "stop_after_realised_dd", 20)
    assert dd["result"]["removed_trades"] == 0 and "latentes" in dd["explanation"]  # V3.70: losses were unrealised
    cap = W.run(s, "exposure_cap", 3)
    assert cap["caveats"] and "pas un backtest" in cap["explanation"]
    with pytest.raises(ValueError):
        W.run(s, "martingale_boost", 2)


def test_lot_scaling_is_exact_arithmetic_on_observed_fills(tmp_path, real_html):
    s = imp(tmp_path, REAL_HTML.name, real_html)["simulation"]
    half = W.run(s, "lot_scale", 0.5)
    assert half["result"]["net"] == pytest.approx(-5238.26 / 2, abs=0.01)


# ---------------------------------------------------------------- API
@pytest.fixture
def client(lab_dir):
    from ai_trader_optimizer.api.app import create_app
    from ai_trader_optimizer.storage import LabCatalog

    from conftest import LocalClient
    return LocalClient(create_app(LabCatalog()))


def test_api_import_list_detail_and_what_if(client, real_html):
    files = {"file": (REAL_HTML.name, real_html, "text/html")}
    r = client.post("/api/v1/external-sims", files=files)
    assert r.status_code == 201, r.text
    sid = r.json()["sim_id"]
    assert client.post("/api/v1/external-sims", files=files).status_code == 200  # idempotent
    listing = client.get("/api/v1/external-sims").json()
    assert listing["simulations"][0]["sim_id"] == sid and listing["robots"][0]["robot"] == "Gold Grid Strategy V3.70 EA"
    d = client.get(f"/api/v1/external-sims/{sid}").json()
    assert d["collapse"]["losing_trades"] == 10
    w = client.get(f"/api/v1/external-sims/{sid}/what-if", params={"rule": "max_positions", "value": 3}).json()
    assert w["qualification"] == "approximation"
    assert client.get("/api/v1/external-sims/what-if-rules").status_code == 200
    assert client.get("/api/v1/external-sims/0123456789abcdef").status_code == 404


@pytest.mark.parametrize("name,status", [("robot.ex5", 415), ("x.html", 422)])
def test_api_refuses_executables_and_unreadable_reports(client, name, status):
    r = client.post("/api/v1/external-sims", files={"file": (name, b"MZ\x00\x00", "application/octet-stream")})
    assert r.status_code == status


def test_api_import_requires_the_local_mutation_header(lab_dir, real_html):
    from ai_trader_optimizer.api.app import create_app
    from ai_trader_optimizer.storage import LabCatalog

    from conftest import LocalClient
    naive = LocalClient(create_app(LabCatalog()), local_header=False)
    r = naive.post("/api/v1/external-sims", files={"file": ("r.html", real_html, "text/html")})
    assert r.status_code == 403


def test_reader_never_needs_the_ex5(tmp_path):
    reps, members = read_members(REAL_HTML.name, REAL_HTML.read_bytes())
    assert len(reps) == 1 and reps[0].deals
