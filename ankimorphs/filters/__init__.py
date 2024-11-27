from anki import hooks

from .am_highlight_morphs import am_highlight_morphs


def register_filters() -> None:
    """Register all filters that AnkiMorphs provides."""
    hooks.field_filter.append(am_highlight_morphs)


register_filters()
