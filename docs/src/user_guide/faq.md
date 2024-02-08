# Frequently Asked Questions

### Can you add make AnkiMorphs work on Anki qt5?

No, supporting multiple versions of Qt is too detrimental to the project's workflow and code-base.

[The last release of Qt 5 was in May 2023](https://www.qt.io/blog/the-conversion-program-is-ending), so using Qt 6 is
the sensible thing to do.

### Transitioning from MorphMan

> Should I add a note-filter row for both my sentence field and my focus morph field?

No, only use the sentence field.

> Should I use the same tags in AnkiMorphs that I was using with Morphman?

I recommend using the default AnkiMorphs tags. Mixing tags can get confusing.

> Should I export all of studied and in progress words into a CSV spreadsheet?

AnkiMorphs determines which morphs are known in the same way MorphMan does it--by how long the learning
intervals of the cards are. The [Known Morphs Exporter](usage/known-morphs-exporter.md) is more of a tool for trimming
your card collection, it's not a requirement for transitioning from MorphMan.

If you want to retain the morphs on cards that you have tagged as known with MorphMan, then I recommend bulk tagging
those
cards with `am-known-manually`:

1. Open `Browse`
2. Select the MorphMan known tag in the sidebar
3. Select all those cards
4. Go to `Notes` in the topbar and click on `Add Tags` (or use Ctrl+Shift+A)
5. Enter the tag `am-known-manually`

That approach could be overkill though. I wouldn't worry too much about losing known morphs from the cards you tagged as
known with MorphMan, you can usually get them back quickly by using `K` when you encounter them when using AnkiMorphs.


> Should I manually delete the words in the focus morph field of my cards so that AnkiMorphs can cleanly reparse
> everything?

AnkiMorphs does not reuse the MorphMan focus morph field, so it makes no difference.
