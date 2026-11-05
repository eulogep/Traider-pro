"""Write examples/SYNTHETIQUE_demo_xauusd_m1.csv (FAKE prices) to try the CSV import screen."""

from pathlib import Path

from ai_trader_optimizer.data import synthetic_m1_frame

out = Path(__file__).resolve().parents[1] / "examples" / "SYNTHETIQUE_demo_xauusd_m1.csv"
df = synthetic_m1_frame(seed=2026, days=3)
df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
df.round(2).to_csv(out, index=False)
print(out)
