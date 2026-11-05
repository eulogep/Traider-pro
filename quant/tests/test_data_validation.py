"""Market Data Manager: validation, timezones, gaps (never filled), fingerprints."""

import io

import pandas as pd
import pytest

from ai_trader_optimizer.data import fingerprint, import_csv, synthetic_dataset, validate_bars

from conftest import flat_bar, make_bars


def csv_bytes(df: pd.DataFrame, ts_format=None) -> bytes:
    out = df.copy()
    if ts_format:
        out["timestamp"] = out["timestamp"].dt.strftime(ts_format)
    return out.to_csv(index=False).encode()


def codes(rep):
    return {i.code for i in rep.issues}


def good(n=10):
    return make_bars([flat_bar(100 + i * 0.01) for i in range(n)])


def test_valid_file_accepted_with_utc_conversion():
    rep, df = validate_bars(csv_bytes(good()))
    assert rep.ok and df is not None and rep.timeframe == "M1"
    assert str(df["timestamp"].dt.tz) == "UTC" and len(df) == 10


def test_missing_columns_rejected():
    rep, df = validate_bars(b"timestamp,open,high,close\n2026-09-07T12:00:00Z,1,2,1.5\n")
    assert df is None and "MISSING_COLUMNS" in codes(rep)


def test_duplicates_rejected_not_dropped():
    d = good()
    d.loc[3, "timestamp"] = d.loc[2, "timestamp"]
    rep, df = validate_bars(csv_bytes(d))
    assert df is None and "DUPLICATED_TIMESTAMP" in codes(rep)
    dup = next(i for i in rep.issues if i.code == "DUPLICATED_TIMESTAMP")
    assert dup.rows == [3, 4]


def test_unsorted_rejected_not_sorted():
    d = good().iloc[[0, 2, 1, 3, 4, 5]]
    rep, df = validate_bars(csv_bytes(d))
    assert df is None and "UNSORTED" in codes(rep)


def test_missing_and_non_numeric_prices_rejected():
    content = csv_bytes(good()).decode().splitlines()
    content[3] = content[3].split(",")[0] + ",,100.2,99.8,100"
    content[5] = content[5].split(",")[0] + ",abc,100.2,99.8,100"
    rep, df = validate_bars("\n".join(content).encode())
    assert df is None and "MISSING_VALUES" in codes(rep)
    assert next(i for i in rep.issues if i.code == "MISSING_VALUES").rows == [3, 5]


def test_invalid_ohlc_and_non_positive_rejected():
    d = good()
    d.loc[2, "high"] = d.loc[2, "low"] - 1
    d.loc[4, ["open", "high", "low", "close"]] = [0, 0, 0, 0]
    rep, df = validate_bars(csv_bytes(d))
    assert df is None and {"INVALID_OHLC", "NON_POSITIVE_PRICE"} <= codes(rep)


def test_naive_timestamps_require_declared_timezone():
    content = csv_bytes(good(), "%Y-%m-%d %H:%M:%S")
    rep, df = validate_bars(content)
    assert df is None and "TZ_MISSING" in codes(rep)
    rep, df = validate_bars(content, source_timezone="Europe/Athens")  # UTC+3 in September
    assert rep.ok and df["timestamp"].iloc[0] == pd.Timestamp("2026-09-07T09:00:00Z")
    rep, _ = validate_bars(content, source_timezone="Mars/Olympus")
    assert "TZ_UNKNOWN" in codes(rep)


def test_explicit_offsets_across_dst_change_are_consistent():
    # Paris DST ends 2026-10-25 03:00 CEST -> 02:00 CET. Same UTC minutes, two different offsets.
    utc = pd.date_range("2026-10-25T00:57:00Z", periods=6, freq="min")
    local = utc.tz_convert("Europe/Paris")
    text = "timestamp,open,high,low,close\n" + "".join(
        f"{t.isoformat()},100,100.2,99.8,100\n" for t in local)
    assert "+02:00" in text and "+01:00" in text
    rep, df = validate_bars(text.encode())
    assert rep.ok and (df["timestamp"].values == utc.values).all() and len(rep.gaps) == 0


def test_dst_ambiguous_local_time_rejected():
    # 02:30 happens twice in Paris on 2026-10-25: never guess.
    times = pd.date_range("2026-10-25 02:28", periods=5, freq="min")
    text = "timestamp,open,high,low,close\n" + "".join(f"{t:%Y-%m-%d %H:%M:%S},100,100.2,99.8,100\n" for t in times)
    rep, df = validate_bars(text.encode(), source_timezone="Europe/Paris")
    assert df is None and "TZ_AMBIGUOUS" in codes(rep)


