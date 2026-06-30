import json
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.dirname(__file__)
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")

def build_dashboard(digest, market_data, date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(DOCS_DIR, exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("template.html")

    html = template.render(
        digest=digest,
        market_data=market_data,
        date=date_str,
    )

    # Always overwrite index.html — GitHub Pages serves this
    output_path = os.path.join(DOCS_DIR, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Dashboard] Built at {output_path}")
    return output_path