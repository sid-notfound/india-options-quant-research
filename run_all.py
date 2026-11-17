# Author: Siddhant Shukla <sidz0124@gmail.com>
"""End-to-end pipeline: download -> parse -> analytics -> backtests -> figures -> PDF.

Usage:
  python run_all.py                 # full run (downloads are cached, so re-runs are fast)
  python run_all.py --skip-download # reuse cached NSE files and Yahoo prices
  python run_all.py --from figures  # start from a later stage
"""
import argparse
import time
import warnings

warnings.filterwarnings("ignore")

STAGES = ["download", "parse", "prices", "surface", "analytics", "backtests", "figures", "pdf"]


def stage_download():
    from src.data import download_nse
    download_nse.run()


def stage_parse():
    from src.data import parse_bhavcopy
    parse_bhavcopy.run()


def stage_prices():
    import pandas as pd

    import config as C
    from src.data import download_prices, universe
    panel = pd.read_parquet(C.PROCESSED / "fo_panel.parquet", columns=["inst", "symbol"])
    universe.sector_map()
    download_prices.download(universe.stock_universe(panel) + ["NIFTY", "BANKNIFTY", "INDIAVIX"])
    universe.participants()


def stage_surface():
    from src.analytics import surface
    surface.run()


def stage_analytics():
    from src.analytics import eov, events, participants, volume, vrp
    volume.run()
    participants.run()
    vrp.run()
    eov.run()
    events.run()


def stage_backtests():
    from src.backtest import call_spreads, straddle_volscore
    print(straddle_volscore.run().round(3).to_string())
    print(call_spreads.run().round(3).to_string())


def stage_figures():
    from src.report import figures
    figures.run()


def stage_pdf():
    from src.report import build_pdf
    build_pdf.build()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--from", dest="start", choices=STAGES, default="download")
    args = ap.parse_args()
    stages = STAGES[STAGES.index(args.start):]
    if args.skip_download:
        stages = [s for s in stages if s not in ("download", "prices")]
        import config as C
        from src.data import universe
        if (C.RAW_PART).exists():
            universe.participants()
    for s in stages:
        t = time.time()
        print(f"\n=== {s} ===")
        globals()[f"stage_{s}"]()
        print(f"=== {s} done in {time.time() - t:.0f}s ===")


if __name__ == "__main__":
    main()
