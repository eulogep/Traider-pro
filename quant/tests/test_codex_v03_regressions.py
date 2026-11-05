"""Regressions for the defects reproduced by the independent Codex audit of V0.3 (2026-11-04).

Evidence: docs/audits/codex-v03-2026-11-04/ (probes.py, evidence.json). Each test encodes the
adversarial intent of a Codex probe against the V0.3.1 interfaces.
"""

import json

import pandas as pd
import pytest

from ai_trader_optimizer.api import create_app
from ai_trader_optimizer.backtest import BacktestConfig, run_backtest
from ai_trader_optimizer.data import synthetic_dataset
from ai_trader_optimizer.storage import LabCatalog, ReproducibilityError

try:
    from ai_trader_optimizer.storage import CorruptRunError
except ImportError:  # V0.3: no such error -> corruption is never reported
    class CorruptRunError(Exception):
        pass
from ai_trader_optimizer.strategies import load_catalog

from conftest import LocalClient, base_config, flat_bar, make_dataset, scripted

BASELINE = "baseline.ema_trend_3bars@1.0.0"


@pytest.fixture
def stored(lab_dir):
    cat = LabCatalog()
    ds = synthetic_dataset(days=3)
    cat.save_dataset(ds)
    res = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig())
    assert len(res.trades) > 0
    cat.save_run(res)
    return cat, res


def _rewrite(path, fn):
    path.write_bytes(fn(path.read_bytes()))


# ============================================================== B2 — integrity of stored runs
def test_b2_tampered_metrics_detected_on_read_and_by_api(stored):
    cat, res = stored
    p = cat.run_dir(res.run_id) / "metrics.json"
    m = json.loads(p.read_text())
    m["net_pnl"] = 987654321  # Codex probe "tampered_metrics"
    p.write_text(json.dumps(m))
    with pytest.raises(CorruptRunError, match="metrics.json"):
        cat.load_run(res.run_id)
    client = LocalClient(create_app(cat))
    r = client.get(f"/api/v1/backtests/{res.run_id}")
    assert r.status_code == 409 and "987654321" not in r.text
    rep = client.post(f"/api/v1/backtests/{res.run_id}/reproduce")
    assert rep.status_code == 409  # never "identical: true" on corrupted evidence


@pytest.mark.parametrize("artifact", ["equity.csv.gz", "trades.csv", "decisions.csv", "manifest.json"])
def test_b2_any_tampered_artifact_detected(stored, artifact):
    import gzip
    cat, res = stored
    p = cat.run_dir(res.run_id) / artifact
    if artifact.endswith(".gz"):
        text = gzip.decompress(p.read_bytes()).decode()
        lines = text.split("\n")
        lines[5] = lines[5].rsplit(",", 2)[0] + ",1.0,0"  # change mtm_equity of one point
        p.write_bytes(gzip.compress("\n".join(lines).encode()))
    elif artifact == "manifest.json":
        man = json.loads(p.read_text())
        man["config"]["initial_equity"] = 1.0
        p.write_text(json.dumps(man))
    else:
        _rewrite(p, lambda b: b.replace(b",", b",9", 1) if artifact == "decisions.csv" else
                 b.replace(str(res.trades["net_pnl"].iloc[0]).encode(), b"1000000.0", 1))
    with pytest.raises(CorruptRunError, match=artifact.split(".")[0]):
        cat.load_run(res.run_id)


def test_b2_consistent_forgery_of_files_and_checksums_still_detected(stored):
    """Rewrite trades AND the integrity file coherently: index digest + semantic checks still catch it."""
    from ai_trader_optimizer.storage.integrity import sha256_hex
    cat, res = stored
    d = cat.run_dir(res.run_id)
    trades = d / "trades.csv"
    original = str(res.trades["net_pnl"].iloc[0]).encode()
    trades.write_bytes(trades.read_bytes().replace(original, b"5000.0", 1))
    integ = json.loads((d / "integrity.json").read_text())
    integ["artifacts"]["trades.csv"]["sha256"] = sha256_hex(trades.read_bytes())
    (d / "integrity.json").write_text(json.dumps(integ))
    with pytest.raises(CorruptRunError):
        cat.load_run(res.run_id)