def test_dst_nonexistent_local_time_rejected():
    times = pd.date_range("2026-03-29 02:00", periods=3, freq="min")  # does not exist in Paris
    text = "timestamp,open,high,low,close\n" + "".join(f"{t:%Y-%m-%d %H:%M:%S},100,100.2,99.8,100\n" for t in times)
    rep, df = validate_bars(text.encode(), source_timezone="Europe/Paris")
    assert df is None and "TZ_AMBIGUOUS" in codes(rep)


def test_mixed_timezone_information_rejected():
    lines = csv_bytes(good()).decode().splitlines()
    lines[2] = lines[2].replace("+00:00", "")
    rep, df = validate_bars("\n".join(lines).encode())
    assert df is None and "TZ_MIXED" in codes(rep)


def test_gaps_detected_classified_and_never_filled():
    times = list(pd.date_range("2026-09-11T20:50Z", periods=10, freq="min"))  # Friday
    times += list(pd.date_range("2026-09-13T22:00Z", periods=10, freq="min"))  # Sunday reopen
    times = times[:15] + times[17:]  # + intraday hole of 2 bars
    d = make_bars([flat_bar()] * len(times), times=pd.DatetimeIndex(times))
    rep, df = validate_bars(csv_bytes(d))
    assert rep.ok and len(df) == len(d)  # nothing invented
    cats = rep.gaps["category"].tolist()
    assert cats == ["week-end", "intrajournalier — à vérifier"]
    assert rep.gaps["missing_bars"].tolist()[1] == 2
    assert "INTRADAY_GAPS" in codes(rep)


def test_misaligned_and_irregular_timestamps_rejected():
    d = good()
    d.loc[5:, "timestamp"] = d.loc[5:, "timestamp"] + pd.Timedelta(seconds=30)
    rep, df = validate_bars(csv_bytes(d))
    assert df is None and ({"IRREGULAR_SPACING", "MISALIGNED"} & codes(rep))


def test_mt5_export_format_parsed():
    text = ("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
            "2026.09.07\t12:00:00\t3900.10\t3900.50\t3899.90\t3900.20\t55\t0\t25\n"
            "2026.09.07\t12:01:00\t3900.20\t3900.60\t3900.00\t3900.40\t40\t0\t30\n"
            "2026.09.07\t12:02:00\t3900.40\t3900.70\t3900.10\t3900.30\t41\t0\t27\n")
    rep, df = validate_bars(text.encode(), source_timezone="UTC")
    assert rep.ok and rep.detected_format == "mt5"
    assert df["close"].tolist() == [3900.20, 3900.40, 3900.30]
    assert rep.stats["spread_points_median"] == 27


def test_expected_timeframe_mismatch():
    rep, df = validate_bars(csv_bytes(good()), expected_timeframe="M5")
    assert df is None and "TIMEFRAME_MISMATCH" in codes(rep)


def test_fingerprint_deterministic_and_sensitive():
    a = synthetic_dataset()
    b = synthetic_dataset()
    assert a.meta.dataset_id == b.meta.dataset_id
    bars = a.bars.copy()
    bars.loc[100, "close"] += 0.01
    assert fingerprint(bars, "XAUUSD-DEMO", "M1", "bid") != a.meta.dataset_id
    assert a.meta.kind.value == "synthetic" and "synthétiques" in a.meta.name


def test_import_csv_roundtrip_preserves_exact_prices():
    d = good(50)
    d["close"] = d["close"] + 1e-7
    d["high"] = d[["high", "close"]].max(axis=1)
    rep, ds = import_csv(csv_bytes(d), name="x", symbol="xauusd", source_label="broker X")
    assert rep.ok and ds.meta.symbol == "XAUUSD" and ds.meta.raw_sha256
    assert (ds.bars["close"].to_numpy() == pd.read_csv(io.BytesIO(csv_bytes(d)), float_precision="round_trip")["close"].to_numpy()).all()
    assert ds.meta.kind.value == "historical"


@pytest.mark.parametrize("bad", [b"", b"just text without structure"])
def test_garbage_files_rejected(bad):
    rep, df = validate_bars(bad)
    assert df is None and not rep.ok
