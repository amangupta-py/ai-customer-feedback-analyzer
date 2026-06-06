# main.py

"""Entry point for the AI Customer Feedback Analyzer pipeline."""

from pathlib import Path
from data_loader import load_tickets, get_tickets_for_classification
from ai_classifier import classify_all_tickets, save_classifications, OUTPUT_FILE as CLASSIFICATIONS_FILE
from aggregator import aggregate_all
from dashboard import render_dashboard


def run_pipeline() -> None:
    """Execute the full pipeline: load → classify → aggregate → render."""

    print("=" * 60)
    print("AI Customer Feedback Analyzer")
    print("=" * 60)

    # Step 1: Load tickets
    print("\n[1/4] Loading tickets...")
    df = load_tickets()
    print(f"      Loaded {len(df)} tickets.")

    # Step 2: Classify (skips already-classified tickets via idempotent logic)
    print("\n[2/4] Classifying tickets...")
    tickets = get_tickets_for_classification(df)
    classifications = classify_all_tickets(tickets)
    save_classifications(classifications)
    # Step 3: Aggregate
    print("\n[3/4] Calculating aggregations...")
    aggregations = aggregate_all(df)
    print(f"      Categories: {len(aggregations['category_counts'])}")
    print(f"      Urgent tickets: {len(aggregations['urgent_tickets'])}")
    print(f"      Ambiguous tickets: {len(aggregations['ambiguous_tickets'])}")

    # Step 4: Render dashboard
    print("\n[4/4] Rendering dashboard...")
    output_path = render_dashboard(aggregations)
    print(f"      Saved to: {output_path}")

    print("\n" + "=" * 60)
    print("✓ Pipeline complete. Open dashboard.html in your browser.")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()