def test_b2_semantic_checks_catch_internally_inconsistent_results(stored):
    """Even with matching checksums (e.g. a buggy writer), journal / equity / metrics must agree."""
    from ai_trader_optimizer.storage.integrity import check_consistency
    _, res = stored
    bad = res.metrics.copy()
    bad["net_pnl"] = res.metrics["net_pnl"] + 1.0
    problems = check_consistency(res.trades, res.decisions, res.equity, bad, res.manifest)
    assert any("net_pnl" in p for p in problems)
    assert check_consistency(res.trades, res.decisions, res.equity, res.metrics, res.manifest) == []


def test_b2_published_run_cannot_be_silently_replaced(stored):
    cat, res = stored
    before = cat.load_run(res.run_id).metrics["net_pnl"]
    res.equity.loc[:, "mtm_equity"] = 1.0  # Codex probe "overwrite_same_hash"
    res.metrics["net_pnl"] = 123456
    with pytest.raises(ReproducibilityError):
        cat.save_run(res)
    assert cat.load_run(res.run_id).metrics["net_pnl"] == before


def test_b2_identical_save_is_idempotent_without_rewrite(stored):
    cat, res = stored
    d = cat.run_dir(res.run_id)
    mtimes = {p.name: p.stat().st_mtime_ns for p in d.iterdir()}
    again = run_backtest(cat.load_dataset(res.manifest["dataset"]["dataset_id"]),
                         load_catalog().specs[BASELINE], BacktestConfig())
    cat.save_run(again)
    assert {p.name: p.stat().st_mtime_ns for p in d.iterdir()} == mtimes


def test_b2_reproduce_separates_determinism_from_storage_integrity(stored):
    cat, res = stored
    client = LocalClient(create_app(cat))
    body = client.post(f"/api/v1/backtests/{res.run_id}/reproduce").json()
    assert body["deterministic"] is True and body["artifacts_intact"] is True and body["identical"] is True
    assert body["stored_hash"] == body["new_hash"] == res.manifest["result_hash"]
    assert len(body["new_hash"]) == 64


def test_b2_result_hash_covers_metrics_and_equity():
    ds = synthetic_dataset(days=3)
    res = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig())
    from ai_trader_optimizer.storage.integrity import result_fingerprint
    h = result_fingerprint(res.trades, res.decisions, res.equity, res.metrics)
    assert h == res.manifest["result_hash"]
    eq = res.equity.copy()
    eq.loc[10, "mtm_equity"] += 1e-9
    assert result_fingerprint(res.trades, res.decisions, eq, res.metrics) != h
    m = dict(res.metrics, win_rate_pct=1.0)
    assert result_fingerprint(res.trades, res.decisions, res.equity, m) != h


# ============================================================== B3 — IS / OOS boundary
def _b3_dataset():
    bars = [flat_bar()] * 11  # 11 M1 bars 12:00 .. 12:10
    bars[5] = (100, 104, 99.8, 103)  # the 12:05 bar touches the TP
    return make_dataset(bars)


def test_b3_codex_example_trade_is_counted_in_exactly_one_segment():
    from ai_trader_optimizer.ai.validation import chronological_split
    ds = _b3_dataset()
    sp, st = scripted({4: (1, 2.0, 3.0)})  # signal at the close of 12:04 -> entry at 12:05 open
    cut = chronological_split(ds.bars["timestamp"].iloc[0], ds.bars["timestamp"].iloc[-1], 0.5)  # Codex: 12:05
    assert cut.train_end == pd.Timestamp("2026-09-07T12:05Z")
    is_ = run_backtest(ds, sp, base_config(trade_end=cut.train_end.isoformat()), strategy=st)
    oos = run_backtest(ds, sp, base_config(trade_start=cut.test_start.isoformat()), strategy=st)
    all_trades = pd.concat([is_.trades, oos.trades])
    assert len(all_trades) == 1, (is_.trades, oos.trades)
    assert all_trades.iloc[0]["entry_time"] >= cut.test_start  # entry at 12:05 belongs to OOS
    assert is_.trades.empty


def test_b3_in_sample_never_uses_a_bar_that_closes_after_the_cut():
    ds = _b3_dataset()
    sp, st = scripted({})
    r = run_backtest(ds, sp, base_config(trade_end="2026-09-07T12:05:00Z"), strategy=st)
    assert r.equity["timestamp"].max() == pd.Timestamp("2026-09-07T12:04Z")  # bar 12:04 closes at 12:05
    r = run_backtest(ds, sp, base_config(trade_end="2026-09-07T12:05:30Z"), strategy=st)  # unaligned cut
    assert r.equity["timestamp"].max() == pd.Timestamp("2026-09-07T12:04Z")  # 12:05 closes at 12:06 > cut


