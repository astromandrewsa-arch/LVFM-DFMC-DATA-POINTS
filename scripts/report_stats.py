"""Print running totals for REPORT.md from data/normalized/summary_counts.csv (written by
build_observations.py), weather_join_coverage.csv and catalog/sources.csv. Output is Markdown."""
import pandas as pd

from common import CATALOG, NORM


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False) if hasattr(df, "to_markdown") else df.to_string(index=False)


if __name__ == "__main__":
    s = pd.read_csv(NORM / "summary_counts.csv")
    s["country"] = s["country"].fillna("unknown")
    clean = s[s["clean"]]
    tot = s.groupby("clean")["n"].sum()
    print(f"**Rows:** {int(s.n.sum()):,} total; {int(tot.get(True, 0)):,} pass QA (no hard flag, not a duplicate).\n")
    print("**By source and fuel class (QA-clean rows):**\n")
    print(md(clean.groupby(["source_id", "fuel_class"])["n"].sum().reset_index().sort_values("n", ascending=False)))
    print("\n**By country (QA-clean):**\n")
    c = clean.pivot_table(index="country", columns="fuel_class", values="n", aggfunc="sum", fill_value=0)
    c["total"] = c.sum(axis=1)
    print(md(c.sort_values("total", ascending=False).reset_index()))
    print("\n**By decade (QA-clean):**\n")
    clean = clean.assign(decade=(clean["year"] // 10 * 10).astype("Int64"))
    print(md(clean.pivot_table(index="decade", columns="fuel_class", values="n", aggfunc="sum", fill_value=0).reset_index()))
    try:
        w = pd.read_csv(NORM / "weather_join_coverage.csv")
        w["source"] = w["file"].str.split("-").str[0]
        w = w.groupby("source")[["rows", "has_power", "has_gridmet", "has_source_weather",
                                       "has_nearest_station", "has_any_weather"]].sum().reset_index()
        tot = w[["rows", "has_any_weather"]].sum()
        print(f"\n**Rows with at least one weather covariate set:** {int(tot.has_any_weather):,} of {int(tot.rows):,} "
              f"({tot.has_any_weather / tot.rows:.1%})")
        print("\n**Weather covariate coverage (rows):**\n")
        print(md(w))
    except FileNotFoundError:
        pass
    try:
        src = pd.read_csv(CATALOG / "sources.csv")
        print("\n**Licensing (sources with ingested rows):**\n")
        x = src[pd.to_numeric(src["records"], errors="coerce") > 0][["source_id", "license", "records"]]
        print(md(x))
    except FileNotFoundError:
        pass
