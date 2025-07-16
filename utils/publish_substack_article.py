import os
from utils.substack import save_article, send_article_email
from utils.blob import upload_to_blob
from utils.x_post import post_tweet, post_tweet_with_media
from utils.notion_logger import log_substack_post_to_notion, update_notion_page_tweet_url
from urllib.parse import quote_plus

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

    # 2. If email requested, send it with the markdown file attached
    if send_email:
        send_article_email(
            title=headline,
            filename=local_path,
            summary=summary,
            recipients=email_recipients
        )

    # 3. Upload to Blob (set correct content type for Markdown/HTML/PDF)
    content_type = "text/markdown"
    blob_url = upload_to_blob(local_path, content_type=content_type)

    # 4. Log to Notion and get the page ID
    notion_page_id = log_substack_post_to_notion(
        headline=headline,
        blob_url=blob_url,
        tweet_url=None,  # We'll update this after posting the tweet
        tags=tags,
        category=article_type,
        summary=summary,
        status="Published"
    )

    # 5. Post tweet using the Notion page ID for the article URL
    if notion_page_id:
        article_app_url = f"https://www.dutchbrat.com/articles/{notion_page_id}"
    else:
        # Fallback to blob URL if Notion logging failed
        article_app_url = blob_url

    tweet_text = (
        f"🚨 New article: {headline}\n\n"
        f"Read it on the archive 👉 {article_app_url}\n"
        "#web3 #crypto"
    )

    # Only try to post with media if image path exists and file exists
    if hunter_image_path and os.path.exists(hunter_image_path):
        print(f"📸 Posting tweet with Hunter image: {hunter_image_path}")
        tweet_url = post_tweet_with_media(tweet_text, hunter_image_path)
    else:
        if hunter_image_path:
            print(f"⚠️ Hunter image not found at {hunter_image_path}")
        print("📝 Posting tweet without image")
        tweet_url = post_tweet(tweet_text)

    # 6. Update the Notion entry with the tweet URL if we got one
    if tweet_url and notion_page_id:
        update_notion_page_tweet_url(notion_page_id, tweet_url)

    print(f"✅ Published! Article: {article_app_url}\nTweet: {tweet_url}")
    return {"blob_url": blob_url, "tweet_url": tweet_url, "article_url": article_app_url, "notion_page_id": notion_page_id}

# Example usage
if __name__ == "__main__":
    article_md = "# Example Article\n\nHello world, here is my latest analysis."
    headline = "Hello World Article"
    tags = ["example", "web3"]
    summary = "A simple test of the end-to-end pipeline."
    hunter_image_path = "./content/assets/hunter_poses/substack_ta.png"
    publish_substack_article(
        article_md, 
        headline, 
        article_type="macro", 
        tags=tags, 
        summary=summary, 
        hunter_image_path=hunter_image_path,
        send_email=True
    )