"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    words = [w for w in re.findall(r"[a-z0-9]+", description.lower())
             if w not in _STOPWORDS]
    wanted_size = size.strip().lower() if size else None

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if wanted_size and not _size_matches(wanted_size, listing["size"]):
            continue

        # Everything a keyword could reasonably appear in
        text = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
        ]).lower()
        listing_words = set(re.findall(r"[a-z0-9]+", text))

        score = sum(1 for word in words if word in listing_words)
        if score > 0:
            scored.append((score, listing))

    # sorted() is stable, so ties keep the order they have in the file
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# Words that appear in almost every listing description and say nothing about
# the item. Without this, "a tee for summer" matches on "a" and "for".
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "of", "to", "in", "on",
    "my", "me", "i", "im", "it", "is", "some", "that", "this", "but", "at",
}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    True when `wanted` equals one whole token of the listing's size.

    "M" matches "S/M" and "M/L", but "L" does not match "XL" and "S" does not
    match "US 9". "One Size" listings fit anyone, so they always match.
    """
    listing_size = listing_size.lower()
    if listing_size.startswith("one size") or wanted == listing_size:
        return True
    tokens = [t for t in re.split(r"[/\s()]+", listing_size) if t]
    return wanted in tokens


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item = _describe_item(new_item)
    items = wardrobe.get("items", [])

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item}\n\n"
            "They haven't told us what's in their wardrobe. Give general styling "
            "advice: 1-2 outfit ideas built around this item, naming the kinds "
            "of pieces to pair it with (e.g. 'straight-leg dark jeans', "
            "'chunky white sneakers'), plus one sentence on why each works."
        )
    else:
        owned = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])}; "
            f"style: {', '.join(w['style_tags'])})"
            + (f" - note: {w['notes']}" if w.get("notes") else "")
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item}\n\n"
            f"Here is what they already own:\n{owned}\n\n"
            "Suggest 1-2 outfits that pair the new item with specific pieces "
            "from their wardrobe. Name each wardrobe piece exactly as written "
            "above, and give one sentence on why each outfit works."
        )

    response = generate(prompt, system=OUTFIT_SYSTEM).strip()
    # The spec promises a non-empty string, even if the model sends nothing back.
    return response or f"Try pairing the {new_item['title']} with simple basics in neutral colors."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return f"Can't write a fit card: no outfit suggestion was given for {new_item['title']}."

    prompt = (
        f"The thrifted find:\n{_describe_item(new_item)}\n\n"
        f"The outfit it's styled in:\n{outfit}\n\n"
        "Write the caption for a social media post about this fit. 2-4 "
        "sentences. Mention the item, its price "
        f"(${new_item['price']:.0f}) and the platform ({new_item['platform']}) "
        "once each, and name no other platform. Be specific about the vibe. "
        "Return only the caption."
    )
    return generate(prompt, system=FIT_CARD_SYSTEM).strip()


# ── Shared helpers ────────────────────────────────────────────────────────────

OUTFIT_SYSTEM = (
    "You are a stylist who works with thrifted clothes. Be concrete and brief. "
    "Plain text, no markdown headers."
)

FIT_CARD_SYSTEM = (
    "You write captions people actually post about their thrift finds: casual, "
    "first person, a little excited, never like a product description. "
    "No hashtag lists."
)


def _describe_item(listing: dict) -> str:
    """One readable block for a listing. Skips brand when it's None."""
    lines = [
        f"{listing['title']} - ${listing['price']:.0f} on {listing['platform']}",
        f"Size {listing['size']}, {listing['condition']} condition",
        f"Colors: {', '.join(listing['colors'])}; style: {', '.join(listing['style_tags'])}",
    ]
    if listing.get("brand"):
        lines.append(f"Brand: {listing['brand']}")
    return "\n".join(lines)
