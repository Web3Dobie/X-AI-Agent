import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Web3 Dobie Dashboard", layout="wide")
st.title("🐾 Web3 Dobie Engagement Dashboard")

def load_csv(file):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame()

# Load enriched metrics
metrics = load_csv("data/tweet_metrics_enriched.csv")
if metrics.empty:
    st.error("No enriched tweet metrics found.")
    st.stop()

# Parse date and extract time features
metrics["date"] = pd.to_datetime(metrics["date"])
metrics["hour"] = metrics["date"].dt.hour
metrics["weekday"] = metrics["date"].dt.day_name()

# Engagement summary
metrics["total_engagement"] = metrics["likes"] + metrics["retweets"] + metrics["replies"]

st.header("📈 Engagement by Hour of Day")
hourly = metrics.groupby("hour")["total_engagement"].mean()
st.bar_chart(hourly)

st.header("📅 Engagement by Day of Week")
weekday = metrics.groupby("weekday")["total_engagement"].mean().reindex([
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
])
st.bar_chart(weekday)

st.header("📝 Engagement by Tweet Type")
type_engagement = metrics.groupby("type")["total_engagement"].mean().sort_values(ascending=False)
st.bar_chart(type_engagement)

st.header("🏆 Top 5 Tweets")
top5 = metrics.sort_values("engagement_score", ascending=False).head(5)
for _, row in top5.iterrows():
    st.markdown(f"- [{row['type']} on {row['date'].date()}]({row['url']})")
    st.write(
        f"❤️ {row['likes']}  🔁 {row['retweets']} 💬 {row['replies']} → Score: {row['engagement_score']}"
    )

st.header("📊 Engagement Heatmap (Day vs Hour)")
import seaborn as sns
import matplotlib.pyplot as plt

heatmap_data = metrics.groupby(["weekday", "hour"])["total_engagement"].mean().unstack().fillna(0)
fig, ax = plt.subplots(figsize=(10, 4))
sns.heatmap(heatmap_data, cmap="YlGnBu", ax=ax)
st.pyplot(fig)

st.markdown("---")
st.caption("Web3 Dobie | Engagement Insights Dashboard")