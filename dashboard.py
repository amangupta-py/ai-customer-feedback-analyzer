import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

BASE_DIR = Path(__file__).parent
AGGREGATIONS_PATH = BASE_DIR / "aggregations.json"
TEMPLATE_PATH = BASE_DIR / "templates" / "dashboard.html"
OUTPUT_PATH = BASE_DIR / "dashboard.html"

REQUIRED_KEYS = {"total_tickets", "category_counts", "top_problem_products", "urgent_tickets", "ambiguous_tickets"}


def load_aggregations(path: Path) -> dict:
    """Load and validate aggregations from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"aggregations.json not found at {path}")
    with open(path) as f:
        data = json.load(f)
    if not data:
        raise ValueError("aggregations.json is empty or contains no data")
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(f"aggregations.json is missing required keys: {sorted(missing)}")
    return data


def render_dashboard(aggregations: dict) -> str:
    """Render the dashboard HTML from the Jinja2 template and aggregations data."""
    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"), autoescape=True)
    try:
        template = env.get_template("dashboard.html")
    except TemplateNotFound:
        raise FileNotFoundError(f"Template not found: {BASE_DIR / 'templates' / 'dashboard.html'}")
    context = {
        "total_tickets": aggregations["total_tickets"],
        "category_counts": aggregations["category_counts"],
        "top_problem_products": aggregations["top_problem_products"],
        "urgent_tickets": aggregations["urgent_tickets"],
        "ambiguous_tickets": aggregations["ambiguous_tickets"],
    }
    return template.render(**context)


if __name__ == "__main__":
    aggregations = load_aggregations(AGGREGATIONS_PATH)
    rendered_html = render_dashboard(aggregations)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"Dashboard saved to: {OUTPUT_PATH}")
