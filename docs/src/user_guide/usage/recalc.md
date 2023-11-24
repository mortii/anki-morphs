# Recalc

<video autoplay loop muted controls>
    <source src="../../img/recalc.mp4" type="video/mp4">
</video>

Recalc is short for “recalculate”, and is basically the command that tells AnkiMorphs to work all its
magic. When you run Recalc, AnkiMorphs will go through
the [cards that matches any 'Note Filter'](../setup/settings/note-filter.md) and do the following:

* Update the ankimorphs.db with any new seen morphs, known morphs, etc.
* Calculate the difficulty of the cards, and then sort the cards based on that difficulty.
* Update any card's [extra fields](../setup/settings/extra-fields.md), and [tags](../setup/settings/tags.md).

Basically, when you run Recalc, AnkiMorphs will go through your collection, recalculate
the difficulty of your cards based on your new knowledge, and reorder your new cards in a way that’s optimal for the new
you: the you who knows more than you did yesterday.

You can run Recalc as often as you like, but you should run it at least once before or after every study session so that
your new cards will appear in the optimal order.

It's easy to forget to run recalc, so you can also
check [the `Recalc on sync` settings option](../setup/settings/recalc.md), which will take care of recalc for you by
running it automatically before Anki syncs your collection.