def test_b3_unaligned_oos_start_rounds_to_next_bar_open():
    ds = _b3_dataset()
    sp, st = scripted({4: (1, 2.0, 30.0), 5: (1, 2.0, 30.0)})
    r = run_backtest(ds, sp, base_config(trade_start="2026-09-07T12:05:30Z"), strategy=st)
    assert (r.trades["entry_time"] >= pd.Timestamp("2026-09-07T12:06Z")).all()
    assert r.equity["timestamp"].min() == pd.Timestamp("2026-09-07T12:06Z")


def test_b3_position_open_at_in_sample_end_is_closed_at_last_in_sample_close():
    ds = _b3_dataset()
    sp, st = scripted({1: (1, 2.0, 30.0)})  # entry 12:02, TP never reached
    r = run_backtest(ds, sp, base_config(trade_end="2026-09-07T12:05:00Z"), strategy=st)
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "END_OF_DATA" and t["exit_time"] == pd.Timestamp("2026-09-07T12:04Z")


def test_b3_compare_variants_segments_are_disjoint(lab_dir):
    from ai_trader_optimizer.services import compare_variants
    cat = LabCatalog()
    ds = synthetic_dataset(days=6)
    cat.save_dataset(ds)
    spec = load_catalog().specs[BASELINE]
    table = compare_variants(cat, ds.meta.dataset_id, spec, BacktestConfig(), "rr", [1.0, 2.0])
    assert set(table["segment"]) == {"in-sample", "hors échantillon"}
    for v, g in table.groupby("valeur"):
        is_end = pd.Timestamp(g.loc[g["segment"] == "in-sample", "evaluated_until"].iloc[0])
        oos_start = pd.Timestamp(g.loc[g["segment"] == "hors échantillon", "evaluated_from"].iloc[0])
        assert is_end <= oos_start, v


# ============================================================== I1 — non-finite / out-of-range financial values
def _api_with_demo(lab_dir):
    cat = LabCatalog()
    ds = synthetic_dataset(days=3)
    cat.save_dataset(ds)
    return cat, ds, LocalClient(create_app(cat))


