# MorphMan Recalc

<video autoplay loop muted controls>
    <source src="../../img/recalc.mp4" type="video/mp4">
</video>

Recalc is short for “recalculate”, and is basically the command that tells MorphMan to work all its
magic. When you run Recalc, MorphMan will go through
the [cards that matches any 'Note Filter'](../setup/preferences/note-filter.md) and do the following:

* Update the MorphMan [databases](../glossary.md#database-db) with any new seen morphs, known morphs, etc.
* Reorder your cards based on their [MorphMan Index](../glossary.md#morphman-index-mmi).
* Update each card's [focus morph](../setup/preferences/extra-fields.md) and [tags](../setup/preferences/tags.md).

Basically, when you run Recalc, MorphMan will go through your collection, recalculate
the difficulty of your cards based on your new knowledge, and reorder your new cards in a way that’s optimal for the new
you: the you who knows more than you did yesterday.

You can run Recalc as often as you like, but you should run it at least once before or after every study session so that your
new cards will appear in the optimal order.



### MorphMan Index (MMI)

MorphMan sorts your cards in accordance with their MorphMan Index, the lower the MMI the sooner the card will be shown.
The formula is:

$$$ MMI = 100000U_k + 1000L + \round{U_n} $$$

where
$$$
\begin{align*}
& U_k = \text{Unknown morphs} \\
& L = \text{Distance from ideal sentence length} \\
& U_n = \text{Usefulness}
\end{align*}
$$$

In other words, cards are first sorted by the number of unknown Morphs they contain. This means that 0T cards (or what
MorphMan calls “comprehension” and “fresh vocab” cards) will be at the very top (although in MorphMan Preferences you
can tell MorphMan to always skip these cards). Then 1T cards, then multi-target (MT) cards.

Cards with the same number of unknown Morphs are then further sorted using a point system. Points are calculated using
the following criteria:

* Cards with sentences that are too long or too short are penalized. For each Morph under the “minimum good sentence
  length” or above the “maximum good sentence length”, 1,000 points are added. There is a maximum penalty of 9,000.
  By default, the “minimum good sentence length” is 2 and the “maximum good sentence length” is 8. This can be changed
  in config.py.
* Cards with unknown Morphs contained in frequency.txt are boosted proportionally to how high their position is in
  frequency.txt. The formula for determining the boost is, for each unknown Morph contained in frequency.txt, “‘total
  number of words in frequency.txt’ minus ‘position in frequency.txt’, times ‘frequency weight'”. The default the
  “frequency weight” is 10. This can be changed in config.py.
* Cards with Morphs contained in priority.db are boosted. By default, for each unknown Morph contained in priority.db,
  200 points are deducted. This amount can be changed in config.py.
* If at least one of the unknown Morphs in a card is a verb, the card is given a flat boost. By default, the boost is
  100 points. This amount can be changed in config.py.
* Cards are boosted proportionally to how frequently their unknown Morphs show up within the portion of your Anki
  collection that MorphMan looks at. By default, for every occurrence of the unknown Morph in your collection, 5 points
  are deducted. This can be changed in config.py. If a card contains multiple unknown Morphs, the boost is calculated
  using
  the average number of occurrences of each unknown Morph.
* Cards with unmature (“known” but not yet “mature”) Morphs are boosted. The boost is calculated by dividing the
  “reinforce new vocab weight” by the interval of the most mature card containing that Morph. For Morphs whose most
  mature card has an interval of less than 1 day, .5 is used in place of the interval. If a card contains multiple
  unmature Morphs, the points for each Morph are added up. The default “reinforce new vocab weight” is set to 5. This
  can be changed in config.py.

