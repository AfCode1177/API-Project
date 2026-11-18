"""Knowledge base and tools for Routine Auditor.

The three public functions at the bottom (lookup_ingredient, check_conflicts,
build_routine) are the agent's tools. Gemini decides when to call them; this
file does the actual checking, so conflicts come from YOUR table, not from the
model's memory.

BEFORE YOU SUBMIT: every `source` string below is a pointer to the kind of
reference that supports the rule. Open a real page (AAD, a drug label, a
peer-reviewed review, etc.), confirm it supports the rule, and replace the
string with the exact title + URL. Do not claim a source you have not read.
"""

# ---- Ingredient table (15 entries). step = layering order, low = first. ----
# time: "am", "pm", or "either"
INGREDIENTS = {
    "cleanser": {"does": "Removes dirt, oil and sunscreen.", "time": "either", "step": 1,
                 "notes": "Use a gentle, non-stripping formula.", "source": "General skincare basics (add citation)"},
    "aha": {"does": "Chemical exfoliant (glycolic, lactic, mandelic acid) that loosens dead surface cells.",
            "time": "either", "step": 2,
            "notes": "Can irritate and raises sun sensitivity. Start 1-2 nights a week.",
            "source": "American Academy of Dermatology, chemical exfoliation guidance (verify + add link)"},
    "bha": {"does": "Salicylic acid. Oil-soluble exfoliant that works inside pores.",
            "time": "either", "step": 2,
            "notes": "Helpful for oily or congested skin. Can dry and irritate.",
            "source": "21 CFR 333.350(c)(1)(ii), FDA labeling of OTC acne drug products (https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-333/subpart-D/section-333.350)"},
    "vitamin c": {"does": "Antioxidant that helps protect against environmental damage and can brighten skin.",
                  "time": "am", "step": 3,
                  "notes": "Usually used in the morning under sunscreen. L-ascorbic acid can sting.",
                  "source": "Dermatology reviews on topical vitamin C (verify + add link)"},
    "niacinamide": {"does": "Supports the skin barrier and can reduce oiliness and redness.",
                    "time": "either", "step": 3, "notes": "Generally well tolerated.",
                    "source": "Dermatology reviews on topical niacinamide (verify + add link)"},
    "hyaluronic acid": {"does": "Humectant that draws water into the outer skin layer.",
                        "time": "either", "step": 3, "notes": "Apply on damp skin, then seal with moisturizer.",
                        "source": "General skincare basics (add citation)"},
    "peptides": {"does": "Signal-type ingredients marketed for firmness and smoothness.",
                 "time": "either", "step": 3, "notes": "Evidence varies by peptide.",
                 "source": "Dermatology reviews on cosmetic peptides (verify + add link)"},
    "copper peptides": {"does": "Copper-bound peptides marketed for firmness and repair.",
                        "time": "either", "step": 3,
                        "notes": "Often advised to keep apart from strong acids. Evidence is limited.",
                        "source": "Cosmetic-science reviews (verify + add link)"},
    "azelaic acid": {"does": "Helps with redness, uneven tone and acne-prone skin.",
                     "time": "either", "step": 4, "notes": "Usually gentle; mild tingling is common.",
                     "source": "American Academy of Dermatology / drug label (verify + add link)"},
    "benzoyl peroxide": {"does": "Antibacterial acne treatment.", "time": "either", "step": 4,
                         "notes": "Can dry and irritate, and bleaches fabric.",
                         "source": "FDA OTC acne drug labeling (verify + add link)"},
    "retinoid": {"does": "Vitamin A family (retinol, retinal, adapalene, tretinoin) for texture, acne and aging.",
                 "time": "pm", "step": 5,
                 "notes": "Use at night, ramp up slowly, and wear sunscreen daily. Avoid during pregnancy unless a doctor says otherwise.",
                 "source": "American Academy of Dermatology, retinoid guidance (verify + add link)"},
    "ceramides": {"does": "Barrier lipids that help moisturizers hold water in.",
                  "time": "either", "step": 6, "notes": "Well tolerated.",
                  "source": "General skincare basics (add citation)"},
    "moisturizer": {"does": "Seals in hydration and supports the barrier.", "time": "either", "step": 6,
                    "notes": "Pick the texture to match skin type.",
                    "source": "General skincare basics (add citation)"},
    "sunscreen": {"does": "Blocks UV light. The most important step for skin health.", "time": "am", "step": 7,
                  "notes": "SPF 30+ broad spectrum, applied last in the morning and reapplied outdoors.",
                  "source": "American Academy of Dermatology, sunscreen guidance (verify + add link)"},
}

