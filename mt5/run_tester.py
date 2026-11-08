#!/usr/bin/env python3
"""Drive MetaTrader 5's STRATEGY TESTER from the command line (macOS, Wine build of MT5). Simulation only.

    python3 mt5/run_tester.py compile
    python3 mt5/run_tester.py export   --from 2026.01.01 --to 2026.10.31
    python3 mt5/run_tester.py baseline --from 2026.01.01 --to 2026.10.31 --model 1

* Only OUR experts (mt5/experts/ATO_*) are compiled and run; a third-party .ex5 is never launched.
* The terminal starts on the account already saved in it: no credential is read, passed or stored here.
* `AllowLiveTrading=0` in the launch configuration, and the experts refuse to start outside the tester.
* The terminal closes itself at the end of the test (ShutdownTerminal=1). It refuses to run if MT5 is already open.

Models: 0 every tick, 1 OHLC M1, 2 open prices, 4 every tick based on real ticks.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFIX = Path.home() / "Library/Application Support/net.metaquotes.wine.metatrader5"
WINE = Path("/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine")
MT5 = PREFIX / "drive_c/Program Files/MetaTrader 5"
WIN_MT5 = "C:\\Program Files\\MetaTrader 5"
COMMON = PREFIX / f"drive_c/users/{os.environ.get('USER', 'user')}/AppData/Roaming/MetaQuotes/Terminal/Common/Files/ATO"  # Wine user
OUT = HERE / "results"
ENV = {**os.environ, "WINEPREFIX": str(PREFIX), "WINEDEBUG": "-all"}


def wine(*args: str, timeout: int) -> int:
    # relative paths from the install folder: the space in "Program Files" breaks MetaEditor's /compile: argument
    return subprocess.run([str(WINE), *args], env=ENV, cwd=MT5, timeout=timeout, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False).returncode


def terminal_running() -> bool:
    out = subprocess.run(["ps", "ax", "-o", "command"], capture_output=True, text=True, check=True).stdout
    return "terminal64.exe" in out or "metatester64.exe" in out


def compile_experts() -> None:
    target = MT5 / "MQL5/Experts/ATO"
    target.mkdir(parents=True, exist_ok=True)
    failed = False
    for src in sorted((HERE / "experts").glob("ATO_*.mq5")):
        shutil.copy2(src, target / src.name)
        log = target / f"{src.stem}.log"
        wine("metaeditor64.exe", f"/compile:MQL5\\Experts\\ATO\\{src.name}", "/log", timeout=300)
        text = log.read_bytes().decode("utf-16", errors="replace") if log.exists() else "journal absent"
        last = [ln for ln in text.splitlines() if ln.strip()][-1:]
        ok = (target / f"{src.stem}.ex5").exists() and "Result: 0 errors" in text
        failed |= not ok
        print(("OK    " if ok else "ÉCHEC ") + src.stem, *last)
        if not ok:
            print(text[-1500:])
    if failed:
        sys.exit(1)


def run_test(expert: str, sets: dict, name: str, a) -> Path:
    if terminal_running():
        sys.exit("MetaTrader 5 est ouvert : fermez-le d'abord (le testeur en ligne de commande a besoin du terminal).")
    ini_dir = PREFIX / "drive_c/users/user/Documents/ATO"
    ini_dir.mkdir(parents=True, exist_ok=True)
    (MT5 / "ATO").mkdir(exist_ok=True)  # MT5 does not create the report folder
    report = f"ATO\\{name}"
    lines = ["[Experts]", "AllowLiveTrading=0", "AllowDllImport=0", "", "[Tester]",
             f"Expert=ATO\\{expert}", f"Symbol={a.symbol}", "Period=M1", "Optimization=0", f"Model={a.model}",
             f"FromDate={a.from_date}", f"ToDate={a.to_date}", "ForwardMode=0", f"Deposit={a.deposit}", "Currency=USD",
             f"Leverage={a.leverage}", "ExecutionMode=0", "UseLocal=1", "UseRemote=0", "UseCloud=0", "Visual=0",
             f"Report={report}", "ReplaceReport=1", "ShutdownTerminal=1"]
    if sets:
        set_file = MT5 / "MQL5/Profiles/Tester" / f"{name}.set"
        set_file.parent.mkdir(parents=True, exist_ok=True)
        set_file.write_text("\n".join(f"{k}={v}" for k, v in sets.items()) + "\n", encoding="utf-16")
        lines.append(f"ExpertParameters={name}.set")
    ini = ini_dir / f"{name}.ini"
    ini.write_text("\r\n".join(lines) + "\r\n", encoding="utf-16")
    t0 = time.time()
    print(f"Testeur : {expert} {a.symbol} M1 modèle {a.model}, {a.from_date} → {a.to_date}…", flush=True)
    subprocess.Popen([str(WINE), f"{WIN_MT5}\\terminal64.exe", f"/config:C:\\users\\user\\Documents\\ATO\\{name}.ini"],
                     env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)
    while terminal_running():
        if time.time() - t0 > a.timeout:
            sys.exit(f"Délai dépassé ({a.timeout} s) : le terminal est toujours ouvert, à inspecter.")
        time.sleep(5)
    print(f"Terminé en {time.time() - t0:.0f} s", flush=True)
    return MT5 / "ATO"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["compile", "export", "baseline"])
    ap.add_argument("--from", dest="from_date", default="2026.01.01")
    ap.add_argument("--to", dest="to_date", default="2026.10.31")
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--model", type=int, default=None)
    ap.add_argument("--deposit", type=int, default=10000)
    ap.add_argument("--leverage", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    if a.command == "compile":
        compile_experts()
        return
    OUT.mkdir(exist_ok=True)
    tag = f"{a.symbol}_M1_{a.from_date.replace('.', '')}_{a.to_date.replace('.', '')}"
    if a.command == "export":
        a.model = 2 if a.model is None else a.model  # one tick per bar: the bars are what is exported
        name = a.name or f"export_{tag}"
        run_test("ATO_ExportBars", {"InpFile": f"ATO\\{name}.csv"}, name, a)
        src = COMMON / f"{name}.csv"
        if not src.exists():
            sys.exit(f"Fichier absent : {src}")
        shutil.copy2(src, OUT / src.name)
        print(OUT / src.name, f"{sum(1 for _ in open(src, encoding='ascii')) - 1} bougies")
    else:
        a.model = 1 if a.model is None else a.model
        name = a.name or f"baseline_{tag}_model{a.model}"
        run_test("ATO_Baseline", {"InpSignalsFile": f"ATO\\{name}_decisions.csv"}, name, a)
        for src in [COMMON / f"{name}_decisions.csv", MT5 / "ATO" / f"{name}.htm", MT5 / "ATO" / f"{name}.html"]:
            if src.exists():
                shutil.copy2(src, OUT / src.name)
                print(OUT / src.name)
        if not any((OUT / f"{name}{e}").exists() for e in (".htm", ".html")):
            sys.exit("Rapport HTML absent : voir Tester/logs.")


if __name__ == "__main__":
    main()
