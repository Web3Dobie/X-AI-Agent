# utils/blob.py - UPDATED to handle proper filenames
import os
import shutil
from datetime import datetime
import re

# Local storage paths
LOCAL_POSTS_DIR = "/app/posts"  # This should match your docker mount point

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    # Remove special characters and convert to lowercase
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    # Replace spaces and multiple hyphens with single hyphen
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    return slug.strip('-')

def extract_title_from_content(filepath: str) -> str:
    """Extract title from markdown content if filename is temp"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the first # heading
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('# ') and 'Hunter' in line:
                title = line.replace('# ', '').strip()
                # Remove common prefixes
                title = title.replace('Hunter Explains: ', '')
                return title
        
        # Fallback: look for any # heading
        for line in lines:
            if line.strip().startswith('# '):
                return line.replace('# ', '').strip()
                
        return "Article"
    except Exception:
        return "Article"

def generate_proper_filename(filepath: str, content_type: str = "text/markdown") -> str:
    """Generate proper filename from temp file"""
    original_filename = os.path.basename(filepath)
    
    # If it's already a proper filename, keep it
    if not original_filename.startswith('tmp') and '-' in original_filename:
        return original_filename
    
    # Extract title from content
    title = extract_title_from_content(filepath)
    
    # Generate proper filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    
    # Truncate if too long
    if len(slug) > 150:
        slug = slug[:150].rstrip('-')
    
    return f"{date_str}_{slug}.md"

def upload_to_blob(filepath: str, blob_name: str = None, content_type: str = "text/markdown") -> str:
    """
    Save file locally instead of uploading to Azure.
    Returns a local URL that matches your API route structure.
    Fixed to use proper filenames instead of temp names.
    """
    
    # Determine category based on content_type or filepath context
    if "technical-analysis" in (blob_name or filepath).lower() or "_ta_" in (blob_name or filepath).lower():
        category = "ta"
    else:
        category = "explainer"
    
    # Generate proper filename if not provided or if it's a temp file
    if not blob_name or blob_name.startswith('tmp'):
        blob_name = generate_proper_filename(filepath, content_type)
    
    # Create directory structure
    category_dir = os.path.join(LOCAL_POSTS_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    
    # Copy file to local storage with proper name
    local_path = os.path.join(category_dir, blob_name)
    shutil.copy2(filepath, local_path)
    
    # Return URL that matches your API route structure
    local_url = f"/api/articles/files/{category}/{blob_name}"
    
    print(f"✅ File saved locally: {local_path}")
    print(f"🔗 Local URL: {local_url}")
    
    return local_url