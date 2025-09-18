# utils/blob.py - UPDATED to save locally instead of Azure
import os
import shutil
from datetime import datetime

# Local storage paths
LOCAL_POSTS_DIR = "/app/posts"  # This should match your docker mount point

def upload_to_blob(filepath: str, blob_name: str = None, content_type: str = "text/markdown") -> str:
    """
    Save file locally instead of uploading to Azure.
    Returns a local URL that matches your API route structure.
    """
    if not blob_name:
        blob_name = os.path.basename(filepath)
    
    # Determine category based on filename or content_type
    if "technical-analysis" in blob_name.lower() or "_ta_" in blob_name.lower():
        category = "ta"
    else:
        category = "explainer"
    
    # Create directory structure
    category_dir = os.path.join(LOCAL_POSTS_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    
    # Copy file to local storage
    local_path = os.path.join(category_dir, blob_name)
    shutil.copy2(filepath, local_path)
    
    # Return URL that matches your API route structure
    local_url = f"/api/articles/files/{category}/{blob_name}"
    
    print(f"✅ File saved locally: {local_path}")
    print(f"🔗 Local URL: {local_url}")
    
    return local_url