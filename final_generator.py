import re
from llama_cpp import Llama
from engine.narrative_controller import NarrativeController

controller = NarrativeController()


# =========================
# TOKEN BUDGETS
# =========================
def get_max_tokens(length):
    # 1 word ≈ 1.3 tokens
    # Short  ~300w  →  500 tokens
    # Medium ~650w  → 1000 tokens
    # Long   ~900w  → 1400 tokens
    return {"Short": 500, "Medium": 900, "Long": 1400}[length]


# =========================
# STRIP LEAKED PROMPT TEXT
# =========================
# When a small model echoes back instructions, these patterns appear.
# We truncate the story at the first sign of leakage.
_LEAK_PATTERNS = [
    r'write only the story',
    r'begin the story now',
    r'no headings',
    r'structure the story',
    r'the story is about',
    r'main character is',
    r'central theme is',
    r'opening of \d+',
    r'middle of \d+',
    r'closing of \d+',
    r'\[beginning\]',
    r'\[middle\]',
    r'\[ending\]',
    r'beginning:',
    r'middle:',
    r'ending:',
    r'strict rules',
    r'word count:',
    r'remember.*this is not copyediting',
    r'if at any point during',
    r'the beginning is the climax',
    r'remember.*the story should',
    r'write a \w+ \w+ story in exactly',
]

_LEAK_RE = re.compile(
    '|'.join(_LEAK_PATTERNS),
    flags=re.IGNORECASE
)


def strip_leaked_prompt(text):
    """Truncate the story at the first line that echoes a prompt instruction."""
    lines = text.splitlines()
    clean = []
    for line in lines:
        if _LEAK_RE.search(line):
            break  # stop here — everything after is echoed instructions
        clean.append(line)
    result = "\n".join(clean).strip()

    # Secondary pass: if a leak starts mid-paragraph (no newline), truncate there
    m = _LEAK_RE.search(result)
    if m:
        result = result[:m.start()].strip()

    return result


# =========================
# CLEAN STORY TEXT
# =========================
def clean_story(text):
    # إزالة الترقيم مثل "1. ", "2. ", ...
    text = re.sub(r'\b\d+\.\s*', '', text)
    # Remove screenplay artifacts
    text = re.sub(r'\b(Scene|Act|Fade|Cut)\b[^\n]*', '', text, flags=re.IGNORECASE)
    # Remove screenplay artifacts
    text = re.sub(r'\b(Scene|Act|Fade|Cut)\b[^\n]*', '', text, flags=re.IGNORECASE)
    # Remove ALL-CAPS speaker labels (script format bleed)
    text = re.sub(r'^[A-Z]{2,}:\s*', '', text, flags=re.MULTILINE)
    # Collapse 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()

    # Reflow into paragraphs of ~5 sentences each
    sentences = re.split(r'(?<=[.!?])\s+', text)
    paragraphs, chunk = [], []
    for s in sentences:
        chunk.append(s)
        if len(chunk) >= 5:
            paragraphs.append(" ".join(chunk))
            chunk = []
    if chunk:
        paragraphs.append(" ".join(chunk))

    return "\n\n".join(paragraphs)


# =========================
# REMOVE REPETITION
# =========================
def remove_repetition(text):
    sentences = text.split(". ")
    seen, cleaned = set(), []
    for s in sentences:
        key = s.strip().lower()
        if key not in seen:
            cleaned.append(s)
            seen.add(key)
    return ". ".join(cleaned)


# =========================
# ENDING DETECTION
# =========================
def has_strong_ending(text):
    tail = text.lower()[-300:]
    signals = [
        "finally", "realized", "truth", "revealed", "understood",
        "it was over", "never again", "from that day", "everything changed",
        "she knew", "he knew", "they knew", "would never",
    ]
    return any(w in tail for w in signals)