@pytest.mark.parametrize("raw_body", [
    '{"initial_equity": 1e309}',                     # overflowing JSON exponent -> inf (Codex "infinite_api")
    '{"initial_equity": "1e309"}',                   # numeric string
    '{"initial_equity": "10000"}',                   # numeric strings are refused for money fields
    '{"initial_equity": 1e13}',                      # above operational bound
    '{"costs": {"spread": 1e309}}',
    '{"costs": {"slippage": -0.0001}}',
    '{"contract": {"contract_size": 1e309, "min_lot": 0.01, "lot_step": 0.01}}',
    '{"risk": {"risk_per_trade_pct": 1e309}}',
    '{"strategy_params": {"rr": 1e309}}',
    '{"strategy_params": {"sl_atr_mult": "1.5"}}',
    '{"initial_equity": true}',
])
def test_i1_invalid_numbers_rejected_before_simulation(lab_dir, raw_body):
    cat, ds, client = _api_with_demo(lab_dir)
    body = f'{{"dataset_id": "{ds.meta.dataset_id}", "strategy_key": "{BASELINE}", "config": {raw_body}}}'
    r = client.post("/api/v1/backtests", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.text
    assert client.get("/api/v1/backtests").json() == []


@pytest.mark.parametrize("change", [{"initial_equity": float("inf")}, {"initial_equity": float("nan")},
                                    {"costs": {"spread": float("inf")}}, {"costs": {"commission_per_lot_per_side": float("nan")}}])
def test_i1_models_refuse_non_finite_values(change):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        BacktestConfig(**change)


def test_i1_non_finite_size_is_refused_by_the_guardian(monkeypatch):
    import ai_trader_optimizer.risk.guardian as g
    sp, st = scripted({0: (1, 2.0, 3.0)})
    ds = make_dataset([flat_bar(), (100, 101, 99.5, 100.5), (100.5, 104, 100, 103), flat_bar(103)])
    monkeypatch.setattr(g, "position_size", lambda *a, **k: (float("inf"), 211.0))
    r = run_backtest(ds, sp, base_config(), strategy=st)
    assert r.trades.empty and r.decisions.iloc[0]["reasons"] == "GUARDIAN_ERROR"


def test_i1_engine_aborts_on_non_finite_intermediate_without_persisting(lab_dir, monkeypatch):
    """Defence in depth: even a faulty guardian approving an infinite size cannot produce a run."""
    from ai_trader_optimizer.risk.guardian import RiskDecision, RiskGuardian
    cat = LabCatalog()
    sp, st = scripted({0: (1, 2.0, 3.0)})
    ds = make_dataset([flat_bar(), (100, 101, 99.5, 100.5), (100.5, 104, 100, 103), flat_bar(103)])
    monkeypatch.setattr(RiskGuardian, "evaluate", lambda self, p: RiskDecision(True, float("inf"), 25.0, []))
    with pytest.raises(ValueError, match="non fini"):
        run_backtest(ds, sp, base_config(), strategy=st)
    assert cat.list_runs().empty


# ============================================================== I5 / I6 / I7 — dataset identity & provenance
def _csv(frame: pd.DataFrame, fmt="%Y-%m-%dT%H:%M:%S.%fZ") -> bytes:
    out = frame.copy()
    out["timestamp"] = out["timestamp"].dt.strftime(fmt)
    return out.to_csv(index=False).encode()


FORM = {"name": "XAU", "source": "test broker", "kind": "historical"}


@pytest.mark.parametrize("symbol", ["xauusd", "XAUUSD", " XauUsd ", "xauusd.m", "XAUUSD-DEMO"])
def test_i5_symbol_normalised_before_identity_and_usable(lab_dir, symbol):
    from conftest import make_bars
    cat = LabCatalog()
    client = LocalClient(create_app(cat))
    bars = make_bars([flat_bar(100 + i * 0.01) for i in range(300)])
    r = client.post("/api/v1/datasets/import", data={**FORM, "symbol": symbol}, files={"file": ("x.csv", _csv(bars))})
    assert r.status_code == 201, r.text
    meta = r.json()["dataset"]
    assert meta["symbol"] == symbol.strip().upper()
    cat.load_dataset(meta["dataset_id"])  # V0.3: "altéré sur disque" for lowercase input
    run = client.post("/api/v1/backtests", json={"dataset_id": meta["dataset_id"], "strategy_key": BASELINE})
    assert run.status_code == 201, run.text
    same = {"xauusd": "XAUUSD", " XauUsd ": "XAUUSD"}
    if symbol in same:  # case/spacing variants of one symbol are one identity
        ref = client.post("/api/v1/datasets/import", data={**FORM, "symbol": "XAUUSD"},
                          files={"file": ("x.csv", _csv(bars))}).json()["dataset"]["dataset_id"]
        assert ref == meta["dataset_id"]


def test_i6_fractional_seconds_rejected_not_truncated():
    from ai_trader_optimizer.data import validate_bars

    from conftest import make_bars
    bars = make_bars([flat_bar()] * 20)
    bars["timestamp"] = bars["timestamp"] + pd.Timedelta(milliseconds=500)  # Codex "fractional_timestamp"
    rep, df = validate_bars(_csv(bars))
    assert df is None and any(i.code == "MISALIGNED" for i in rep.errors())


def test_i6_tiny_price_difference_changes_identity_and_roundtrips_exactly(lab_dir):
    from ai_trader_optimizer.data import dataset_from_frame
    from ai_trader_optimizer.safety import DataKind

    from conftest import make_bars
    f = make_bars([flat_bar()] * 30)
    f2 = f.copy()
    f2.loc[0, "close"] += 1e-8  # Codex "dataset_precision_collision"
    a = dataset_from_frame(f, name="a", symbol="XAUUSD", source_label="t", kind=DataKind.SYNTHETIC)
    b = dataset_from_frame(f2, name="b", symbol="XAUUSD", source_label="t", kind=DataKind.SYNTHETIC)
    assert a.meta.dataset_id != b.meta.dataset_id
    cat = LabCatalog()
    cat.save_dataset(b)
    back = cat.load_dataset(b.meta.dataset_id)
    pd.testing.assert_frame_equal(back.bars, b.bars)  # what is simulated == what was accepted


def test_i7_conflicting_provenance_refused_and_history_kept(lab_dir):
    from conftest import make_bars
    cat = LabCatalog()
    client = LocalClient(create_app(cat))
    raw = _csv(make_bars([flat_bar(100 + i * 0.01) for i in range(300)]))
    a = client.post("/api/v1/datasets/import", data={**FORM, "symbol": "XAUUSD", "kind": "synthetic",
                                                     "source": "générateur"}, files={"file": ("neutral.csv", raw)})
    assert a.status_code == 201
    did = a.json()["dataset"]["dataset_id"]
    b = client.post("/api/v1/datasets/import", data={**FORM, "symbol": "XAUUSD", "kind": "historical",
                                                     "source": "claimed broker"}, files={"file": ("neutral.csv", raw)})
    assert b.status_code == 409, b.text  # V0.3: 201 and silent relabel
    assert cat.dataset_meta(did).kind.value == "synthetic"
    c = client.post("/api/v1/datasets/import", data={**FORM, "symbol": "XAUUSD", "kind": "synthetic",
                                                     "source": "même générateur, 2e déclaration"},
                    files={"file": ("neutral.csv", raw)})
    assert c.status_code == 201 and c.json()["dataset"]["dataset_id"] == did
    history = cat.dataset_provenance(did)
    assert [h["source"] for h in history] == ["générateur", "même générateur, 2e déclaration"]
    assert cat.dataset_meta(did).source == "générateur"  # first declaration is never replaced


def test_i7_historical_label_says_declared_not_verified(lab_dir):
    from ai_trader_optimizer.safety import DATA_KIND_LABELS_FR, DataKind
    assert "déclaré" in DATA_KIND_LABELS_FR[DataKind.HISTORICAL]


# ============================================================== I8 — gaps at the open before intrabar touches
# Reference position: entry 100.35 (ask 100.30 + slip), SL 98.35, TP 103.35 ; 0.11 lot ; risk 23.21.
def _run_long(next_bar):
    sp, st = scripted({0: (1, 2.0, 3.0)})
    return run_backtest(make_dataset([flat_bar(), flat_bar(), next_bar, flat_bar(99)]), sp, base_config(), strategy=st)


def test_i8_buy_open_beyond_tp_exits_at_tp_not_sl():
    t = _run_long((105, 106, 97, 99)).trades.iloc[0]  # Codex "open_above_tp": V0.3 gave SL -23.21
    assert t["exit_reason"] == "TP_GAP" and t["exit_price"] == pytest.approx(103.30)
    assert t["net_pnl"] == pytest.approx(31.79)


def test_i8_buy_open_below_sl_exits_at_open():
    t = _run_long((97, 104, 96, 103)).trades.iloc[0]  # high later reaches TP: irrelevant, stop gapped first
    assert t["exit_reason"] == "SL_GAP" and t["exit_price"] == pytest.approx(96.95)


def test_i8_ambiguous_intrabar_both_touched_stays_stop_first():
    t = _run_long((100, 104, 98, 101)).trades.iloc[0]
    assert t["exit_reason"] == "SL" and t["exit_price"] == pytest.approx(98.30)


def _run_short(next_bar):
    # SELL: entry 99.95 (bid - slip), SL 101.95, TP 96.95 ; exits at ASK = BID + 0.30
    sp, st = scripted({0: (-1, 2.0, 3.0)})
    return run_backtest(make_dataset([flat_bar(), flat_bar(), next_bar, flat_bar(100)]), sp, base_config(),
                        strategy=st)


def test_i8_sell_open_beyond_tp_exits_at_tp():
    t = _run_short((96, 103, 95.5, 102)).trades.iloc[0]  # ask open 96.30 <= TP 96.95
    assert t["exit_reason"] == "TP_GAP" and t["exit_price"] == pytest.approx(97.00)  # TP + slippage


def test_i8_sell_open_above_sl_exits_at_ask_open():
    t = _run_short((103, 103.5, 95, 96)).trades.iloc[0]  # ask open 103.30 >= SL 101.95
    assert t["exit_reason"] == "SL_GAP" and t["exit_price"] == pytest.approx(103.35)


def test_i8_sell_ambiguous_intrabar_stop_first():
    t = _run_short((100, 102, 96, 99)).trades.iloc[0]
    assert t["exit_reason"] == "SL" and t["exit_price"] == pytest.approx(102.00)


# ============================================================== M4 — MAE / MFE qualified
def test_m4_excursions_are_proven_lower_bounds_not_post_exit_extremes():
    sp, st = scripted({0: (1, 2.0, 3.0)})
    r = run_backtest(make_dataset([flat_bar(), (100, 1000, 98, 100), flat_bar()]), sp, base_config(), strategy=st)
    t = r.trades.iloc[0]  # Codex "post_exit_excursions": V0.3 reported MFE 899.65 = 449.8 R
    assert t["exit_reason"] == "SL"
    assert t["mfe_price"] == pytest.approx(0.0) and t["mfe_r"] == pytest.approx(0.0)
    assert t["mae_price"] == pytest.approx(2.0)  # the stop level was provably reached
    assert t["excursion_basis"] == "lower_bound_ohlc"
    assert "MAE/MFE" in " ".join(r.manifest["fill_assumptions"])


def test_m4_fully_held_bars_count_entirely():
    sp, st = scripted({0: (1, 2.0, 30.0)})
    r = run_backtest(make_dataset([flat_bar(), (100, 101.35, 99.35, 100.5), flat_bar(100.5)]), sp, base_config(),
                     strategy=st)
    t = r.trades.iloc[0]  # no exit in bar 1 -> its whole range is observed while holding
    assert t["mfe_price"] == pytest.approx(1.0) and t["mae_price"] == pytest.approx(1.0)


# ============================================================== I3 — upload size bounded BEFORE multipart parsing
MUTATION_HEADERS = {"X-ATO-Request": "1"}


def _instrumented(app, seen):
    async def asgi(scope, receive, send):
        async def recv():
            msg = await receive()
            seen["bytes"] += len(msg.get("body", b""))
            return msg
        await app(scope, recv, send)
    return asgi


def test_i3_declared_oversize_rejected_without_reading_body(lab_dir, monkeypatch):
    monkeypatch.setenv("ATO_MAX_UPLOAD_MB", "0.001")  # ~1 KB
    seen = {"bytes": 0}
    client = LocalClient(_instrumented(create_app(LabCatalog()), seen), local_header=False)
    r = client.post("/api/v1/datasets/import", headers=MUTATION_HEADERS,
                    files={"file": ("big.csv", b"x" * (2 * 1024 * 1024), "text/csv")},
                    data={"name": "t", "symbol": "XAUUSD", "source": "t", "kind": "historical"})
    assert r.status_code == 413
    assert seen["bytes"] == 0  # V0.3: 2 097 687 bytes received before the check (Codex)
    assert LabCatalog().list_datasets().empty


def test_i3_streamed_body_without_length_is_cut_at_the_limit(lab_dir, monkeypatch):
    """ASGI-level: count the body chunks actually pulled from the client (no Content-Length)."""
    import asyncio
    monkeypatch.setenv("ATO_MAX_UPLOAD_MB", "0.1")  # 104 857 bytes
    app = create_app(LabCatalog())
    pulled, sent = 0, []

    head = (b'--x\r\nContent-Disposition: form-data; name="file"; filename="big.csv"\r\n'
            b"Content-Type: text/csv\r\n\r\n")

    async def receive():  # a well-formed multipart file part that never ends (2 MB offered)
        nonlocal pulled
        pulled += 1
        chunk = head if pulled == 1 else b"y" * 32768
        return {"type": "http.request", "body": chunk, "more_body": pulled < 64}

    async def send(message):
        sent.append(message)
    scope = {"type": "http", "method": "POST", "path": "/api/v1/datasets/import", "query_string": b"",
             "headers": [(b"host", b"localhost"), (b"x-ato-request", b"1"),
                         (b"content-type", b"multipart/form-data; boundary=x")]}
    asyncio.run(app(scope, receive, send))
    assert sent[0]["status"] == 413
    assert pulled <= 1 + 104857 // 32768 + 1 < 64  # header part + chunks up to the limit, not 2 MB


def test_i3_row_limit_rejects_before_parsing(lab_dir, monkeypatch):
    from conftest import make_bars
    monkeypatch.setenv("ATO_MAX_ROWS", "100")
    client = LocalClient(create_app(LabCatalog()), headers=MUTATION_HEADERS)
    bars = make_bars([flat_bar()] * 300)
    r = client.post("/api/v1/datasets/import", data={**FORM, "symbol": "XAUUSD"}, files={"file": ("x.csv", _csv(bars))})
    assert r.status_code == 413 and "lignes" in r.json()["error"]


def test_i3_heavy_jobs_are_bounded(lab_dir, monkeypatch):
    import threading

    import ai_trader_optimizer.api.app as api_app
    monkeypatch.setenv("ATO_MAX_CONCURRENT_JOBS", "1")
    gate, started = threading.Event(), threading.Event()
    real = api_app.synthetic_dataset

    def slow(*a, **k):
        started.set()
        gate.wait(5)
        return real(*a, **k)
    monkeypatch.setattr(api_app, "synthetic_dataset", slow)
    client = LocalClient(api_app.create_app(LabCatalog()), headers=MUTATION_HEADERS)
    first = {}
    t = threading.Thread(target=lambda: first.setdefault("r", client.post("/api/v1/datasets/demo", json={})))
    t.start()
    started.wait(5)
    second = client.post("/api/v1/datasets/demo", json={"seed": 1})
    gate.set()
    t.join(10)
    assert second.status_code == 429 and first["r"].status_code == 201


def test_i3_storage_quota(lab_dir, monkeypatch):
    monkeypatch.setenv("ATO_MAX_STORAGE_MB", "0.0001")
    client = LocalClient(create_app(LabCatalog()), headers=MUTATION_HEADERS)
    assert client.post("/api/v1/datasets/demo", json={}).status_code == 507


# ============================================================== I4 — mutations from foreign origins / hosts
def _import(client, headers, name="neutral.csv"):
    from conftest import make_bars
    raw = _csv(make_bars([flat_bar(100 + i * 0.01) for i in range(300)]))
    return client.post("/api/v1/datasets/import", headers=headers, files={"file": (name, raw)},
                       data={**FORM, "symbol": "XAUUSD"})


@pytest.mark.parametrize("headers,status", [
    ({"Origin": "https://evil.example", **MUTATION_HEADERS}, 403),        # Codex "cors_write": V0.3 -> 201
    ({"Host": "evil.example", **MUTATION_HEADERS}, 421),                  # DNS rebinding
    ({"Sec-Fetch-Site": "cross-site", **MUTATION_HEADERS}, 403),
    ({}, 403),                                                            # no local request header
    ({"Origin": "http://localhost.evil.example:8080", **MUTATION_HEADERS}, 403),
])
def test_i4_foreign_mutations_refused_and_nothing_written(lab_dir, headers, status):
    cat = LabCatalog()
    client = LocalClient(create_app(cat), local_header=False)
    r = _import(client, headers)
    assert r.status_code == status, r.text
    assert cat.list_datasets().empty


def test_i4_local_ui_origin_is_accepted(lab_dir):
    cat = LabCatalog()
    client = LocalClient(create_app(cat), local_header=False)
    r = _import(client, {"Origin": "http://localhost:8080", **MUTATION_HEADERS})
    assert r.status_code == 201
    assert LocalClient(create_app(cat), headers={"Host": "evil.example"}).get("/api/v1/datasets").status_code == 421


# ============================================================== I2 — research mode vs enforced risk policy
def _cfg_loose():
    return BacktestConfig(risk={"max_trades_per_day": 100, "max_losses_per_day": None, "max_daily_loss_pct": 100,
                                "max_drawdown_pct": 100}).model_dump(mode="json")


def test_i2_research_mode_is_explicit_in_results(lab_dir):
    from ai_trader_optimizer.risk import RiskConfig
    from ai_trader_optimizer.services import save_risk
    cat, ds, client = _api_with_demo(lab_dir)
    client.headers.update(MUTATION_HEADERS)
    save_risk(cat, RiskConfig(max_trades_per_day=1))
    body = client.post("/api/v1/backtests", json={"dataset_id": ds.meta.dataset_id, "strategy_key": BASELINE,
                                                  "config": _cfg_loose()}).json()
    pol = body["manifest"]["risk_policy"]
    assert pol["mode"] == "research" and pol["enforced"] is False and pol["differs_from_saved_profile"] is True


def test_i2_supervised_mode_refuses_looser_limits_and_contract_changes(lab_dir, monkeypatch):
    from ai_trader_optimizer.risk import RiskConfig
    from ai_trader_optimizer.services import save_risk
    monkeypatch.setenv("ATO_RISK_POLICY", "supervised")
    cat, ds, client = _api_with_demo(lab_dir)
    client.headers.update(MUTATION_HEADERS)
    save_risk(cat, RiskConfig(max_trades_per_day=1))
    url, base = "/api/v1/backtests", {"dataset_id": ds.meta.dataset_id, "strategy_key": BASELINE}
    assert client.post(url, json={**base, "config": _cfg_loose()}).status_code == 403  # V0.3: 201, 73 trades
    stricter = BacktestConfig(risk=RiskConfig(max_trades_per_day=1, risk_per_trade_pct=0.1)).model_dump(mode="json")
    ok = client.post(url, json={**base, "config": stricter})
    assert ok.status_code == 201 and ok.json()["manifest"]["risk_policy"]["enforced"] is True
    contract = BacktestConfig(risk=RiskConfig(max_trades_per_day=1)).model_dump(mode="json")
    contract["contract"]["contract_size"] = 1000
    assert client.post(url, json={**base, "config": contract}).status_code == 403
    assert cat.list_runs()["trades"].max() <= 3  # nothing looser was ever stored


# ============================================================== I9 — atomic, concurrent-safe publication
def test_i9_interrupted_publication_leaves_nothing_visible(stored, monkeypatch):
    import os

    import ai_trader_optimizer.storage.catalog as catmod
    cat, res = stored
    ds = cat.load_dataset(res.manifest["dataset"]["dataset_id"])
    other = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig(strategy_params={"rr": 2.0}))

    real_rename = os.rename

    def crash(*a, **k):
        raise OSError("disk unplugged")
    monkeypatch.setattr(catmod.os, "rename", crash)
    with pytest.raises(OSError):
        cat.save_run(other)
    monkeypatch.setattr(catmod.os, "rename", real_rename)
    with pytest.raises(KeyError):
        cat.run_dir(other.run_id)
    assert other.run_id not in set(cat.list_runs()["run_id"])
    assert not list((cat.root / "runs" / ".staging").glob(f"{other.run_id}-*"))
    cat.save_run(other)  # retry succeeds
    assert cat.load_run(other.run_id).manifest["result_hash"] == other.manifest["result_hash"]


