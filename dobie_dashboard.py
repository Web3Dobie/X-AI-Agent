import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Web3 Dobie Dashboard", layout="wide")
st.title("🐾 Web3 Dobie Performance Dashboard")


# Load logs
def load_csv(file):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame()


tweets = load_csv("logs/tweet_log.csv")
performance = load_csv("logs/performance_log.csv")
followers = load_csv("logs/follower_log.csv")

# Merge with safe timestamp mapping
if not tweets.empty and not performance.empty:
    tweets["timestamp"] = pd.to_datetime(
        tweets["timestamp"], format="ISO8601", utc=True
    )
    df = pd.merge(
        performance,
        tweets[["tweet_id", "content", "category"]],
        on="tweet_id",
        how="left",
    )
    df["timestamp"] = df["tweet_id"].map(
        dict(zip(tweets["tweet_id"], tweets["timestamp"]))
    )
    df["engagement_score"] = df["likes"] + df["retweets"] + df["replies"]
else:
    df = pd.DataFrame()

# Layout
col1, col2 = st.columns(2)

with col1:
    st.header("📊 Tweet Volume")
    if not tweets.empty:
        tweets["date"] = tweets["timestamp"].dt.date
        daily_counts = tweets.groupby("date").size()
        st.bar_chart(daily_counts)
    else:
        st.info("No tweet log found.")

with col2:
    st.header("🏆 Top 3 Tweets (7 days)")
    if not df.empty:
        recent = df[df["timestamp"] > pd.Timestamp.utcnow() - timedelta(days=7)]
        top3 = recent.sort_values("engagement_score", ascending=False).head(3)
        for _, row in top3.iterrows():
            st.markdown(
                f"- [{row['content'][:80]}...](https://x.com/Web3_Dobie/status/{row['tweet_id']})"
            )
            st.write(
                f"❤️ {row['likes']}  🔁 {row['retweets']} 💬 {row['replies']} → Score: {row['engagement_score']}"
            )

st.header("📈 Follower Growth")
if not followers.empty:
    followers["timestamp"] = pd.to_datetime(
        followers["timestamp"], format="ISO8601", utc=True
    )
    followers["date"] = followers["timestamp"].dt.date
    growth = followers.groupby("date")["followers"].mean()
    st.line_chart(growth)
    current = int(growth.iloc[-1])
    st.metric("Current Followers", current)
    st.metric("To Monetization (500)", f"{max(0, 500 - current)}")
else:
    st.info("No follower log found.")

st.header("📊 Engagement Summary (Last 7 Days)")
if not df.empty:
    recent = df[df["timestamp"] > pd.Timestamp.utcnow() - timedelta(days=7)]
    total_likes = recent["likes"].sum()
    total_retweets = recent["retweets"].sum()
    total_replies = recent["replies"].sum()
    total_score = recent["engagement_score"].sum()
    st.metric("❤️ Total Likes", total_likes)
    st.metric("🔁 Total Retweets", total_retweets)
    st.metric("💬 Total Replies", total_replies)
    st.metric("💥 Total Engagement Score", total_score)

    daily = recent.copy()
    daily["date"] = daily["timestamp"].dt.date
    daily_engagement = daily.groupby("date")[["likes", "retweets", "replies"]].sum()
    st.bar_chart(daily_engagement)
else:
    st.info("No engagement data available.")

st.markdown("---")
st.caption("Web3 Dobie | Powered by GPT + Streamlit")
