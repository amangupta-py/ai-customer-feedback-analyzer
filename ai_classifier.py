"""
ai_classifier.py — Classifies customer support tickets into 5 problem categories using Gemini API.
Sends tickets in batches, returns structured classifications with reasoning.
"""

import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path

load_dotenv()

# === Configuration ===
MODEL_NAME = "gemini-2.5-flash"
API_KEY = os.getenv("GEMINI_API_KEY")
BATCH_SIZE = 20  # Tickets per API call
# === Output path ===
OUTPUT_FILE = Path(__file__).parent / "classifications.json"

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env file. "
        "Make sure .env exists in project root."
    )

genai.configure(api_key=API_KEY)

SYSTEM_PROMPT = """
You are a Senior E-commerce Customer Operations Specialist for Indian e-commerce brands, with expertise in categorizing customer support tickets across delivery, returns, product quality, payments, and order management workflows.
Your job: Analyze and classify each customer support ticket into exactly one of five problem categories.

Rules:
1. You must be consistent — identical types of problems should always receive the same category, regardless of how the customer phrases them.
2. You write nothing else. No suggestions, no resolutions, no greetings. Only the classification output in the exact format specified.

## TICKET CATEGORIES

### 1. Delivery Issues
- Covers: Late delivery, lost package, tracking not updating, package marked delivered but not received, damaged packaging on arrival, delivery to wrong address.
- Does NOT cover: Wrong product inside the package (that's "Wrong/Missing Item"). Damaged product itself (that's "Product Quality").
- Edge Case: If customer says "package arrived smashed" — if they mention packaging or "box damaged," classify as Delivery Issues. If they mention the product inside is broken, classify as Product Quality.

### 2. Wrong/Missing Item
- Covers: Received wrong item or product, product missing in package, empty package, fake product, incorrect product size, incorrect product color variant.
- Does NOT cover: Damaged product, tampered box (that's "Delivery Issues"), quality of the product (that's "Product Quality").
- Edge Case: If customer says product quality is low, cheap, or not up to the mark, that goes to Product Quality.

### 3. Product Quality
- Covers: Product build quality is low or cheap, manufacturing defects, design flaws, product not matching described specifications, product stops working shortly after use, product feels counterfeit but was received correctly.
- Does NOT cover: Incorrect size or color variant (that's "Wrong/Missing Item"), product price or affordability complaints (that's "Payment & Billing"), transport or packaging damage (that's "Delivery Issues"), physical damage caused by customer misuse or accidental drops.
- Edge Case: If customer says "it broke after one use" — default to Product Quality (manufacturing defect), not Delivery Issues. If customer says "it looks fake" but received the right item — classify as Product Quality. If they received a different product altogether — classify as Wrong/Missing Item.

### 4. Payment & Billing
- Covers: Incorrect charge or overcharge, double payment, payment deducted but order not placed, refund not received or delayed, coupon or discount not applied, invoice or receipt mismatch, unauthorized transaction, EMI or payment plan issues.
- Does NOT cover: Order cancellation request (that's "Order Management"), delivery charge disputes tied to a specific order status (that's "Order Management").
- Edge Case: If customer says "I was charged twice" but also wants the order cancelled — classify as Payment & Billing (the financial issue is more urgent). Mark is_ambiguous: true. If customer says "my refund hasn't arrived" — classify as Payment & Billing only if the return was already approved; otherwise classify as Order Management.

### 5. Order Management
- Covers: Order cancellation requests, order not placed despite payment, order stuck in processing, wrong delivery address submitted, request to modify order (quantity, address, item), order confirmation not received, order showing as delivered but return/replacement not initiated.
- Does NOT cover: Delivery delays post-dispatch (that's "Delivery Issues"), refund status after return approved (that's "Payment & Billing"), product complaints (that's "Product Quality").
- Edge Case: If customer wants to cancel AND get refund — classify as Order Management (cancellation is the primary action; refund tracking follows automatically). Mark is_ambiguous: true only if the cancellation has already been processed and the refund is delayed. If order was never dispatched and customer hasn't received confirmation — classify as Order Management, not Delivery Issues.


## OUTPUT FORMAT
Return a JSON array. One object per ticket. Each object has exactly 5 fields:

- "ticket_id": integer (must match input)
- "category": one of exactly these 5 strings — "Delivery Issues", "Wrong/Missing Item", "Product Quality", "Payment & Billing", "Order Management"
- "urgency": one of "low", "medium", "high"
- "is_ambiguous": boolean (true or false)
- "reasoning": one sentence (15-25 words) explaining the categorization

Example output:
[
  {
    "ticket_id": 50001,
    "category": "Delivery Issues",
    "urgency": "high",
    "is_ambiguous": false,
    "reasoning": "Customer reports package marked delivered but not received — classic post-delivery loss pattern."
  },
  {
    "ticket_id": 50002,
    "category": "Wrong/Missing Item",
    "urgency": "medium",
    "is_ambiguous": false,
    "reasoning": "Customer received Sony headphones instead of ordered iPhone — wrong product shipped."
  }
]

## URGENCY RULES

- "high": Money lost (fraud, double-charge), broken product, undelivered after 5+ days, payment failed but charged.
- "medium": Wrong item received, delivery delays under 5 days, refund delays.
- "low": Order modification requests, general queries, post-delivery non-critical issues.


## GLOBAL EDGE CASE RULES

1. If a ticket message is too short or unclear to classify confidently — still pick the most likely category and mark is_ambiguous: true. Never refuse to classify.
2. If a ticket mentions multiple issues — classify based on the most urgent and actionable problem. Use is_ambiguous: true only when categories are genuinely close.
3. If customer language is emotional or abusive — focus only on the underlying problem. Ignore emotional content. Same category as if politely written.

## FINAL INSTRUCTION
Classify the tickets that follow.Return ONLY the JSON array. Do not include any preamble, explanation, or markdown code blocks. Just the raw JSON array, ready for programmatic parsing.
"""

