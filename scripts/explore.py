"""Quick one-off EDA of the ASTraM dataset to ground model design."""
import pandas as pd

CSV = "data/Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
df = pd.read_csv(CSV, low_memory=False)
print("SHAPE:", df.shape)
print("\nCOLUMNS:", list(df.columns))

for col in ["event_type", "event_cause", "corridor", "priority", "status",
            "requires_road_closure", "veh_type", "zone", "junction"]:
    print(f"\n=== {col} (top) ===")
    print(df[col].value_counts(dropna=False).head(12))

print("\n=== datetime range ===")
dt = pd.to_datetime(df["start_datetime"], errors="coerce", utc=True)
print("min", dt.min(), "max", dt.max(), "na", dt.isna().sum())

print("\n=== lat/long sanity ===")
for c in ["latitude", "longitude"]:
    s = pd.to_numeric(df[c], errors="coerce")
    print(c, "min", round(s.min(), 4), "max", round(s.max(), 4), "na", s.isna().sum())

# duration analysis
end = pd.to_datetime(df["end_datetime"], errors="coerce", utc=True)
dur = (end - dt).dt.total_seconds() / 60.0
print("\n=== resolution duration (min) ===")
print(dur.describe())

print("\n=== events by hour of day ===")
print(dt.dt.hour.value_counts().sort_index())

print("\n=== distinct corridors count ===", df["corridor"].nunique())
print("=== distinct junctions count ===", df["junction"].nunique())
print("=== distinct police_station ===", df["police_station"].nunique())
