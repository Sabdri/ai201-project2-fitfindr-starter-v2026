# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr is a command-line agent for thrift shopping. You type what you want in plain words, like `python app.py ask 'vintage graphic tee under $30, size M'`, and it searches 40 secondhand listings from Depop, Poshmark and thredUp for the best match within your size and price. It then suggests one or two outfits that pair that item with clothes already in your wardrobe, or gives general styling advice if your wardrobe is empty, and writes a short caption you could actually post about the find. If nothing matches, it stops before the outfit step and tells you what to change: broader words, a different size, or a higher price.



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches `data/listings.json` for listings whose words match the description, keeping only ones that fit the size and price limits, best match first.
- **Inputs:**
  - `description` (str): keywords like `"vintage graphic tee"`.
  - `size` (str or None): a size like `"M"` or `"W30"`. `None` skips the size filter. A listing matches when the requested size equals one whole token of the listing's size, case-insensitive, after splitting on `/`, spaces and parentheses. So `"M"` matches `"S/M"`, `"M/L"` and `"M"`. `"L"` does **not** match `"XL"`, and `"S"` does **not** match `"US 9"`. Listings whose size starts with `"One Size"` match any requested size, and a size that equals the listing's whole size also matches (so `"US 8"` matches `"US 8"`).
  - `max_price` (float or None): the price ceiling, inclusive. `None` skips the price filter.
- **Returns:** A `list[dict]` of at most 10 (`config.SEARCH_RESULT_LIMIT`) listing dicts, sorted by score, highest first. The score is how many words from `description` (ignoring filler words like "a", "for", "with") appear in the listing's `title`, `description`, `style_tags`, `category` and `colors`. Each dict is the full listing, unchanged: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
- **When it has nothing:** It returns an empty list, `[]`, not `None` and not an exception. A listing that scores 0 is dropped, so when no listing scores above 0 the result is `[]`.

### `suggest_outfit`

- **What it does:** Uses the model to suggest one or two outfits that pair the thrifted item with pieces the user already owns.
- **Inputs:**
  - `new_item` (dict): one listing dict, the one `search_listings` found.
  - `wardrobe` (dict): `{"items": [...]}`, where each item has `id`, `name`, `category`, `colors`, `style_tags` and `notes`. It can be empty: `{"items": []}`.
- **Returns:** A non-empty `str` with 1–2 outfit ideas. Each idea names the new item and the specific wardrobe pieces it goes with, using their `name`, plus one sentence on why they work together.
- **When it has nothing:** If `wardrobe["items"]` is empty, it does not fail and does not return `""`. It asks the model for general styling advice for the item instead, such as what kinds of pieces to pair it with. It returns a non-empty string in both cases and never returns `""` or `[]`.

### `create_fit_card`

- **What it does:** Uses the model to write a short social-media caption about the find and the outfit, one that reads like a real post rather than a product description.
- **Inputs:**
  - `outfit` (str): the string `suggest_outfit` returned.
  - `new_item` (dict): the listing dict for the item.
- **Returns:** A `str` caption of 2–4 sentences. It mentions the item, its `price` and its `platform` once each, and describes the vibe of the outfit. The same input can give different wording each time, because temperature is 0.9.
- **When it has nothing:** If `outfit` is empty or only whitespace, it does not call the model and does not raise. It returns the message `"Can't write a fit card: no outfit suggestion was given for <item title>."`

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` naming what the user could change and stop, without calling `suggest_outfit`. The message suggests fewer or broader keywords, a different size, or a higher price, and says which of these was in the query. Otherwise, take the first result as `session["selected_item"]` and go on to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. "under $30", "below 30" or "$30" becomes `max_price=30.0`. "size M" or "size US 8" becomes `size`. Filler like "looking for a" is removed, and whatever is left is the `description`. Anything not found is `None`. For example, `'vintage graphic tee under $30, size M'` becomes `{"description": "vintage graphic tee", "size": "M", "max_price": 30.0}`.

**What moves through the session:** Each pass of the loop, `_next_step()` reads the session and picks the next step. The fields fill in this order: `query`, then `parsed` (description / size / max_price), then `search_results` (and `searched = True`). **The branch happens here:** if the results are empty, `error` is set and the run stops. Otherwise it continues with `selected_item` (the first result), then `outfit_input_id` (the `id` of the item handed to `suggest_outfit`, recorded for criterion 3), then `outfit_suggestion`, then `fit_card`. Every tool reads its inputs back out of the session, not from the previous call's return value.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1:
Pair the Y2K Baby Tee — Butterfly Print with Baggy straight-leg jeans, dark wash and Chunky white sneakers. 
Why it works: The fitted baby tee balances the volume of the baggy jeans for a classic Y2K streetwear silhouette.

Outfit 2:
Pair the Y2K Baby Tee — Butterfly Print with Wide-leg khaki trousers, Vintage black denim jacket, and Black combat boots. 
Why it works: The feminine butterfly graphic softens the tough black denim and combat boots while the khaki trousers ground the look with earth tones.

  Fit card: Found this little baby tee on depop for $18 and I’m literally obsessed. Been living in it with baggy denim and chunky sneakers for that ultimate early 2000s mallrat energy, but it’s honestly just as good toughened up with a beat-up jacket and boots. Such a good score.

0 model calls this session, 2 served from cache
```