def batch_tickets(tickets: list[dict], batch_size: int = BATCH_SIZE) -> list[list[dict]]:
    """
    Split a list of tickets into batches for API processing.

    Args:
        tickets: List of ticket dicts from data_loader.
        batch_size: Number of tickets per batch (default: BATCH_SIZE).

    Returns:
        List of batches, where each batch is a list of ticket dicts.
    """
    if not tickets:
        return []

    return [
        tickets[i:i + batch_size]
        for i in range(0, len(tickets), batch_size)
    ]

# === Validation constants ===
VALID_CATEGORIES = {
    "Delivery Issues",
    "Wrong/Missing Item",
    "Product Quality",
    "Payment & Billing",
    "Order Management",
}

VALID_URGENCIES = {"low", "medium", "high"}


def classify_batch(batch: list[dict]) -> list[dict]:
    """
    Classify a batch of tickets using Gemini API.

    Args:
        batch: List of ticket dicts (with ticket_id, customer_message, product_name, product_category).

    Returns:
        List of classification dicts with ticket_id, category, urgency, is_ambiguous, reasoning.

    Raises:
        RuntimeError: If the API call fails or returns malformed output.
    """
    # Format the batch as JSON for the prompt
    tickets_json = json.dumps(batch, indent=2)
    user_prompt = f"Tickets to classify:\n{tickets_json}"

    # Call Gemini
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(
            user_prompt,
            generation_config={
                "temperature": 0.0,  # Maximum determinism for consistency
                "max_output_tokens": 8000,
                "response_mime_type": "application/json",  # Forces JSON output
            },
        )
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}") from e

    # Extract text from response
    text = ""
    if hasattr(response, "text") and response.text:
        text = response.text
    elif hasattr(response, "candidates") and response.candidates:
        parts = response.candidates[0].content.parts
        text = "".join(part.text for part in parts if hasattr(part, "text"))

    if not text:
        raise RuntimeError(f"Gemini returned empty response. Full response: {response}")

    # Parse JSON
    try:
        classifications = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse AI response as JSON. Error: {e}\n"
            f"Response was:\n{text[:500]}..."
        ) from e

    required_keys = {"ticket_id", "category", "urgency", "is_ambiguous", "reasoning"}
    for item in classifications:
        if not isinstance(item, dict):
            raise RuntimeError(f"Invalid classification format for ticket {item.get('ticket_id', 'unknown')}")

        missing_keys = required_keys - set(item.keys())
        if missing_keys:
            raise RuntimeError(f"Missing keys for ticket {item.get('ticket_id', 'unknown')}: {missing_keys}")

        if item["category"] not in VALID_CATEGORIES:
            raise RuntimeError(f"Invalid category for ticket {item.get('ticket_id', 'unknown')}: {item['category']}")

        if item["urgency"] not in VALID_URGENCIES:
            raise RuntimeError(f"Invalid urgency for ticket {item.get('ticket_id', 'unknown')}: {item['urgency']}")

        if not isinstance(item["is_ambiguous"], bool):
            raise RuntimeError(f"Invalid is_ambiguous for ticket {item.get('ticket_id', 'unknown')}: {item['is_ambiguous']}")

        if not isinstance(item["reasoning"], str) or not item["reasoning"].strip():
            raise RuntimeError(f"Invalid reasoning for ticket {item.get('ticket_id', 'unknown')}: {item['reasoning']}")

    return classifications

