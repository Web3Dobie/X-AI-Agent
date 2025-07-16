def log_substack_post_to_notion(
    headline: str,
    blob_url: str,
    tweet_url: str = None,
    tags: list = None,
    category: str = None,
    summary: str = None,
    status: str = "Draft",
) -> str:
    """
    Log a Substack post to Notion and return the page ID.
    
    Returns:
        str: The Notion page ID if successful, None if failed
    """
    props = {
        "Headline": {"title": [{"text": {"content": headline}}]},
        "Date":     {"date":  {"start": datetime.utcnow().isoformat()}},
        "File":     {"url": blob_url},  # URL type property
        "Status":   {"select": {"name": status}},
    }
    if tweet_url:
        props["Tweet"] = {"url": tweet_url}  # Make sure the Notion field is a URL property
    if summary:
        props["Summary"] = {"rich_text": [{"text": {"content": summary}}]}
    if category:
        props["Category"] = {"select": {"name": category}}
    if tags:
        props["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}

    try:
        response = notion.pages.create(
            parent={"database_id": NOTION_SUBSTACK_ARCHIVE_DB_ID},
            properties=props,
        )
        page_id = response["id"]
        logger.info(f"[OK] Logged '{headline}' to Notion DB {NOTION_SUBSTACK_ARCHIVE_DB_ID}, page ID: {page_id}")
        return page_id
    except Exception as e:
        logger.error(f"[ERROR] Couldn't log Substack post '{headline}': {e}")
        return None

def update_notion_page_tweet_url(page_id: str, tweet_url: str) -> bool:
    """
    Update an existing Notion page with a tweet URL.
    
    Args:
        page_id: The Notion page ID
        tweet_url: The tweet URL to add
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Tweet": {"url": tweet_url}
            }
        )
        logger.info(f"[OK] Updated Notion page {page_id} with tweet URL: {tweet_url}")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Failed to update Notion page {page_id} with tweet URL: {e}")
        return False