# Names people actually type -> canonical key above.
ALIASES = {
    "retinol": "retinoid", "retinal": "retinoid", "retinaldehyde": "retinoid", "tretinoin": "retinoid",
    "adapalene": "retinoid", "differin": "retinoid", "retinoids": "retinoid", "retinyl palmitate": "retinoid",
    "glycolic acid": "aha", "lactic acid": "aha", "mandelic acid": "aha", "aha": "aha", "alpha hydroxy acid": "aha",
    "salicylic acid": "bha", "bha": "bha", "beta hydroxy acid": "bha",
    "ascorbic acid": "vitamin c", "l-ascorbic acid": "vitamin c", "vitamin c": "vitamin c",
    "sodium ascorbyl phosphate": "vitamin c",
    "niacinamide": "niacinamide", "vitamin b3": "niacinamide",
    "hyaluronic acid": "hyaluronic acid", "sodium hyaluronate": "hyaluronic acid",
    "peptide": "peptides", "peptides": "peptides",
    "copper peptide": "copper peptides", "copper peptides": "copper peptides",
    "azelaic acid": "azelaic acid", "benzoyl peroxide": "benzoyl peroxide", "bpo": "benzoyl peroxide",
    "ceramide": "ceramides", "ceramides": "ceramides", "ceramide np": "ceramides",
    "spf": "sunscreen", "sunscreen": "sunscreen", "sun screen": "sunscreen",
    "moisturizer": "moisturizer", "moisturiser": "moisturizer", "cream": "moisturizer",
    "cleanser": "cleanser", "face wash": "cleanser",
}

# ---- Conflict rules. severity: high / moderate / low / none (myth) ----
RULES = [
    {"pair": ("retinoid", "aha"), "severity": "high",
     "issue": "Both increase peeling and irritation. Using them together can over-exfoliate and damage the skin barrier.",
     "advice": "Use them on different nights (for example retinoid Mon/Thu, AHA Tue/Fri) and never layer them in one routine.",
     "source": "American Academy of Dermatology, retinoid and exfoliant guidance (verify + add link)"},
    {"pair": ("retinoid", "bha"), "severity": "high",
     "issue": "Both can dry and irritate. Together they raise the risk of redness, peeling and a damaged barrier.",
     "advice": "Alternate nights, or use the BHA in the morning if your skin tolerates it.",
     "source": "American Academy of Dermatology, retinoid and exfoliant guidance (verify + add link)"},
    {"pair": ("aha", "bha"), "severity": "moderate",
     "issue": "Two chemical exfoliants at once is easy to overdo.",
     "advice": "Pick one per night, or alternate nights, and watch for stinging or tightness.",
     "source": "Dermatology reviews on chemical exfoliation (verify + add link)"},
    {"pair": ("retinoid", "benzoyl peroxide"), "severity": "moderate",
     "issue": "Together they can be very drying. Benzoyl peroxide can also degrade some retinoids such as tretinoin (adapalene is a common exception).",
     "advice": "Use benzoyl peroxide in the morning and the retinoid at night, or ask a dermatologist about prescription combinations.",
     "source": "FDA drug labeling for tretinoin / adapalene (verify + add link)"},
    {"pair": ("vitamin c", "benzoyl peroxide"), "severity": "low",
     "issue": "Benzoyl peroxide can oxidize vitamin C and reduce how well it works.",
     "advice": "Use vitamin C in the morning and benzoyl peroxide at night.",
     "source": "Cosmetic-science and dermatology reviews (verify + add link)"},
    {"pair": ("vitamin c", "retinoid"), "severity": "low",
     "issue": "Not a true clash, but using both at once can add irritation for sensitive skin.",
     "advice": "Vitamin C in the morning, retinoid at night.",
     "source": "Dermatology reviews (verify + add link)"},
    {"pair": ("vitamin c", "aha"), "severity": "low",
     "issue": "Both are acidic and can sting together, especially on sensitive skin.",
     "advice": "Separate them by time of day (vitamin C AM, AHA PM) if you notice irritation.",
     "source": "Dermatology reviews (verify + add link)"},
    {"pair": ("copper peptides", "vitamin c"), "severity": "low",
     "issue": "Often advised to keep apart because acids may affect copper peptides. Evidence is limited.",
     "advice": "Use them at different times of day.",
     "source": "Cosmetic-science reviews (verify + add link)"},
    {"pair": ("copper peptides", "aha"), "severity": "low",
     "issue": "Strong acids may reduce how well copper peptides work. Evidence is limited.",
     "advice": "Use them on separate nights.",
     "source": "Cosmetic-science reviews (verify + add link)"},
    {"pair": ("niacinamide", "vitamin c"), "severity": "none",
     "issue": "Commonly repeated as a conflict, but modern formulations are generally fine together.",
     "advice": "No need to separate them unless your skin reacts.",
     "source": "Dermatology and cosmetic-science reviews (verify + add link)"},
    {"pair": ("benzoyl peroxide", "bha"), "severity": "moderate",
     "issue": "Both can dry and irritate. Together they raise the risk of dryness, peeling and stinging.",
     "advice": "Start with one, or use them at different times (for example the benzoyl peroxide wash in the morning, the BHA at night), and add a moisturizer.",
     "source": "21 CFR 333.350(c)(1)(ii), FDA labeling of OTC acne drug products (https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-333/subpart-D/section-333.350)"},
]

