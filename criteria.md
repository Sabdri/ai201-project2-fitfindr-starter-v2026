# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My `search_listings` is a plain keyword match, not a model. It only finds a listing when the user's words actually appear in its title, description, tags, category or colors. A query that uses a synonym the data doesn't contain, like "hoodie" when the listing says "sweatshirt", can miss a listing that would have fit. There are also two model calls on this path (`suggest_outfit` and `create_fit_card`), and either one can fail or time out. 5 of 5 would assume none of that ever happens.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** 
This path never calls the model. `search_listings` is plain Python, and the branch is an `if` that checks whether the result list is empty, so the same query gives the same result every time. If it fails even once, that's a bug in my code, not bad luck, so anything less than 5 of 5 would be accepting a bug.

---

## 3. The item search found is the item `suggest_outfit` receives

For 5 different queries that match at least one listing, the `id` of the listing passed into `suggest_outfit` equals `session["selected_item"]["id"]`, which equals `session["search_results"][0]["id"]` — in 5 of 5 runs.

**Why this target:** Every listing has a unique `id`, so comparing ids proves it is the same item, not just a similar one. Getting the item from the search results into `session["selected_item"]` and then into `suggest_outfit` is plain Python with no model involved, so nothing random can change it. Any mismatch would mean my loop read the wrong session field or passed a value around the session, which is a bug. That makes 5 of 5 the only honest target.

---

## 4. The fit card is the right length and names the right platform

For 5 queries that reach the fit card, each caption is 2–4 sentences long (counting sentences as text ending in `.`, `!` or `?`) and names the listing's actual `platform` (for example "depop" when `selected_item["platform"]` is `"depop"`) without naming any other platform — in at least 4 of 5 captions.

**Why this target:** The caption comes from the model at temperature 0.9 (`config.py`), so I've set it up to come out different every time, and the model doesn't always follow length instructions. It can also make up details, like saying Poshmark when the item is on Depop. I'm allowing one miss in five because of that randomness. I'm not going lower, though: getting the platform wrong is a factual error a buyer would notice, and a caption longer than 4 sentences isn't one anyone would actually post.

---

## 5. The search respects the price ceiling

For 5 queries run through the full agent that each include a price limit (for example `'graphic tee under $30'`), every listing in `session["search_results"]` has `price` less than or equal to the limit in the query — in 5 of 5 runs.

**Why this target:** The filter itself is just a comparison (`price <= max_price`), so it should never let a more expensive item through. I'm checking it through the full agent instead of calling `search_listings` directly, so this also tests whether my query parsing pulls the right number out of the user's words. If the parser misses "$30" and passes `None`, the filter is skipped and this criterion catches it. That makes 5 of 5 a real test rather than an easy one.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
