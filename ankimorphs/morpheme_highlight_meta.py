import re

from ankimorphs.ankimorphs_config import AnkiMorphsConfig


class MorphemeHighlightMeta:
    """A helper class for highlighting.
    Tracks a couple of attributes to help us format the output."""

    def __init__(
        self, string: str, learning_interval: int, am_config: AnkiMorphsConfig
    ):
        self.string = string
        self.status = MorphemeHighlightMeta.get_morph_status(
            learning_interval, am_config.interval_for_known_morphs
        )
        self.regex = MorphemeHighlightMeta.make_morph_regex(
            string,
            am_config.preprocess_ignore_bracket_contents,
            am_config.preprocess_ignore_round_bracket_contents,
            am_config.preprocess_ignore_slim_round_bracket_contents,
        )

    @staticmethod
    def get_morph_status(learning_interval: int, interval_for_known_morphs: int) -> str:
        """Get the morpheme's text status. Use the relevant interval based on the user's config."""

        if learning_interval == 0:
            return "unknown"

        if learning_interval < interval_for_known_morphs:
            return "learning"

        return "known"

    @staticmethod
    def make_morph_regex(
        morph: str,
        preprocess_ignore_bracket_contents: bool,
        preprocess_ignore_round_bracket_contents: bool,
        preprocess_ignore_slim_round_bracket_contents: bool,
    ) -> str:
        """Construct the regex for finding this morpheme. Each morpheme gets a custom regex that
        interpolates the possibility of a ruby between each character."""

        # furigana_regex is a subpattern used to deal with rubies inside the target string.
        # 1 `(?![^\[]*\])`: A negative lookahead that ensures the pattern does not match inside square
        # brackets, preventing accidental matches inside rubies.
        # 2 `(?:\[.*?\]|.{0})`: A non-capturing group that matches:
        #     a Ruby inside square brackets (`\[.*?\]`)
        #     OR
        #     b An empty string (`.{0}`), effectively allowing for matches with no rubies present.
        #
        # So, furigana_regex matches either a ruby enclosed in square brackets or allows for zero
        # characters to match (empty match).

        # skip_brackets skips looking for morphs inside ruby <rt> tags. This prevents finding
        # morphs in pronunciations. If the user has specified to parse inside brackets, we disable
        # this rule.

        # skip_parens, skip_slim_parens these skip looking for morphs inside parens, unless the
        # user has specified to parse inside them.

        # Then we create a new string by inserting the furigana_regex pattern between each character of
        # the morph string. For example, if morph is "abc", this would generate:
        #
        # a(?![^\[]*\])(?:\[.*?\]|.{0})b(?![^\[]*\])(?:\[.*?\]|.{0})c(?![^\[]*\])(?:\[.*?\]|.{0})
        #
        # This ensures that each character is tested for, with the optional possibility that there is
        # a ruby in the middle (or on the end) of it.

        # Finally, we layer all these subparts together, and add a "not in <span> tags check."
        #
        # We use a novel technique for ensuring that we're outside of some tag types.
        # it's described here: https://stackoverflow.com/questions/23589174/regex-pattern-to-match-excluding-when-except-between
        # the TL;DR version is that it's a way to use a short circuit operator in a regex.
        # the only 'extra work' you need to do in your code to use it is `if match.group(1):`
        # this is because the regex will match in the false cases, but the capture group will be
        # empty. It will be populated in the positive cases.

        # Matching Examples
        # "abc"
        # "a[kana]bc"
        # "ab[kana]c"
        # "abc[kana]"

        # Non-Matching Examples
        # "<span>abc</span>"
        # "<rt>abc</rt>"
        # "<span>abc[kana]</span>"
        # "a<span>b</span>c"
        # "a[[kana]]b"
        # "[kana]abc"

        furigana_regex = r"(?![^\[]*\])(?:\[.*?\]|.{0})"
        skip_brackets = r"<rt.*?</rt>|" if preprocess_ignore_bracket_contents else ""
        skip_parens = r"（[^（]*）|" if preprocess_ignore_round_bracket_contents else ""
        skip_slim_parens = (
            r"\([^(]*\)|" if preprocess_ignore_slim_round_bracket_contents else ""
        )
        morph_regex = (
            furigana_regex.join([re.escape(morph_char) for morph_char in morph])
            + furigana_regex
        )
        return rf"<span.*?</span>|{skip_brackets}{skip_parens}{skip_slim_parens}({morph_regex})"