SKIN_TYPES = {"oily", "dry", "combination", "normal", "sensitive", "unknown"}
MAX_ITEMS = 25
MAX_NAME_LEN = 60


def _canon(name):
    """Map a user-typed name to a canonical key, or None if unknown."""
    if not isinstance(name, str):
        return None
    key = name.strip().lower()[:MAX_NAME_LEN]
    return ALIASES.get(key) or (key if key in INGREDIENTS else None)


def _split(names):
    """Return (known canonical set, list of unrecognized names). Caps list size."""
    known, unknown = set(), []
    for n in list(names or [])[:MAX_ITEMS]:
        c = _canon(n)
        if c:
            known.add(c)
        elif isinstance(n, str) and n.strip():
            unknown.append(n.strip()[:MAX_NAME_LEN])
    return known, unknown


# ============================ AGENT TOOLS ============================

def lookup_ingredient(name: str) -> dict:
    """Look up what a skincare ingredient does and how to use it.

    Args:
        name: Ingredient name, e.g. "retinol", "glycolic acid", "niacinamide".
    """
    c = _canon(name)
    if not c:
        return {"found": False, "note": "Not in the knowledge base. Say you cannot verify it."}
    return {"found": True, "ingredient": c, **INGREDIENTS[c]}


def check_conflicts(actives: list[str]) -> dict:
    """Check every pair of active ingredients in a routine for known conflicts.

    Args:
        actives: All active ingredients across the user's products,
            e.g. ["retinol", "glycolic acid", "vitamin c"].
    """
    known, unknown = _split(actives)
    found = []
    for r in RULES:
        a, b = r["pair"]
        if a in known and b in known:
            found.append({"between": [a, b], "severity": r["severity"], "issue": r["issue"],
                          "advice": r["advice"], "source": r["source"]})
    order = {"high": 0, "moderate": 1, "low": 2, "none": 3}
    found.sort(key=lambda x: order[x["severity"]])
    return {"recognized": sorted(known), "unrecognized": unknown, "conflicts": found,
            "note": "Only pairs in the knowledge base are checked. Unrecognized items were not checked."}


def build_routine(actives: list[str], product_types: list[str], skin_type: str) -> dict:
    """Build an AM/PM order and find missing basic steps.

    Args:
        actives: Active ingredients the user has, e.g. ["retinol", "vitamin c"].
        product_types: Basic products the user has: "cleanser", "moisturizer", "sunscreen".
        skin_type: One of oily, dry, combination, normal, sensitive, unknown.
    """
    known_a, unknown_a = _split(actives)
    known_p, unknown_p = _split(product_types)
    have = known_a | known_p
    skin = skin_type.strip().lower() if isinstance(skin_type, str) and skin_type.strip().lower() in SKIN_TYPES else "unknown"

    def slot(period):
        items = [k for k in have if INGREDIENTS[k]["time"] in (period, "either")]
        if period == "am":   # sunscreen last; retinoid and exfoliants stay out of the morning
            items = [k for k in items if k not in ("retinoid", "aha", "bha")]
        else:
            items = [k for k in items if k not in ("sunscreen", "vitamin c")]
            if {"retinoid", "aha", "bha"} & have:   # keep benzoyl peroxide apart from them
                items = [k for k in items if k != "benzoyl peroxide"]
        return sorted(items, key=lambda k: INGREDIENTS[k]["step"])

    notes = []
    if "retinoid" in have and ({"aha", "bha"} & have):
        notes.append("Alternate nights: retinoid nights and exfoliant nights should not overlap.")
    if {"retinoid", "aha", "bha", "benzoyl peroxide"} & have and "sunscreen" not in have:
        notes.append("You use drying/exfoliating actives but no sunscreen. Daily SPF matters more now.")
    if skin == "sensitive" and ({"retinoid", "aha", "bha"} & have):
        notes.append("Sensitive skin: introduce each strong active 1-2 nights a week and patch test first.")
    if "aha" in have or "bha" in have or "benzoyl peroxide" in have:
        notes.append("Exfoliants (AHA/BHA) go in the PM only. Benzoyl peroxide goes in the AM when you also use an exfoliant or retinoid, so they stay apart. Limit to a few nights a week.")

    gaps = [g for g in ("cleanser", "moisturizer", "sunscreen") if g not in have]
    return {"skin_type": skin, "am": slot("am"), "pm": slot("pm"), "gaps": gaps, "notes": notes,
            "unrecognized": unknown_a + unknown_p}
