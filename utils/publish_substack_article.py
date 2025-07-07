from utils.substack import save_article
from utils.blob import upload_to_blob
from utils.x_post import post_tweet, post_tweet_with_media
from utils.notion_logger import log_substack_post_to_notion
from urllib.parse import quote_plus
from utils.substack import send_article_email

def publish_substack_article(
    article_md: str,
    headline: str,
    article_type: str = "article",
    tags: list = None,
    summary: str = None,
    hunter_image_path: str = None,
    send_email: bool = False,
    email_recipients: list = None
):
    # 1. Save locally
    local_path = save_article(article_md, headline, article_type)

    # If email requested, send it with the markdown file attached
    if send_email:
        # If not passed in, will default to ALERT_RECIPIENT or SMTP_USER (per previous fix)
        send_article_email(
            title=headline,
            filename=local_path,
            summary=summary,
            recipients=email_recipients
        )

    # 2. Upload to Blob (set correct content type for Markdown/HTML/PDF)
    content_type = "text/markdown"  # or "application/pdf" if PDF
    blob_url = upload_to_blob(local_path, content_type=content_type)

    # 3. Post tweet (with or without Hunter image)
    APP_BASE_URL = "https://articles.dutchbrat.com"
    article_app_url = f"{APP_BASE_URL}/?article={quote_plus(blob_url)}"

    tweet_text = (
        f"🚨 New article: {headline}\n\n"
        f"Read it on the archive 👉 {article_app_url}\n"
        "#web3 #crypto"
    )

    if hunter_image_path:
        tweet_url = post_tweet_with_media(tweet_text, hunter_image_path)
    else:
        tweet_url = post_tweet(tweet_text)

    # 4. Log to Notion (this function must use blob_url and tweet_url)
    log_substack_post_to_notion(
        headline=headline,
        blob_url=blob_url,
        tweet_url=tweet_url,
        tags=tags,
        category=article_type,
        summary=summary,
        status="Published"
    )

    # 5. Optionally email the article
    if send_email:
        from utils.substack import send_article_email
        send_article_email(
            title=headline,
            filename=local_path,
            summary=summary,
            recipients=email_recipients
        )

    print(f"✅ Published! Blob: {blob_url}\nTweet: {tweet_url}")

# Example usage
if __name__ == "__main__":
    article_md = "# Example Article\n\nHello world, here is my latest analysis."
    headline = "Hello World Article"
    tags = ["example", "web3"]
    summary = "A simple test of the end-to-end pipeline."
    hunter_image_path = "./content/assets/hunter_poses/substack_ta.png"
    publish_substack_article(article_md, headline, article_type="macro", tags=tags, summary=summary, hunter_image_path=hunter_image_path)
