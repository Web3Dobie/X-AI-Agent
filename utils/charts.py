"""
Utility module to generate charts for TA Substack generator.
Wraps the existing generate_btc_technical_charts module.
"""

import os

from .config import CHART_DIR
from .generate_btc_technical_charts import main as _generate_btc_charts


def clear_charts():
    """
    Remove existing chart PNG files in CHART_DIR.
    """
    for fname in os.listdir(CHART_DIR):
        if fname.lower().endswith(".png"):
            try:
                os.remove(os.path.join(CHART_DIR, fname))
            except Exception:
                pass


def generate_charts(tokens):
    """
    Generates chart images for the given list of tokens into CHART_DIR.
    Returns a list of full file paths of the generated PNGs.
    """
    # Ensure chart directory exists
    os.makedirs(CHART_DIR, exist_ok=True)
    # Optional: clear old charts first
    clear_charts()
    # Generate charts into CHART_DIR (if supported by _generate_btc_charts)
    try:
        _generate_btc_charts(output_dir=CHART_DIR)
    except TypeError:
        # Underlying main() may not accept output_dir
        _generate_btc_charts()
        # You may need to move default files into CHART_DIR here

    # Build expected filenames based on tokens
    paths = []
    for token in tokens:
        filename = f"{token}_weekly_chart.png"
        paths.append(os.path.join(CHART_DIR, filename))
    return paths