**The empty-search branch**

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched 'designer ballgown' in size XXS under $5. No listing at any size or price matches the words 'designer ballgown'. Try broader words, like 'tee', 'jeans', 'jacket', 'dress' or 'vintage'. Also raise your price limit: nothing listed costs less than $12.

0 model calls this session

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(l['id'], l['title'], l['price'], l['size'], l['platform']) for l in search_listings('graphic tee', max_price=30)])"
[('lst_002', 'Y2K Baby Tee — Butterfly Print', 18.0, 'S/M', 'depop'), ('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style', 24.0, 'L', 'depop'), ('lst_017', 'Mesh Long-Sleeve Top — Black', 15.0, 'S/M', 'depop'), ('lst_033', 'Vintage Band Tee — Faded Grey', 19.0, 'L', 'depop'), ('lst_011', 'Low-Rise Cargo Pants — Khaki', 27.0, 'W29', 'poshmark'), ('lst_015', 'Vintage Graphic Hoodie — Faded Black', 26.0, 'L', 'depop')]

$ python -c "from tools import search_listings; print(search_listings('ballgown tuxedo', size='XS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1
White ribbed tank top
Black cropped zip hoodie
Chunky white sneakers
Brown leather belt

This outfit works because the fitted tank and cropped hoodie balance the straight-leg fit of the vintage jeans while the belt pulls the streetwear look together.


Outfit 2
Oversized grey crewneck sweatshirt
Black combat boots
Black crossbody bag

This outfit works because the relaxed crewneck creates an effortless, cozy silhouette when paired with classic denim and chunky boots.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Finally found the dream fit with these vintage Levi's 501s and I’m never taking them off. Snagged them on depop for $38 and the medium wash is literally to die for. Just threw them on with beat-up white sneakers for that effortlessly lazy Sunday coffee run energy.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I gave Claude my first spec for `suggest_outfit`: it returned a list of outfit dicts (`outfit_id`, `name`, `item_ids`, `rationale`) and returned `[]` when the wardrobe was empty (`{"items": []}`), and I asked it to check the spec.
- *What came back:* It pointed out three problems by comparing my spec to the stub in `tools.py`. My description said the tool combines listings with each other, but it actually takes one listing plus the user's wardrobe. `create_fit_card` takes a string, so a list of dicts wouldn't plug into it without changes and JSON parsing. And the brief says an empty wardrobe should give general advice, not an empty result.
- *What I changed:* I changed the return type to a non-empty string with 1–2 outfits that name specific wardrobe pieces. For an empty wardrobe, the tool now asks the model for general styling advice instead of returning `[]`, so it never returns an empty value.

**Moment 2**

- *What I asked for:* After `create_fit_card` was built, I had Claude run it three times on the same item (the 2003 tour graphic tee) to check that the captions varied, as Milestone 4 asks.
- *What came back:* All three captions were word for word identical. Temperature in `config.py` was already 0.9, so the cause was the starter's cache handing back the first answer for the same prompt.
- *What I changed:* I left the cache on for building, since it saves requests, and reran the test with `AI201_CACHE=0`. All three captions came out different and each still mentioned the $24 price and Depop once. I'll keep the cache off when I test the criteria in unit 4, because criterion 4 needs five real answers, not one repeated.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
