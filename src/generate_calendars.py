import calendar
import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

DATA_DIR = Path("data")
META = DATA_DIR / "station_metadata.csv"
FILES = DATA_DIR / "heatrisk_files"
OUT_IMG = Path("docs/img")
OUT_JS = Path("docs/stations.js")

COLORS = ["#d9f4cd", "#ffde59", "#fd933c", "#cc0000", "#8f1eae"]
MISSING = "#d9d9d9"

# Option 1 analytics: first day when >= X% of years meet/exceed threshold
PERCENT_THRESHOLD = 0.60  # 60%
AVG_YEAR = 2026

PAT = re.compile(r"HeatRisk-v[\d.]+-(?P<id>[A-Z0-9]+)-(?P<year>\d{4})\.csv")
WEEKDAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

def _find_col(df: pd.DataFrame, wanted: list[str]) -> str:
    cols = {c.lower(): c for c in df.columns}
    for w in wanted:
        if w.lower() in cols:
            return cols[w.lower()]
    raise KeyError(f"Missing required column. Wanted one of: {wanted}. Found: {list(df.columns)}")

def load_meta() -> pd.DataFrame:
    df = pd.read_csv(META, sep=None, engine="python")
    df = df.rename(columns={"GHCN": "id", "NAME": "name", "STATE": "state"})
    return df[["id", "name", "state"]]

def write_manifest(stations: list[dict]) -> None:
    lines = ["window.HEATRISK_STATIONS = ["]
    for s in stations:
        years = ", ".join(map(str, s["years"]))
        name = (s.get("name") or "").replace('"', '\"')
        state = (s.get("state") or "").replace('"', '\"')
        lines.append(f'  {{ id: "{s["id"]}", name: "{name}", state: "{state}", years: [{years}] }},')
    lines.append("];")
    OUT_JS.write_text("\n".join(lines), encoding="utf-8")

def fmt_month_day(md):
    if md is None:
        return "N/A"
    m, d = md
    return f"{calendar.month_abbr[m]} {d:02d}"

def first_day_by_percent(all_year_values: dict[int, dict[tuple[int,int], int]], threshold: int, pct: float):
    years = list(all_year_values.keys())
    n = len(years)
    if n == 0:
        return None
    required = int((pct * n) + 0.999)  # ceil
    for m in range(1, 13):
        for d in range(1, calendar.monthrange(2021, m)[1] + 1):
            count = 0
            for y in years:
                v = all_year_values[y].get((m, d), None)
                if v is not None and v >= threshold:
                    count += 1
            if count >= required:
                return (m, d)
    return None

def footer_for_station(all_year_values: dict[int, dict[tuple[int,int], int]]) -> str:
    pct_label = int(PERCENT_THRESHOLD * 100)
    starts = {thr: first_day_by_percent(all_year_values, thr, PERCENT_THRESHOLD) for thr in (1,2,3,4)}
    line1 = f"Typical first day (≥{pct_label}% of years):  ≥1={fmt_month_day(starts[1])}   ≥2={fmt_month_day(starts[2])}"
    line2 = f"≥3={fmt_month_day(starts[3])}   ≥4={fmt_month_day(starts[4])}"
    return line1 + "\n" + line2

def average_values_across_years(all_year_values: dict[int, dict[tuple[int,int], int]]) -> dict[tuple[int,int], int]:
    sums, counts = {}, {}
    for _, vals in all_year_values.items():
        for k, v in vals.items():
            sums[k] = sums.get(k, 0) + int(v)
            counts[k] = counts.get(k, 0) + 1
    out = {}
    for k in sums:
        out[k] = int(round(sums[k] / counts[k]))
        out[k] = max(0, min(4, out[k]))
    return out

def draw_year_calendar(station_id: str, display_name: str, year: int, values: dict[tuple[int,int], int], footer_text: str) -> None:
    fig, axes = plt.subplots(3, 4, figsize=(16, 10))
    fig.subplots_adjust(left=0.04, right=0.985, bottom=0.085, top=0.90, hspace=0.36, wspace=0.14)

    for month in range(1, 13):
        ax = axes[(month - 1) // 4][(month - 1) % 4]
        ax.set_title(calendar.month_name[month], fontsize=11, pad=10)
        ax.set_xlim(0, 7)
        ax.set_ylim(0, 7)
        ax.axis("off")

        for d, name in enumerate(WEEKDAY_NAMES):
            ax.add_patch(Rectangle((d, 6), 1, 1, fill=False, edgecolor="#cccccc", linewidth=0.9))
            ax.text(d + 0.5, 6.5, name, ha="center", va="center", fontsize=9, fontweight="bold")

        cal = calendar.monthcalendar(year, month)

        for r in range(6):
            week = cal[r] if r < len(cal) else [0] * 7
            for c, day in enumerate(week):
                if day == 0:
                    color = MISSING
                else:
                    v = values.get((month, day), None)
                    color = COLORS[v] if v is not None and 0 <= v <= 4 else MISSING

                ax.add_patch(Rectangle((c, 5 - r), 1, 1,
                                       facecolor=color, edgecolor="#cfcfcf", linewidth=0.8))

                if day != 0:
                    ax.text(c + 0.06, 5 - r + 0.88, str(day),
                            ha="left", va="top", fontsize=8, fontweight="normal")

    fig.suptitle(f"{display_name} ({station_id}) — {year}", fontsize=16, y=0.965)
    fig.text(0.5, 0.028, footer_text, ha="center", va="center", fontsize=10, linespacing=1.2)

    OUT_IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_IMG / f"{station_id}_{year}.png", dpi=200)
    plt.close(fig)

def main() -> None:
    meta = load_meta().set_index("id")

    stations_years: dict[str, set[int]] = {}
    station_data: dict[str, dict[int, dict[tuple[int,int], int]]] = {}

    for f in FILES.glob("*.csv"):
        m = PAT.match(f.name)
        if not m:
            continue
        sid, year = m.group("id"), int(m.group("year"))

        df = pd.read_csv(f)
        date_col = _find_col(df, ["date"])
        hr_col = _find_col(df, ["heatrisk", "heat_risk", "heat risk"])
        df[date_col] = pd.to_datetime(df[date_col])

        station_data.setdefault(sid, {}).setdefault(year, {})
        for _, row in df.iterrows():
            hr = row.get(hr_col)
            if pd.isna(hr):
                continue
            dt = row[date_col]
            station_data[sid][year][(int(dt.month), int(dt.day))] = int(hr)

        stations_years.setdefault(sid, set()).add(year)

    manifest: list[dict] = []
    for sid in sorted(stations_years.keys()):
        row = meta.loc[sid] if sid in meta.index else None
        display_name = row["name"] if row is not None else sid
        state = row["state"] if row is not None else ""
        years = sorted(stations_years[sid])

        all_years_vals = station_data.get(sid, {})
        footer = footer_for_station(all_years_vals)

        for y in years:
            draw_year_calendar(sid, display_name, y, all_years_vals[y], footer)

        # Average view rendered onto AVG_YEAR (2026)
        avg_vals = average_values_across_years(all_years_vals)
        draw_year_calendar(sid, display_name, AVG_YEAR, avg_vals, footer)

        manifest.append({"id": sid, "name": display_name, "state": state, "years": years})

    write_manifest(manifest)
    print(f"Generated images in: {OUT_IMG}")
    print(f"Wrote manifest: {OUT_JS}")

if __name__ == "__main__":
    main()