# =========================
# ENDING GENERATOR
# =========================
_ENDING_STYLE = {
    "Mystery":      "Reveal the final truth through one clear, decisive action or discovery.",
    "Fantasy":      "End with the cost of victory made clear — what was gained, what was lost.",
    "Romance":      "Resolve with an emotional moment that feels earned, not rushed.",
    "Sci-Fi":       "Close with a revelation that reframes everything the reader just read.",
    "Slice of Life":"End quietly — one small moment that carries the full weight of the story.",
    "Horror":       "End with something deeply unsettling that the character cannot escape.",
    "Adventure":    "End with the character changed — older, wiser, or carrying a new scar.",
}


def get_ending_prompt(genre, story):
    style = _ENDING_STYLE.get(genre, "End with a clear, complete final scene.")
    # Natural brief — no bullet points, no rule lists
    return (
        f"The following story needs a closing paragraph. "
        f"Write exactly one paragraph of 60 to 80 words that ends the story as a scene. "
        f"{style} "
        f"Write only the closing paragraph now:\n\n"
        f"{story[-500:]}"
    )


def generate_ending(model, story, genre):
    response = model(
        get_ending_prompt(genre, story),
        max_tokens=150,
        temperature=0.7,
        stop=["</s>", "\n\n\n"],
    )
    raw = response["choices"][0]["text"].strip()
    return strip_leaked_prompt(raw)


def ensure_strong_ending(model, story, genre):
    if has_strong_ending(story):
        return story
    ending = generate_ending(model, story, genre)
    if ending and len(ending.split()) > 30:
        story += "\n\n" + ending
    return story


# =========================
# TITLE GENERATOR
# =========================
def generate_title(model, story, genre):
    response = model(
        (
            f"Write a short creative title for this {genre} story. "
            f"Maximum 6 words. No quotes. No punctuation at the end. "
            f"Story: {story[:300]} "
            f"Title:"
        ),
        max_tokens=20,
        temperature=0.7,
    )
    title = response["choices"][0]["text"].strip()
    title = re.sub(r'[^A-Za-z0-9\s]', '', title).strip()
    return title if len(title) >= 3 else "Untitled Story"


# =========================
# WORD COUNT LOGGER
# =========================
def log_word_count(story, length):
    targets = {
        "Short":  (260, 340),
        "Medium": (600, 700),
        "Long":   (840, 960),
    }
    lo, hi = targets[length]
    wc = len(story.split())
    status = "OK" if lo <= wc <= hi else "OUT OF RANGE"
    print(f"[Word count] {wc} words | Target {lo}-{hi} | {status}")
    return wc


# =========================
# DISPLAY SANITIZER
# =========================
def sanitize_for_display(text):
    """Final safety net before the text is shown in the UI."""
    m = _LEAK_RE.search(text)
    if m:
        text = text[:m.start()].strip()
    # Trim any trailing incomplete sentence
    last_end = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_end != -1 and last_end >= len(text) - 80:
        text = text[:last_end + 1].strip()
    return text


# =========================
# MAIN GENERATOR
# =========================
def generate_story_fast(model, genre, character, theme, tone, length, user_prompt):

    prompt = controller.build_prompt(
        genre, character, theme, tone, length, user_prompt
    )

    temp_map           = {"Short": 0.65, "Medium": 0.72, "Long": 0.82}
    repeat_penalty_map = {"Short": 1.25, "Medium": 1.22, "Long": 1.18}

    response = model(
        prompt,
        max_tokens=get_max_tokens(length),
        temperature=temp_map[length],
        top_p=0.9,
        repeat_penalty=repeat_penalty_map[length],
        stop=["</s>"],
    )

    story = response["choices"][0]["text"].strip()

    # ── QUALITY PIPELINE ──────────────────────────────────────────────
    story = strip_leaked_prompt(story)    # 1. remove echoed instructions
    story = remove_repetition(story)      # 2. deduplicate sentences
    story = clean_story(story)            # 3. reflow paragraphs
    story = ensure_strong_ending(model, story, genre)  # 4. close the arc
    story = sanitize_for_display(story)   # 5. final display safety net

    wc = log_word_count(story, length)

    title = generate_title(model, story, genre)

    return {
        "title": title,
        "prompt": user_prompt,
        "story": story,
        "word_count": wc,
    }