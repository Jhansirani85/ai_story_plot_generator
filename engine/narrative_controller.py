class NarrativeController:

    def build_prompt(self, genre, character, theme, tone, length, user_idea=None):

        # Target word counts
        word_limits = {
            "Short":  "280-320 words",
            "Medium": "620-680 words",
            "Long":   "860-940 words",
        }

        # Explicit continuation instruction per length.
        # Short: stop naturally once done.
        # Medium/Long: actively discourage early wrap-up.
        continuation_hints = {
            "Short":  (
                "Write exactly 280-320 words. "
                "Do not pad — stop naturally when the story is complete."
            ),
            "Medium": (
                "Write exactly 620-680 words. "
                "Do NOT wrap up early. "
                "Keep writing scenes until you reach the word count, "
                "then end with a final resolved scene."
            ),
            "Long":   (
                "Write exactly 860-940 words. "
                "Do NOT summarise or rush to a conclusion. "
                "Develop the middle with additional scenes, dialogue, and detail. "
                "Only write the ending once you are near 900 words."
            ),
        }

        return f"""Write a {tone.lower()} {genre.lower()} story about: {user_idea}

Main character: {character}
Theme: {theme}

STRICT RULES:
- Write ONLY the story. No summaries, tips, or commentary.
- Do NOT say what the story will do ("tension builds", "truth is revealed").
- Do NOT use headings, labels, or act structure.
- Do NOT write character names in ALL CAPS.
- Do NOT leave the story incomplete or end mid-sentence.
- Write like a published novel — show events as scenes, not summaries.
- Weave clues naturally so the reader discovers truth with the character.

ENDING (critical):
- Resolve the conflict with a clear final scene.
- Last sentence must feel complete and final.
- Do NOT summarize — write the ending as it happens.

LENGTH INSTRUCTION (follow exactly):
{continuation_hints[length]}
Target length: {word_limits[length]}

Begin the story immediately with the first sentence. No title, no preamble:
"""
