# Card Template Filters

## am-highlight

Highlights morphs based on your learning progress, just-in-time.

If there are cards that you do not wish to add the
[am-highlighted](../setup/settings/extra-fields.md#using-am-highlighted) field to, but you still would like to
highlight the morphs, even from cards that you do not process with AnkiMorphs, you can use the `am-highlight`
card template filter. It is intended to result in the same highlight capability as the
`am-highlighted` extra field. It does however incur a small overhead for the just-in-time processing. It is not
available on mobile.

To use the filter, you will need to register [a note filter](note-filter.md#read--modify) for each note type
that you would like to use the `am-highlight` filter on. If you do not want this card to be considered for
your learning progress, you can disable read and modify flags. With this setup step done, you can start adding the
filter to cards for that note type.

The `am-highlight` filter can be executed on its own, and will parse the field specified and add highlighting to all
morphs found.

```text
{{am-highlight:Reading}}
```

The `am-highlight` filter also supports
[ruby characters](https://docs.ankiweb.net/templates/fields.html#ruby-characters). To have them displayed properly,
it is required that one of the the Anki built in ruby card filters `furigana:`, `kanji:`, or `kana:` is applied to the
field in the card template before (i.e. to the right of) `am-highlight`. This is because
[Anki cannot process custom filters before built in filters](https://github.com/ankicommunity/anki-desktop/blob/main/rslib/src/template_filters.rs#L22-L24).

Correct:

```text
{{am-highlight:furigana:Reading}}
```

Incorrect:

```text
{{furigana:am-highlight:Reading}}
```

You should also have the `Ignore content in square brackets` [preprocess setting](preprocess.md) activated, to prevent
the morphemizer from finding these pronunciations.
