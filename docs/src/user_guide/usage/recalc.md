# Recalc

![recalc_example.png](../../img/recalc_example.png)

Recalc is short for “recalculate”, and is basically the command that tells AnkiMorphs to work all its
magic. When you run Recalc, AnkiMorphs will go through
the [cards that match any 'Note Filter'](../setup/settings/note-filter.md) and do the following:

* Update the `ankimorphs.db` with any new seen morphs, known morphs, etc.
* Calculate the [score of the cards](#scoring-algorithm), and then sort the cards based on that score.
* Update any cards' [extra fields](../setup/settings/extra-fields.md) and [tags](../setup/settings/tags.md).

Basically, when you run Recalc, AnkiMorphs will go through your collection, recalculate
the difficulty of your cards based on your new knowledge, and reorder your new cards in a way that’s optimal for the new
you: the you who knows more than you did yesterday.

You can run Recalc as often as you like, but you should run it at least once before or after every study session so that
your new cards will appear in the optimal order.

It's easy to forget to run recalc, so you can also
check the [`Recalc on sync` settings option](../setup/settings/recalc.md), which will take care of recalc for you by
running it automatically before Anki syncs your collection.

> **Note**: Recalc can potentially reorganize all your cards, which can cause long sync times.
> The [Anki FAQ](https://faqs.ankiweb.net/can-i-sync-only-some-of-my-decks.html) has some
> tricks you can try if this poses a significant problem.

### Scoring Algorithm

Low scores are good, high scores are bad; the more comprehensible and important a text is evaluated to be, the lower the
score will end up being.

The algorithm is as follows:

$$$ \large \text{Score} = U_n \times U_p + \sum_{m \in M}{m_p} $$$

where
$$$
\begin{align*}
& U_n = \text{The number of unknown morphs} \\
& U_p = \text{Unknown morph penalty} = 5 \times 10^5\\
& M = \text{The set of morphs}\\
& m_p = \text{The priority given to morph } m\\
\end{align*}
$$$

Note that the sum of [morph priorities](../setup/prioritizing.md) is capped to be less than the unknown morph penalty,
which gives us the inequality:

$$$ \large 0 \le \left(\sum_{m \in M}{m_p}\right) < U_p $$$

This makes sure that one unknown morph is calculated to be more difficult than any number of known rare morphs.

