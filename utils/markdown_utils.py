# utils/markdown_utils.py

from typing import Tuple

def extract_title_and_subtitle_from_md(md: str) -> Tuple[str, str, str]:
    """
    Given a Markdown string `md`, return (title, subtitle, remainder_md).
    - title: first line that starts with '# ' (H1).
    - subtitle: if the next non-blank line doesn't start with '#', treat as subtitle.
    - remainder_md: the Markdown after removing those first 1 or 2 lines.
    """
    lines = md.splitlines()
    title = ""
    subtitle = ""
    start_index = 0

    # 1) Find the first non-blank line that begins with "# "
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            title = line.strip()[2:].strip()
            start_index = i + 1
            break

    # 2) Skip blank lines immediately after the title
    while start_index < len(lines) and not lines[start_index].strip():
        start_index += 1

    # 3) If the next non-blank line does NOT start with "#", it's the subtitle
    if start_index < len(lines) and not lines[start_index].strip().startswith("#"):
        subtitle = lines[start_index].strip()
        start_index += 1

    # 4) Everything from start_index onward is the “body” of the Markdown
    remainder_md = "\n".join(lines[start_index:]).lstrip("\n")
    return title, subtitle, remainder_md
