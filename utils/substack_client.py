import logging
import os
import json
import requests

from .config import LOG_DIR
from .markdown_utils import extract_title_and_subtitle_from_md

# Configure a logger for this module (it will use the root handler set by post_explainer_combo.py)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SubstackClient:
    API_BASE = "https://{slug}.substack.com/api/v1"
    EDITORJS_VERSION = "2.23.2"  # adjust if DevTools shows a different version

    def __init__(self, api_key=None, slug=None):
        """
        Initializes SubstackClient. Reads SUBSTACK_SLUG from the environment (or slug param)
        and builds self.base_url = "https://<slug>.substack.com/api/v1".

        Authentication is handled via SUBSTACK_COOKIE (your Substack browser session cookie).
        """
        self.slug = slug or os.getenv("SUBSTACK_SLUG")
        if not self.slug:
            logger.error("Missing SUBSTACK_SLUG environment variable.")
            raise ValueError("SUBSTACK_SLUG must be set.")
        self.base_url = self.API_BASE.format(slug=self.slug)

    def _headers(self):
        """
        Returns the headers required for each request:
          - "Cookie": <SUBSTACK_COOKIE>
          - "Content-Type": "application/json"

        Make sure SUBSTACK_COOKIE (in your .env) is the entire semicolon-delimited cookie string
        copied (“Copy as cURL”) from DevTools when you viewed a draft request.
        """
        cookie_val = os.getenv("SUBSTACK_COOKIE")
        if not cookie_val:
            logger.error("SUBSTACK_COOKIE is not set. Cannot authenticate.")
            raise ValueError("SUBSTACK_COOKIE environment variable must be defined.")
        return {
            "Cookie": cookie_val,
            "Content-Type": "application/json",
        }

    def _build_editorjs_ast(self, body_md: str) -> dict:
        """
        Convert a plain Markdown string into a minimal EditorJS AST with a single paragraph block.
        We replace newline characters with <br/> inside that block.
        """
        text_with_br = body_md.strip().replace("\n", "<br/>")
        return {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "data": {"text": text_with_br}
                }
            ],
            "version": self.EDITORJS_VERSION
        }

    def upsert_draft(
        self,
        title: str,
        subtitle: str,
        body_md: str,
        published_at: str,
    ) -> dict:
        """
        Create or update a Substack draft using the full “editor‐state” payload (top‐level keys).
        Returns the JSON object for that draft (including 'id'), whether it’s under "draft",
        "post", or is a flat object.

        Required environment variable:
          - SUBSTACK_AUTHOR_ID: numeric ID of your Substack account (found in DevTools under "draft_bylines").

        Parameters:
          - title: the post’s title (string)
          - subtitle: the post’s subtitle (string; can be "")
          - body_md: the remainder of the Markdown (after extracting title/subtitle)
          - published_at: ISO‐8601 UTC string (e.g. "2025-05-31T14:30:00Z"), or None to save as draft
        """
        url = f"{self.base_url}/drafts"

        # 1) Fetch and validate author ID from environment
        author_id_str = os.getenv("SUBSTACK_AUTHOR_ID")
        if not author_id_str:
            logger.error("SUBSTACK_AUTHOR_ID is not set. Cannot build draft_bylines.")
            raise ValueError("SUBSTACK_AUTHOR_ID environment variable must be defined.")
        try:
            author_id = int(author_id_str)
        except ValueError:
            logger.error("SUBSTACK_AUTHOR_ID must be a valid integer.")
            raise

        # 2) Convert body_md → EditorJS AST → JSON string
        editorjs_ast = self._build_editorjs_ast(body_md)
        draft_body_str = json.dumps(editorjs_ast)

        # 3) Build the exact top‐level payload matching DevTools (no "draft": {...} wrapper)
        payload = {
            "draft_title": title,
            "draft_subtitle": subtitle,
            "draft_podcast_url": "",
            "draft_podcast_duration": None,
            "draft_video_upload_id": None,
            "draft_podcast_upload_id": None,
            "draft_podcast_preview_upload_id": None,
            "draft_voiceover_upload_id": None,
            "draft_body": draft_body_str,
            "section_chosen": False,
            "draft_section_id": None,
            "draft_bylines": [{"id": author_id, "is_guest": False}],
            "audience": "everyone",
            "type": "newsletter",
            "published_at": published_at,
        }

        # 4) Debug print the payload so you can compare to DevTools if needed
        logger.info("DEBUG: upsert_draft payload → %s", json.dumps(payload))

        # 5) Send POST to /api/v1/drafts
        resp = requests.post(url, json=payload, headers=self._headers())

        # Attempt to parse JSON (fall back to raw if invalid)
        try:
            resp_json = resp.json()
        except ValueError:
            resp_json = {"_raw_text": resp.text}

        # 6) Log the response for debugging
        logger.info("DEBUG: Substack /drafts response → %s", json.dumps(resp_json))

        if not resp.ok:
            logger.error("=== Substack upsert_draft returned %s ===", resp.status_code)
            logger.error("Response body: %s", resp.text)
            resp.raise_for_status()

        # 7) Extract the draft object from resp_json:
        #    a) If "draft" key exists, take resp_json["draft"]
        #    b) Else if "post" key exists, take resp_json["post"]
        #    c) Else if resp_json contains a top-level "id", treat resp_json as the draft
        draft_obj = {}
        if "draft" in resp_json:
            draft_obj = resp_json["draft"]
        elif "post" in resp_json:
            draft_obj = resp_json["post"]
        elif "id" in resp_json:
            draft_obj = resp_json  # flat object
        else:
            # No recognizable structure
            logger.error("Upsert returned JSON without 'draft', 'post', or top-level 'id': %s", json.dumps(resp_json))
            raise RuntimeError("Draft ID missing after upsert_draft.")

        draft_id = draft_obj.get("id")
        if not draft_id:
            logger.error("Draft object exists but has no 'id': %s", json.dumps(draft_obj))
            raise RuntimeError("Draft ID missing after upsert_draft.")

        logger.info("Draft upserted: id=%s", draft_id)
        return draft_obj

    def publish(
        self,
        body_md: str,
        published_at: str,
    ) -> dict:
        """
        Publish a draft in two steps:
        1) Extract title + subtitle from body_md
        2) Call upsert_draft(title, subtitle, remainder_md, published_at)
        3) POST /api/v1/drafts/{draft_id}/publish

        Returns the JSON “post” object (including “canonical_url”).
        """
        # 1) Extract title, subtitle, and remainder from the Markdown
        title, subtitle, remainder_md = extract_title_and_subtitle_from_md(body_md)

        # 2) Create/update the draft
        draft_obj = self.upsert_draft(
            title=title,
            subtitle=subtitle,
            body_md=remainder_md,
            published_at=published_at,
        )
        draft_id = draft_obj.get("id")

        # 3) Publish the draft
        publish_url = f"{self.base_url}/drafts/{draft_id}/publish"
        resp = requests.post(publish_url, headers=self._headers())

        # Attempt to parse JSON (fall back to raw if invalid)
        try:
            publish_json = resp.json()
        except ValueError:
            publish_json = {"_raw_text": resp.text}

        # Log the publish response for debugging
        logger.info("DEBUG: Substack /drafts/%s/publish response → %s", draft_id, json.dumps(publish_json))

        resp.raise_for_status()

        # “post” may be top‐level or nested under "post", so handle both
        post_obj = publish_json.get("post") or publish_json

        logger.info("Post published: url=%s", post_obj.get("canonical_url"))
        return post_obj

    def upload_asset(self, filepath: str) -> str:
        """
        Upload a local file (e.g. image) to Substack’s asset store. Returns the public URL.

        Endpoint: POST https://api.substack.com/v1/assets/{newsletter_slug}
        Authentication: uses the same SUBSTACK_COOKIE header.
        """
        url = f"https://api.substack.com/v1/assets/{self.slug}"
        headers = {"Cookie": os.getenv("SUBSTACK_COOKIE")}
        with open(filepath, "rb") as f:
            files = {"file": f}
            resp = requests.post(url, headers=headers, files=files)

        resp.raise_for_status()
        asset = resp.json().get("asset", {})
        asset_url = asset.get("url")
        logger.info("Uploaded asset: %s", asset_url)
        return asset_url
