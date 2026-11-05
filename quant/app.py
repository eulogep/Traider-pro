"""AI Trader Optimizer — Streamlit research lab (French UI).

Launch:  streamlit run app.py
Absolutely no broker connection, no credentials and no live orders.
"""

import streamlit as st

from ai_trader_optimizer import __version__
from ai_trader_optimizer.ui.common import setup_page
from ai_trader_optimizer.ui.pages_lab import dashboard_page, market_data_page, strategy_lab_page
from ai_trader_optimizer.ui.pages_run import backtesting_page, journal_page, risk_page, settings_page

st.set_page_config(page_title="AI Trader Optimizer", page_icon="📊", layout="wide")
setup_page()

pages = {
    "Laboratoire": [
        st.Page(dashboard_page, title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
        st.Page(market_data_page, title="Market Data", icon=":material/database:", url_path="market-data"),
        st.Page(strategy_lab_page, title="Strategy Lab", icon=":material/science:", url_path="strategy-lab"),
        st.Page(backtesting_page, title="Backtesting", icon=":material/query_stats:", url_path="backtesting"),
        st.Page(journal_page, title="Trade Journal", icon=":material/receipt_long:", url_path="journal"),
    ],
    "Contrôle": [
        st.Page(risk_page, title="Risk Management", icon=":material/shield:", url_path="risk"),
        st.Page(settings_page, title="Settings", icon=":material/settings:", url_path="settings"),
    ],
}
nav = st.navigation(pages)
with st.sidebar:
    st.markdown(f"**AI Trader Optimizer** · v{__version__}")
    st.caption("Laboratoire de recherche hors ligne — simulation uniquement. "
               "Aucun résultat ne garantit un gain futur.")
nav.run()
