# utils/url_helpers.py

def get_article_file_path(category: str, filename: str) -> str:
    """
    Constructs the API path for article files.
    
    This returns a path (not a full URL) that is stored in Notion
    and used by the frontend to fetch the markdown file.
    
    Args:
        category: Article category ('explainer', 'ta', etc.)
        filename: The markdown filename (e.g., '2025-10-04_article-title.md')
    
    Returns:
        API path to the article file (e.g., '/api/articles/files/explainer/...')
    
    Example:
        >>> get_article_file_path('explainer', '2025-10-04_test.md')
        '/api/articles/files/explainer/2025-10-04_test.md'
    """
    valid_categories = {'explainer', 'ta'}
    if category not in valid_categories:
        logger.warning(
            f"Unexpected article category '{category}'. "
            f"Valid categories: {valid_categories}"
        )
    
    return f"/api/articles/files/{category}/{filename}"


def get_article_web_url(notion_page_id: str) -> str:
    """
    Constructs the public web URL for an article page.
    
    This returns the full URL that appears in tweets and is what
    users click to view the article on dutchbrat.com.
    
    Args:
        notion_page_id: The Notion page ID for the article
    
    Returns:
        Public URL to view the article
    
    Example:
        >>> get_article_web_url('abc123')
        'https://dutchbrat.com/articles?articleId=abc123'
    """
    return f"https://dutchbrat.com/articles?articleId={notion_page_id}"


def get_tweet_url(username: str, tweet_id: str) -> str:
    """
    Constructs a Twitter/X URL from username and tweet ID.
    
    Args:
        username: Twitter handle (without @)
        tweet_id: The tweet ID
    
    Returns:
        Full Twitter URL
    
    Example:
        >>> get_tweet_url('Web3_Dobie', '1234567890')
        'https://x.com/Web3_Dobie/status/1234567890'
    """
    return f"https://x.com/{username}/status/{tweet_id}"

def get_image_url(image_name: str) -> str:
    """
    Constructs the URL for static images used in articles.
    
    Images are stored in /app/posts/images/ and served via the
    /api/articles/files/images/ endpoint.
    
    Args:
        image_name: The image filename (e.g., 'hunter_headshot.png')
    
    Returns:
        URL path to the image
    
    Example:
        >>> get_image_url('hunter_headshot.png')
        '/api/articles/files/images/hunter_headshot.png'
    """
    return f"/api/articles/files/images/{image_name}"

def get_chart_url(chart_filename: str) -> str:
    """
    Constructs the URL for generated chart images.
    
    Note: Charts are currently stored in the same directory as other images
    (/app/posts/images/) but we use this separate function for semantic clarity
    and to allow easy migration if we later move charts to a separate directory.
    
    Args:
        chart_filename: The chart filename (e.g., 'bitcoin_2025-10-04_advanced.png')
    
    Returns:
        URL path to the chart image
    
    Example:
        >>> get_chart_url('bitcoin_2025-10-04_advanced.png')
        '/api/articles/files/images/bitcoin_2025-10-04_advanced.png'
    """
    # Charts are currently in the images folder
    return f"/api/articles/files/images/{chart_filename}"