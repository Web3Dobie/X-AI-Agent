import csv

valid_rows = []
with open("data/scored_headlines.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        try:
            float(row["score"])  # Validate score is a float
            valid_rows.append(row)
        except:
            print(f"❌ Corrupt row removed: {row}")

# Overwrite the file with only valid rows
with open("data/scored_headlines.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=["score", "headline", "url", "ticker", "timestamp"]
    )
    writer.writeheader()
    writer.writerows(valid_rows)

print("✅ scored_headlines.csv cleaned.")
