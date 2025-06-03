import logging
import os
import sys
import json
import requests  # ensure this is imported
from datetime import datetime, timezone

from utils.substack_client import SubstackClient
from content.ta_substack_generator import generate_ta_substack_article
from utils import TA_POST_DIR

logger = logging.getLogger("post_ta_weekly_combo")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(os.path.join(TA_POST_DIR, "post_ta_weekly_combo.log"))
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


def post_ta_weekly_combo() -> None:
    logger.info("[ROCKET] Starting post_ta_weekly_combo")

    # 1) Generate a new TA markdown file
    try:
        new_md_path = generate_ta_substack_article()
    except Exception as e:
        logger.error("[ERROR] Failed to generate TA markdown: %s", e)
        print(f"Error: generation failed: {e}")
        return

    if not os.path.isfile(new_md_path):
        logger.error("[ERROR] Generated path is not a file: %s", new_md_path)
        print(f"Error: Expected generated file at {new_md_path}, but none found.")
        return

    logger.info("[WRITE] Generated TA markdown: %s", new_md_path)
    print(f"Generated new Markdown: {new_md_path}")

    # 2) Read the entire Markdown (full_md)
    try:
        with open(new_md_path, "r", encoding="utf-8") as f:
            full_md_original = f.read().strip()
    except Exception as e:
        logger.error("[ERROR] Failed to read '%s': %s", new_md_path, e)
        print(f"Error: could not read file {new_md_path}")
        return

    if not full_md_original:
        logger.error("[ERROR] The generated .md is empty; aborting.")
        print(f"Error: The file {new_md_path} is empty; aborting.")
        return

    # 3) Force a blank subtitle by inserting an extra blank line
    #    immediately after the first "# <headline>" line.
    lines = full_md_original.splitlines()
    if not lines or not lines[0].strip().startswith("#"):
        logger.error("[ERROR] Generated Markdown did not begin with '# '; aborting.")
        print("Error: Generated Markdown must begin with a '# ' heading.")
        return

    # Keep the first (headline) line, then insert one blank line, then the rest.
    headline_line = lines[0]
    remainder_lines = lines[1:]
    full_md = "\n".join([headline_line, "", ""] + remainder_lines)

    # 4) Instantiate SubstackClient and publish
    try:
        client = SubstackClient()
    except Exception as e:
        logger.error("[ERROR] Failed to initialize SubstackClient: %s", e)
        print(f"Error: Could not initialize SubstackClient: {e}")
        return

    publish_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        # Monkey‐patch upsert_draft to dump payload
        original_upsert = client.upsert_draft

        def debug_upsert(*args, **kwargs):
            # Extract the expected parameters
            title = kwargs.get("title") or (args[0] if len(args) > 0 else "")
            subtitle = kwargs.get("subtitle") or (args[1] if len(args) > 1 else "")
            body_md = kwargs.get("body_md") or (args[2] if len(args) > 2 else "")
            published_at_arg = kwargs.get("published_at") or (args[3] if len(args) > 3 else "")

            payload = {
                "draft_title":           title,
                "draft_subtitle":        subtitle,
                "draft_podcast_url":     "",
                "draft_podcast_duration": None,
                "draft_video_upload_id":    None,
                "draft_podcast_upload_id":   None,
                "draft_podcast_preview_upload_id": None,
                "draft_voiceover_upload_id": None,
                "draft_body":            json.dumps(
                    client._build_editorjs_ast(body_md)
                ),
                "section_chosen":        False,
                "draft_section_id":      None,
                "draft_bylines":         [{"id": int(os.getenv("SUBSTACK_AUTHOR_ID")), "is_guest": False}],
                "audience":              "everyone",
                "type":                  "newsletter",
                "published_at":          published_at_arg,
            }
            logger.error("DEBUG-PAYLOAD: %s", json.dumps(payload, indent=2))
            return original_upsert(*args, **kwargs)

        client.upsert_draft = debug_upsert

        post_obj = client.publish(full_md, published_at=publish_at)
        post_data = post_obj.get("post", {}) or post_obj
        slug = post_data.get("slug")
        url = post_data.get("canonical_url") or f"https://{client.slug}.substack.com/p/{slug}"
        logger.info("[OK] Published TA article at %s", url)
        print(f"✅ Published to Substack: {url}")
    except requests.HTTPError as e:
        resp = e.response
        try:
            logger.error("SUBSTACK RESPONSE: %s", resp.json())
        except ValueError:
            logger.error("SUBSTACK RESPONSE TEXT: %s", resp.text)
        logger.error("[ERROR] Failed to publish TA article: %s", e)
        print(f"Error: Substack publish failed: {e}")
        return
    finally:
        client.upsert_draft = original_upsert  # restore original

    logger.info("[ROCKET] post_ta_weekly_combo complete")
    print("Done.")


if __name__ == "__main__":
    post_ta_weekly_combo()
