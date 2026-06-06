import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent
CLASSIFICATIONS_PATH = BASE_DIR / "classifications.json"
TICKETS_PATH = BASE_DIR / "tickets.csv"
OUTPUT_PATH = BASE_DIR / "aggregations.json"
TOP_N_PRODUCTS = 5


def load_classifications() -> list[dict]:
    """Load and return classifications from classifications.json."""
    if not CLASSIFICATIONS_PATH.exists():
        raise FileNotFoundError(f"classifications.json not found at {CLASSIFICATIONS_PATH}")
    with open(CLASSIFICATIONS_PATH) as f:
        data = json.load(f)
    if not data:
        raise ValueError("classifications.json is empty")
    return data


def load_tickets() -> pd.DataFrame:
    """Load and return tickets DataFrame from tickets.csv."""
    if not TICKETS_PATH.exists():
        raise FileNotFoundError(f"tickets.csv not found at {TICKETS_PATH}")
    df = pd.read_csv(TICKETS_PATH)
    if df.empty:
        raise ValueError("tickets.csv is empty")
    df["created_at"] = pd.to_datetime(df["created_at"], dayfirst=True)
    return df


def merge_with_tickets(classifications: list[dict], df: pd.DataFrame) -> pd.DataFrame:
    """Inner-join classifications with tickets on ticket_id."""
    classifications_df = pd.DataFrame(classifications)
    merged = classifications_df.merge(df, on="ticket_id", how="inner")
    if merged.empty:
        raise ValueError("Merge of classification & tickets produced empty DataFrame — no matching ticket_ids")
    return merged


def calculate_category_counts(merged: pd.DataFrame) -> list[dict]:
    """Return ticket counts per category, sorted descending."""
    counts = (
        merged.groupby("category")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    return counts.to_dict(orient="records")


def calculate_top_problem_products(merged: pd.DataFrame, top_n: int = TOP_N_PRODUCTS) -> list[dict]:
    """Return top N products by complaint count with their most common category."""
    grouped = merged.groupby("product_name")
    complaint_counts = grouped.size().rename("complaint_count")
    most_common = grouped["category"].apply(lambda s: s.value_counts().idxmax()).rename("most_common_category")
    result = (
        pd.concat([complaint_counts, most_common], axis=1)
        .reset_index()
        .sort_values("complaint_count", ascending=False)
        .head(top_n)
    )
    return result.to_dict(orient="records")


def get_urgent_tickets(merged: pd.DataFrame) -> list[dict]:
    """Return high-urgency tickets sorted by created_at descending."""
    urgent = merged[merged["urgency"] == "high"].sort_values("created_at", ascending=False)
    return [
        {
            "ticket_id": row["ticket_id"],
            "created_at": pd.to_datetime(row["created_at"]).strftime("%Y-%m-%d %H:%M"),
            # "created_at": row["created_at"].strftime("%Y-%m-%d"),
            "customer_name": row["customer_name"],
            "customer_email": row["customer_email"],
            "product_name": row["product_name"],
            "category": row["category"],
            "customer_message": row["customer_message"],
        }
        for _, row in urgent.iterrows()
    ]


def get_ambiguous_tickets(merged: pd.DataFrame) -> list[dict]:
    """Return tickets flagged as ambiguous by the classifier."""
    ambiguous = merged[merged["is_ambiguous"] == True]
    return [
        {
            "ticket_id": row["ticket_id"],
            "category": row["category"],
            "urgency": row["urgency"],
            "reasoning": row["reasoning"],
            "customer_message": row["customer_message"],
        }
        for _, row in ambiguous.iterrows()
    ]


def aggregate_all(tickets_df: pd.DataFrame) -> dict:
    """Orchestrate all aggregations and return the master result dict."""
    classifications = load_classifications()
    merged = merge_with_tickets(classifications, tickets_df)
    return {
        "total_tickets": len(merged),
        "category_counts": calculate_category_counts(merged),
        "top_problem_products": calculate_top_problem_products(merged),
        "urgent_tickets": get_urgent_tickets(merged),
        "ambiguous_tickets": get_ambiguous_tickets(merged),
    }


if __name__ == "__main__":
    tickets_df = load_tickets()
    result = aggregate_all(tickets_df)

    print(f"Total tickets     : {result['total_tickets']}")
    print(f"Categories found  : {len(result['category_counts'])}")
    print(f"Top products      : {len(result['top_problem_products'])}")
    print(f"Urgent tickets    : {len(result['urgent_tickets'])}")
    print(f"Ambiguous tickets : {len(result['ambiguous_tickets'])}")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved to {OUTPUT_PATH}")