def classify_all_tickets(tickets: list[dict]) -> list[dict]:
    """Classify only unclassified tickets, merge with existing classifications."""
    existing = load_existing_classifications()
    existing_ids = {c["ticket_id"] for c in existing}

    pending = [t for t in tickets if t["ticket_id"] not in existing_ids]

    if not pending:
        print(f"✓ All {len(tickets)} tickets already classified. Nothing to do.")
        return existing

    print(f"Already classified: {len(existing)}")
    print(f"Pending: {len(pending)}")
    print(f"Classifying in batches of {BATCH_SIZE}...")

    batches = batch_tickets(pending)
    new_classifications = list(existing)  # Start with existing

    for i, batch in enumerate(batches, start=1):
        print(f"  Batch {i}/{len(batches)} ({len(batch)} tickets)...", end=" ")

        success = False
        for attempt in range(2):
            try:
                classifications = classify_batch(batch)
                new_classifications.extend(classifications)
                print(f"✓ {len(classifications)} classified")
                success = True
                break
            except RuntimeError as e:
                if attempt == 0:
                    print(f"⚠️ Retry... ", end="")
                else:
                    print(f"❌ Failed after retry: {e}")

        if not success:
            continue

        if i < len(batches):
            time.sleep(4)

    return new_classifications

def load_existing_classifications() -> list[dict]:
    """Load classifications already saved from previous runs."""
    if not OUTPUT_FILE.exists():
        return []
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []

def save_classifications(classifications: list[dict]) -> None:
    """Save classifications to JSON file. Refuses to overwrite with empty data."""
    if not classifications:
        print("\n⚠️  No new classifications to save. Existing file preserved.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(classifications, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(classifications)} classifications to {OUTPUT_FILE.name}")

if __name__ == "__main__":
    from data_loader import load_tickets, get_tickets_for_classification

    df = load_tickets()
    tickets = get_tickets_for_classification(df)

    classifications = classify_all_tickets(tickets)
    save_classifications(classifications)

    # Quick stats
    print("\n=== Classification Summary ===")
    from collections import Counter
    category_counts = Counter(c["category"] for c in classifications)
    urgency_counts = Counter(c["urgency"] for c in classifications)
    ambiguous_count = sum(1 for c in classifications if c["is_ambiguous"])

    print("\nCategory distribution:")
    for cat, count in category_counts.most_common():
        print(f"  {cat}: {count}")

    print("\nUrgency distribution:")
    for urg, count in urgency_counts.most_common():
        print(f"  {urg}: {count}")

    print(f"\nAmbiguous tickets: {ambiguous_count}")