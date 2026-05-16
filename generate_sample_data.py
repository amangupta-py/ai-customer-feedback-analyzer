import random
import csv
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

PRODUCTS = {
    "iPhone 15 Pro":        "Electronics",
    "Samsung Galaxy S24":   "Electronics",
    "Sony WH-1000XM5":      "Electronics",
    "Apple AirPods Pro":    "Electronics",
    "Nike Air Max 270":     "Apparel",
    "Levi's 511 Jeans":     "Apparel",
    "Adidas Ultraboost 22": "Apparel",
    "Instant Pot Duo":      "Home & Kitchen",
    "Dyson V15 Vacuum":     "Home & Kitchen",
}

PRODUCT_NAMES = list(PRODUCTS.keys())
CHANNELS = ["email", "phone", "chat", "social_media"]

# Templates keyed by issue category.
# Each template is a (message_template, days_since_delivery_range) tuple.
# days_since_delivery_range: (min, max) — None means use full 0-30 range.
MESSAGE_TEMPLATES = {
    "delivery_issues": [
        ("its been {days} days and my {product} still hasnt shown up. the tracking hasnt updated in a week. what is going on??", (0, 0)),
        ("My package was marked delivered but there's nothing at my door. I ordered a {product} and paid good money for it.", (0, 2)),
        ("driver left my {product} outside in the rain. box is completely soaked. not happy at all.", (0, 3)),
        ("delivery was supposed to come yesterday and nothing. no update, no call. i need my {product} asap", (0, 1)),
        ("the courier just left my {product} with a neighbor without even telling me. i had to go hunt it down.", (0, 5)),
        ("Package shows delivered 3 days ago but I never got it. Order was a {product}. Please help", (0, 3)),
        ("my {product} was supposed to arrive by monday. its friday now and still nothing. very disappointed", (0, 0)),
    ],
    "wrong_missing_item": [
        ("i ordered a {product} but got something completely different in the box. this is unacceptable", (1, 10)),
        ("one item missing from my order. i specifically ordered a {product} and it wasnt in the package at all.", (1, 7)),
        ("received the wrong color {product}. i clearly selected the black one and got white. need this fixed", (1, 14)),
        ("my {product} came with no accessories inside. manual says there should be a charger but box was empty", (1, 10)),
        ("You sent me a used {product}. The box was opened and there were scratches on it. I ordered brand new.", (1, 7)),
        ("got someone elses order instead of my {product}. whoever ordered this probably has mine too lol please sort this out", (1, 5)),
    ],
    "product_quality": [
        ("my {product} stopped working after just 2 weeks. i barely used it. this quality is terrible", (3, 20)),
        ("the {product} I received is clearly defective. screen has dead pixels right out of the box.", (1, 10)),
        ("battery on my {product} drains in like 2 hours. thats not normal. previous one lasted all day", (5, 25)),
        ("there's a crack in my {product} and i definitely didnt drop it. must have been damaged before shipping", (1, 5)),
        ("my {product} makes a weird noise every time i use it. sounds like something is loose inside", (3, 20)),
        ("the {product} looks nothing like the photos on the website. quality is really cheap and flimsy", (1, 15)),
        ("i've had my {product} for 3 weeks and it's already falling apart. really poor build quality", (15, 30)),
    ],
    "payment_billing": [
        ("i was charged twice for my order. my bank shows two transactions for my {product} purchase. please refund one", (0, 30)),
        ("still waiting on my refund for the {product} i returned 2 weeks ago. where is my money?", (10, 30)),
        ("you charged me for express shipping but my {product} came standard delivery. want a refund on the difference", (3, 20)),
        ("got an unexpected charge on my card after my {product} order. nobody told me about extra fees", (1, 14)),
        ("my discount code didnt apply at checkout. i was supposed to get 20% off my {product} but paid full price", (0, 5)),
        ("i cancelled my order but got charged anyway. never even received the {product}. need full refund NOW", (0, 0)),
        ("invoice shows different amount than what i was quoted. {product} was listed at one price, charged another", (0, 10)),
    ],
    "order_management": [
        ("i need to change the shipping address for my {product} order. it hasnt shipped yet so please update it", (0, 0)),
        ("tried to cancel my {product} order 10 minutes after placing it and the system wont let me. help please", (0, 0)),
        ("can someone tell me the status of my {product} order? the tracking link doesnt work at all", (0, 7)),
        ("i accidentally ordered the wrong size. can i exchange my {product} before it ships?", (0, 0)),
        ("my order confirmation email never came through. did my {product} order even go through?", (0, 0)),
        ("i want to return my {product}. its within the return window but i cant find the return label anywhere", (5, 30)),
        ("how long does it take to process a return? sent back my {product} a week ago and nothing", (7, 30)),
    ],
}

CATEGORIES = list(MESSAGE_TEMPLATES.keys())


def generate_message_and_days(product_name: str) -> tuple[str, int]:
    category = random.choice(CATEGORIES)
    template, day_range = random.choice(MESSAGE_TEMPLATES[category])
    days = random.randint(day_range[0], day_range[1])

    # Some delivery_issues templates embed {days} — only those need a >0 stand-in
    days_display = max(days, 5) if "{days}" in template else days
    message = template.format(product=product_name, days=days_display)
    return message, days


def generate_tickets(n: int = 200) -> list[dict]:
    now = datetime.now()
    sixty_days_ago = now - timedelta(days=60)
    tickets = []

    for i in range(n):
        product_name = random.choice(PRODUCT_NAMES)
        product_category = PRODUCTS[product_name]
        message, days_since_delivery = generate_message_and_days(product_name)

        created_at = fake.date_time_between(start_date=sixty_days_ago, end_date=now)

        tickets.append({
            "ticket_id":            50001 + i,
            "created_at":           created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_name":        fake.name(),
            "customer_email":       fake.email(),
            "order_id":             random.randint(100000, 999999),
            "product_name":         product_name,
            "product_category":     product_category,
            "channel":              random.choice(CHANNELS),
            "days_since_delivery":  days_since_delivery,
            "customer_message":     message,
        })

    return tickets


def main():
    tickets = generate_tickets(200)

    output_path = "tickets.csv"
    fieldnames = [
        "ticket_id", "created_at", "customer_name", "customer_email",
        "order_id", "product_name", "product_category", "channel",
        "days_since_delivery", "customer_message",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tickets)

    dates = [t["created_at"] for t in tickets]
    print(f"Generated {len(tickets)} tickets")
    print(f"Date range : {min(dates)} → {max(dates)}")
    print(f"Saved to   : {output_path}")


if __name__ == "__main__":
    main()
