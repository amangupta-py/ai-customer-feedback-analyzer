import pandas as pd

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


def load_tickets(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath, encoding="utf-8", parse_dates=["created_at"])
    return df


def validate_tickets(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
if __name__ == "__main__":
    df = load_tickets("tickets.csv")
    validate_tickets(df)
    print(f"Loaded {len(df)} tickets")
    print(df.dtypes)
    print(df.head(2))