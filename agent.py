"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable
from utils.data_loader import load_listings


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "searched": False,           # True once search_listings has run, even if it found nothing
        "outfit_input_id": None,     # id of the item that actually reached suggest_outfit (criterion 3)
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    count = 0
    while True:
        count += 1
        trace.check_iterations(count)

        step = _next_step(session)

        if step == "parse":
            session["parsed"] = parse_query(session["query"])

        elif step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"], parsed["size"], parsed["max_price"]
            )
            session["searched"] = True

        elif step == "stop_empty":
            # THE BRANCH: nothing found, so explain what to change and stop.
            # suggest_outfit is never called with nothing.
            session["error"] = _no_results_message(session["parsed"])
            return session

        elif step == "select":
            session["selected_item"] = session["search_results"][0]

        elif step == "suggest":
            # Read the item back out of the session, not from a local variable.
            item = session["selected_item"]
            session["outfit_input_id"] = item["id"]
            session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])

        elif step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )

        elif step == "done":
            return session


def _next_step(session: dict) -> str:
    """Look at what the session holds so far and pick the next step."""
    if not session["parsed"]:
        return "parse"
    if not session["searched"]:
        return "search"
    if not session["search_results"]:
        return "stop_empty"
    if session["selected_item"] is None:
        return "select"
    if session["outfit_suggestion"] is None:
        return "suggest"
    if session["fit_card"] is None:
        return "fit_card"
    return "done"


# ── query parsing (regex) ─────────────────────────────────────────────────────

_PRICE = re.compile(
    r"(?:under|below|less than|max|up to|<=?)\s*\$?\s*(\d+(?:\.\d+)?)"
    r"|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE = re.compile(
    r"\bsize\s+(us\s*\d+(?:\.\d+)?|one size|[a-z0-9/]+)",
    re.IGNORECASE,
)
_FILLER = re.compile(
    r"\b(?:i'?m|i am|i want|i need|looking for|searching for|find me|show me|"
    r"something|anything|some|a|an|the|in|please)\b",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language with regex.

        "vintage graphic tee under $30, size M"
        -> {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    Anything not found is None. Whatever is left after removing the price,
    size and filler words is the description.
    """
    rest = query

    max_price = None
    price_match = _PRICE.search(rest)
    if price_match:
        max_price = float(price_match.group(1) or price_match.group(2))
        rest = rest[: price_match.start()] + " " + rest[price_match.end():]

    size = None
    size_match = _SIZE.search(rest)
    if size_match:
        size = size_match.group(1).strip()
        rest = rest[: size_match.start()] + " " + rest[size_match.end():]

    rest = _FILLER.sub(" ", rest)
    description = " ".join(re.sub(r"[^\w\s'-]", " ", rest).split())

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """
    Say what the user could change, based on which filter emptied the search.

    Re-runs search_listings with one filter dropped at a time. That's still only
    the search tool, so the branch rule holds: suggest_outfit is never called.
    """
    desc, size, max_price = parsed["description"], parsed["size"], parsed["max_price"]

    asked = f"'{desc}'" if desc else "your search"
    if size:
        asked += f" in size {size}"
    if max_price is not None:
        asked += f" under ${max_price:.0f}"

    if not desc:
        return (
            f"No listings matched {asked}: I couldn't tell what kind of item you "
            "want. Add a word for it, like 'graphic tee', 'jeans' or 'jacket'."
        )

    tips = []
    if not search_listings(desc):
        tips.append(
            f"No listing at any size or price matches the words '{desc}'. "
            "Try broader words, like 'tee', 'jeans', 'jacket', 'dress' or 'vintage'."
        )
        cheapest_overall = min(l["price"] for l in load_listings())
        if max_price is not None and max_price < cheapest_overall:
            tips.append(
                f"Also raise your price limit: nothing listed costs less than "
                f"${cheapest_overall:.0f}."
            )
    else:
        if max_price is not None:
            without_price = search_listings(desc, size, None)
            if without_price:
                cheapest = min(l["price"] for l in without_price)
                tips.append(
                    f"Raise your price limit: the cheapest match is ${cheapest:.0f}."
                )
        if size:
            without_size = search_listings(desc, None, max_price)
            if without_size:
                sizes = sorted({l["size"] for l in without_size})
                tips.append(
                    f"Try a different size: matches come in {', '.join(sizes[:5])}."
                )
        if not tips:
            tips.append("Loosen both the size and the price limit together.")

    return f"No listings matched {asked}. " + " ".join(tips)


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
