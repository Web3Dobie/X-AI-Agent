import os
import tempfile
import logging
from urllib.parse import quote_plus

# Import your existing utility functions
from utils.substack import send_article_email
from utils.blob import upload_to_blob
from utils.x_post import post_tweet, post_tweet_with_media
from utils.notion_logger import log_substack_post_to_notion, update_notion_page_tweet_url

logger = logging.getLogger(__name__)

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
    """
    Publishes an article by saving it to a temporary file, emailing,
    uploading to a blob, and posting to social media.
    This version uses robust temporary file handling to prevent I/O errors.
    """
    # Create a safe, temporary file to store the article markdown.
    # The 'with' block ensures this file is automatically deleted afterward.
    # delete=False is used on Windows to prevent permission errors.
    is_windows = os.name == 'nt'
    with tempfile.NamedTemporaryFile(
        mode='w+', # Use w+ for writing and reading
        encoding='utf-8', 
        suffix='.md', 
        delete=not is_windows
    ) as temp_article_file:
        try:
            # 1. Save locally to the temporary file
            temp_article_file.write(article_md)
            temp_article_file.flush() # Ensure all content is written to disk
            local_path = temp_article_file.name
            logger.info(f"Article saved to temporary file: {local_path}")

            # 2. If email requested, send it with the markdown file attached
            if send_email:
                send_article_email(
                    title=headline,
                    filename=local_path, # Pass the path to the temp file
                    summary=summary,
                    recipients=email_recipients
                )

            # 3. Upload to Blob (set correct content type)
            content_type = "text/markdown"
            blob_url = upload_to_blob(local_path, content_type=content_type)
            logger.info(f"Article uploaded to blob: {blob_url}")

        finally:
            # On Windows, we need to manually close and delete the file.
            if is_windows:
                temp_article_file.close()
                os.unlink(temp_article_file.name)


    # --- The rest of the logic remains the same ---

    # 4. Log to Notion and get the page ID
    notion_page_id = log_substack_post_to_notion(
        headline=headline,
        blob_url=blob_url,
        tweet_url=None,
        tags=tags,
        category=article_type,
        summary=summary,
        status="Published"
    )

    # 5. Post tweet using the Notion page ID for the article URL
    if notion_page_id:
        article_app_url = f"https://www.dutchbrat.com/articles?articleId={notion_page_id}"
    else:
        article_app_url = blob_url

    tweet_text = (
        f"🚨 New article: {headline}\n\n"
        f"Read it on the archive 👉 {article_app_url}\n"
        "#web3 #crypto"
    )

    if hunter_image_path and os.path.exists(hunter_image_path):
        logger.info(f"📸 Posting tweet with Hunter image: {hunter_image_path}")
        tweet_url = post_tweet_with_media(tweet_text, hunter_image_path)
    else:
        if hunter_image_path:
            logger.warning(f"⚠️ Hunter image not found at {hunter_image_path}")
        logger.info("📝 Posting tweet without image")
        tweet_url = post_tweet(tweet_text)

    # 6. Update the Notion entry with the tweet URL if we got one
    if tweet_url and notion_page_id:
        update_notion_page_tweet_url(notion_page_id, tweet_url)

    logger.info(f"✅ Published! Article: {article_app_url}\nTweet: {tweet_url}")
    return {"blob_url": blob_url, "tweet_url": tweet_url, "article_url": article_app_url, "notion_page_id": notion_page_id}

# Example usage (remains unchanged)
if __name__ == "__main__":
    # ... (example usage code is the same)
    pass