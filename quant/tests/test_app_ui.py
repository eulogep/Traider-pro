"""Headless UI checks (Streamlit AppTest): every page renders on an empty lab and on a lab
with data; a backtest can be launched from the Backtesting form; synthetic results are flagged."""

from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"
PAGES = {
    "dashboard_page": "pages_lab", "market_data_page": "pages_lab", "strategy_lab_page": "pages_lab",
    "backtesting_page": "pages_run", "journal_page": "pages_run", "risk_page": "pages_run",
    "settings_page": "pages_run",
}


def page_app(func: str) -> AppTest:
    script = (f"from ai_trader_optimizer.ui.common import setup_page\n"
              f"from ai_trader_optimizer.ui.{PAGES[func]} import {func}\n"
              f"setup_page()\n{func}()\n")
    at = AppTest.from_string(script, default_timeout=120)
    at.run()
    return at


def seed_lab():
    from ai_trader_optimizer.backtest import BacktestConfig
    from ai_trader_optimizer.data import synthetic_dataset
    from ai_trader_optimizer.services import run_and_store
    from ai_trader_optimizer.storage import LabCatalog
    from ai_trader_optimizer.strategies import load_catalog

    cat = LabCatalog()
    ds = synthetic_dataset(days=5)
    cat.save_dataset(ds)
    run_and_store(cat, ds.meta.dataset_id, load_catalog().specs["baseline.ema_trend_3bars@1.0.0"], BacktestConfig())


def test_main_app_boots(lab_dir):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception
    assert at.title[0].value == "Tableau de bord"


@pytest.mark.parametrize("func", list(PAGES))
def test_pages_render_on_empty_lab(lab_dir, func):
    at = page_app(func)
    assert not at.exception, at.exception
    assert any("SIMULATION" in m.value for m in at.markdown)


@pytest.mark.parametrize("func", list(PAGES))
def test_pages_render_with_data(lab_dir, func):
    seed_lab()
    at = page_app(func)
    assert not at.exception, at.exception


def test_backtest_launched_from_form_and_flagged_synthetic(lab_dir):
    seed_lab()
    at = page_app("backtesting_page")
    submit = next(b for b in at.button if "Lancer" in b.label)
    submit.click()
    at.run()
    assert not at.exception, at.exception
    assert any("Backtest enregistré" in s.value for s in at.success)
    assert any("synthétiques" in e.value for e in at.error)


def test_reproduce_button_confirms_identical_results(lab_dir):
    seed_lab()
    at = page_app("backtesting_page")
    next(b for b in at.button if b.label == "Reproduire").click()
    at.run()
    assert not at.exception, at.exception
    assert any("Résultats identiques" in s.value for s in at.success)


def test_invalid_contract_is_announced_on_risk_page(lab_dir):
    from ai_trader_optimizer.risk import ContractSpec
    from ai_trader_optimizer.services import default_config, save_defaults
    from ai_trader_optimizer.storage import LabCatalog

    cat = LabCatalog()
    save_defaults(cat, default_config(cat).model_copy(update={"contract": ContractSpec(symbol="XAUUSD")}))
    at = page_app("risk_page")
    assert any("toutes les opérations seront refusées" in e.value for e in at.error)
