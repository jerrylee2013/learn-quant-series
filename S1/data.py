"""S1 系列共享数据源：从 Cryptocompare 下载 BTC 日线并缓存到 data/raw/btc_daily.csv

功能：
- download_and_cache(start=None, end=None, save_path='data/raw/btc_daily.csv', update=True)
- load_cached(save_path) -> pd.DataFrame

要求：返回包含 ['datetime','open','high','low','close','volume'] 的 DataFrame，index 为 datetime（UTC）。
"""
from __future__ import annotations
import os
import requests
import pandas as pd
import logging
# no local datetime import required
from typing import Optional

API_URL = "https://min-api.cryptocompare.com/data/v2/histoday"


def _fetch_cc(limit: int = 2000, to_ts: Optional[int] = None) -> pd.DataFrame:
    params = {
        "fsym": "BTC",
        "tsym": "USDT",
        "limit": limit,
    }
    if to_ts:
        params["toTs"] = to_ts
    r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    data = j.get("Data", {}).get("Data", [])
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # cryptocompare fields: time, high, low, open, close, volumefrom, volumeto
    df = df.rename(columns={
        "time": "datetime",
        "volumeto": "volume",
    })
    df["datetime"] = pd.to_datetime(df["datetime"], unit="s", utc=True)
    df = df[["datetime", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def load_cached(save_path: str = "data/raw/btc_daily.csv") -> pd.DataFrame:
    if not os.path.exists(save_path):
        return pd.DataFrame()
    df = pd.read_csv(save_path, parse_dates=["datetime"]) 
    # ensure tz-aware UTC
    if df["datetime"].dt.tz is None:
        df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    return df


def download_and_cache(start: Optional[str] = None,
                       end: Optional[str] = None,
                       save_path: str = "data/raw/btc_daily.csv",
                       update: bool = True) -> pd.DataFrame:
    """下载数据并缓存。

    start/end 可以是 ISO 日期字符串（例如 '2020-01-01'）。
    如果 update=True 且已有缓存，则只追加缺失的最新数据。
    返回完整 DataFrame（按 datetime 升序）。
    """
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cached = load_cached(save_path)

    if cached.empty:
        # fetch full range (limit covers ~2000 days)
        logging.info("No cache found, fetching full range (limit=2000)")
        df = _fetch_cc(limit=2000)
    else:
        if not update:
            df = cached.copy()
        else:
            # incremental update: fetch missing days after the last cached date in batches
            last_date = pd.to_datetime(cached["datetime"].max())
            if last_date.tz is None:
                last_date = last_date.tz_localize("UTC")
            today = pd.Timestamp.utcnow()
            if today.tz is None:
                today = today.tz_localize("UTC")
            missing_days = (today.normalize() - last_date.normalize()).days
            if missing_days <= 0:
                logging.info("Cache is up-to-date; no fetch needed")
                df = cached.copy()
            else:
                logging.info(f"Need to fetch {missing_days} missing days since {last_date.date()}")
                parts = []
                fetched_total = 0
                # iterate in batches up to 2000 days per request
                while missing_days > 0:
                    to_fetch = min(missing_days, 2000)
                    # set to_ts to last_date + to_fetch days (inclusive)
                    to_ts_date = (last_date + pd.Timedelta(days=to_fetch))
                    to_ts = int(to_ts_date.tz_convert("UTC").timestamp()) if to_ts_date.tz is not None else int(to_ts_date.tz_localize("UTC").timestamp())
                    logging.info(f"Fetching batch: last_date={last_date.date()} to to_ts={pd.to_datetime(to_ts, unit='s').date()} (limit={to_fetch})")
                    df_batch = _fetch_cc(limit=to_fetch, to_ts=to_ts)
                    logging.info(f"Batch returned {len(df_batch)} rows")
                    if df_batch.empty:
                        break
                    parts.append(df_batch)
                    fetched_total += len(df_batch)
                    # advance last_date to max datetime in df_batch
                    last_date = pd.to_datetime(df_batch["datetime"].max())
                    if last_date.tz is None:
                        last_date = last_date.tz_localize("UTC")
                    missing_days = (today.normalize() - last_date.normalize()).days
                    # safety: avoid infinite loop
                    if len(parts) > 50:
                        logging.warning("Too many batches, stopping to avoid infinite loop")
                        break
                if parts:
                    df_new = pd.concat(parts, ignore_index=True)
                else:
                    df_new = pd.DataFrame()
                # combine and dedupe (keep earliest occurrences)
                df = pd.concat([cached, df_new], ignore_index=True) if not df_new.empty else cached.copy()
                df = df.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)

    # filter by start/end
    if start:
        start_ts = pd.to_datetime(start).tz_localize("UTC") if pd.to_datetime(start).tz is None else pd.to_datetime(start)
        df = df[df["datetime"] >= start_ts]
    if end:
        end_ts = pd.to_datetime(end).tz_localize("UTC") if pd.to_datetime(end).tz is None else pd.to_datetime(end)
        df = df[df["datetime"] <= end_ts]

    # write cache (full range)
    try:
        df.to_csv(save_path, index=False)
    except Exception:
        pass
    return df


if __name__ == "__main__":
    # quick CLI: python S1/data.py --start 2020-01-01 --end 2023-01-01
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--save", default="data/raw/btc_daily.csv")
    p.add_argument("--no-update", action="store_true")
    args = p.parse_args()
    df = download_and_cache(start=args.start, end=args.end, save_path=args.save, update=not args.no_update)
    print(f"Downloaded {len(df)} rows, saved to {args.save}")