def test_i9_leftover_staging_from_a_crash_is_ignored_then_cleaned(stored):
    cat, res = stored
    ds = cat.load_dataset(res.manifest["dataset"]["dataset_id"])
    other = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig(strategy_params={"rr": 2.5}))
    junk = cat.root / "runs" / ".staging" / f"{other.run_id}-deadbeef"
    junk.mkdir(parents=True)
    (junk / "manifest.json").write_text("{}")  # half-written publication
    with pytest.raises(KeyError):
        cat.run_dir(other.run_id)
    cat.save_run(other)
    assert not junk.exists() and cat.load_run(other.run_id)


def test_i9_concurrent_identical_saves_publish_once(stored):
    import threading
    cat, res = stored
    ds = cat.load_dataset(res.manifest["dataset"]["dataset_id"])
    run = run_backtest(ds, load_catalog().specs[BASELINE], BacktestConfig(strategy_params={"rr": 3.0}))
    errors = []

    def save():
        try:
            LabCatalog(cat.root).save_run(run)
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)
    threads = [threading.Thread(target=save) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert list(cat.list_runs()["run_id"]).count(run.run_id) == 1
    assert cat.load_run(run.run_id).manifest["result_hash"] == run.manifest["result_hash"]


# ============================================================== M3 — time zones and windows
@pytest.mark.parametrize("mutate", [
    lambda c: c["risk"].update(day_timezone="Not/AZone"),                       # Codex "bad_timezone": V0.3 500
    lambda c: c.update(trading_hours={"timezone": "Mars/Base", "sessions": ["00:00-23:59"], "weekdays": [0]}),
    lambda c: c.update(trade_start="2026-09-10T00:00:00Z", trade_end="2026-09-08T00:00:00Z"),
    lambda c: c.update(trade_start="2026-09-08T00:00:00Z", trade_end="2026-09-08T00:00:00Z"),
    lambda c: c.update(trade_start="not a date"),
    lambda c: c.update(trade_end="NaT"),
])
def test_m3_invalid_time_inputs_are_422_not_500(lab_dir, mutate):
    cat, ds, client = _api_with_demo(lab_dir)
    client.headers.update(MUTATION_HEADERS)
    cfg = BacktestConfig().model_dump(mode="json")
    mutate(cfg)
    r = client.post("/api/v1/backtests", json={"dataset_id": ds.meta.dataset_id, "strategy_key": BASELINE,
                                               "config": cfg})
    assert r.status_code == 422, r.text


def test_m2_run_summaries_carry_their_currency(stored):
    cat, res = stored
    assert cat.list_runs().iloc[0]["account_currency"] == "USD"
