"""
SubstackClient encapsulates the private Substack API for draft creation, publishing,
and asset upload. Logs operations and errors to a centralized log file.
"""

import logging
import os

import requests

from .config import LOG_DIR

# Configure logging
log_file = os.path.join(LOG_DIR, "substack_client.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class SubstackClient:
    API_BASE = "https://{slug}.substack.com/api/v1"

    def __init__(self, api_key=None, slug=None):
        self.api_key = api_key or os.getenv("SUBSTACK_API_KEY")
        self.slug = slug or os.getenv("SUBSTACK_SLUG")
        if not self.api_key or not self.slug:
            logging.error(
                "Missing SUBSTACK_API_KEY or SUBSTACK_SLUG environment variables."
            )
            raise ValueError("SUBSTACK_API_KEY and SUBSTACK_SLUG must be set.")
        self.base_url = self.API_BASE.format(slug=self.slug)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def upsert_draft(self, title: str, body_markdown: str, publish_at: str):
        """
        Create or update a draft. Returns the draft JSON including its 'id'.
        """
        url = f"{self.base_url}/drafts"
        payload = {
            "draft": {
                "title": title,
                "body_markdown": body_markdown,
                "published_at": publish_at,
            }
        }
        try:
            resp = requests.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            draft = resp.json().get("draft", {})
            logging.info(f"Draft upserted: id={draft.get('id')}")
            return draft
        except Exception as e:
            logging.error(f"Failed to upsert draft: {e}")
            raise

    def publish(self, title: str, body_markdown: str, publish_at: str):
        """
        Full two-step publish: upsert draft, then publish it.
        Returns the published post JSON including 'canonical_url'.
        """
        draft = self.upsert_draft(title, body_markdown, publish_at)
        draft_id = draft.get("id")
        if not draft_id:
            raise RuntimeError("Draft ID missing after upsert.")
        pub_url = f"{self.base_url}/drafts/{draft_id}/publish"
        try:
            resp = requests.post(pub_url, headers=self._headers())
            resp.raise_for_status()
            post = resp.json().get("post", resp.json())
            logging.info(f"Post published: url={post.get('canonical_url')}")
            return post
        except Exception as e:
            logging.error(f"Failed to publish draft {draft_id}: {e}")
            raise

    def upload_asset(self, filepath: str) -> str:
        """
        Upload a local file to Substack's asset store.
        Returns the public URL for embedding in markdown.
        """
        url = f"https://api.substack.com/v1/assets/{self.slug}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with open(filepath, "rb") as f:
                files = {"file": f}
                resp = requests.post(url, headers=headers, files=files)
            resp.raise_for_status()
            asset = resp.json().get("asset", {})
            asset_url = asset.get("url")
            logging.info(f"Uploaded asset: {asset_url}")
            return asset_url
        except Exception as e:
            logging.error(f"Failed to upload asset {filepath}: {e}")
            raise
