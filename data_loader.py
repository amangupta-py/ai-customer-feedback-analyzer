import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).parent / "tickets.csv"

REQUIRED_COLUMNS = [
    "ticket_id",
    "created_at",
    "customer_name",
    "customer_email",
    "order_id",
    "product_name",
    "product_category",
    "channel",
    "days_since_delivery",
    "customer_message",
    "true_category",
]


def load_tickets() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found\n"
                                "please run generate_sample_data.py to create it.")
    
    df = pd.read_csv(DATA_FILE, encoding="utf-8", parse_dates=["created_at"])
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if len(df) == 0:
        raise ValueError("No tickets found in the data.")
    if df['customer_message'].isnull().any():
        raise ValueError("Some tickets have empty customer messages.")
    return df

def get_tickets_for_classification(df: pd.DataFrame) -> list:
    tickets = df[["ticket_id", "customer_message", "product_name", "product_category"]].to_dict(orient="records")
    return tickets

if __name__ == "__main__":
    df = load_tickets()
    tickets = get_tickets_for_classification(df)
    print(f"Loaded {len(df)} tickets")
    print(tickets[:2])