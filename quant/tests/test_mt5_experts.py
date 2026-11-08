"""Safety locks of the MT5 tooling (mt5/): our experts can only run inside the Strategy Tester; the runner never
handles credentials, never allows live trading and never launches a third-party .ex5."""

from __future__ import annotations

import re
from pathlib import Path

MT5 = Path(__file__).resolve().parents[2] / "mt5"
EXPERTS = sorted((MT5 / "experts").glob("*.mq5"))
TESTER_GUARD = re.compile(r"if\s*\(\s*!\s*MQLInfoInteger\s*\(\s*MQL_TESTER\s*\)\s*\)")
ORDER_CALLS = re.compile(r"\b(OrderSend|OrderSendAsync|PositionOpen|\.Buy\(|\.Sell\(|BuyLimit|SellLimit|BuyStop|SellStop)")


def test_every_expert_refuses_to_start_outside_the_tester():
    assert {p.stem for p in EXPERTS} == {"ATO_Baseline", "ATO_ExportBars"}  # a new expert is added consciously
    for p in EXPERTS:
        init = p.read_text().split("int OnInit()")[1].split("\n  }")[0]
        assert TESTER_GUARD.search(init) and "INIT_FAILED" in init, p.name


def test_the_bar_export_contains_no_order_function():
    src = (MT5 / "experts" / "ATO_ExportBars.mq5").read_text()
    assert ORDER_CALLS.search(src) is None and "Trade.mqh" not in src


def test_orders_of_the_baseline_are_preceded_by_a_second_tester_lock():
    src = (MT5 / "experts" / "ATO_Baseline.mq5").read_text()
    first_order = ORDER_CALLS.search(src).start()
    guards = [m.start() for m in TESTER_GUARD.finditer(src)]
    assert len(guards) == 2 and guards[1] < first_order
    assert "AccountInfoString" not in src and "ACCOUNT_LOGIN" not in src  # no account identity read


def test_the_runner_forbids_live_trading_and_handles_no_credential():
    src = (MT5 / "run_tester.py").read_text()
    assert "AllowLiveTrading=0" in src and "AllowDllImport=0" in src and "ShutdownTerminal=1" in src
    assert not re.search(r"(?i)\b(login|password)\s*=", src)
    assert 'Expert=ATO\\\\{expert}' in src  # only our folder
    calls = re.findall(r'run_test\("([^"]+)"', src)
    assert set(calls) == {"ATO_Baseline", "ATO_ExportBars"}
