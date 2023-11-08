# Glossary

### 1T Sentence

Abbreviation for “one-target sentence”. A sentence that contains one unknown word or grammar structure. The unknown word
or structure is referred to as the “target word” or “target structure”.

Learning through 1T sentences can be thought of as “picking low-hanging fruit”. It makes the target word/structure easy
to understand and retain. As you continue to learn, sentences that were previously one-target will become zero-target,
and sentences that were previously multi-target will become one-target. In this way, one-target sentences can take you
all the way to fluency.

[Learn about the "Input Hypothesis"](https://en.wikipedia.org/wiki/Input_hypothesis)

### MT Sentence
Abbreviation for “multi-target sentence”. A sentence that contains **more than** one unknown word or grammar structure.

### Morph

Short for the word "morpheme." A morpheme is the smallest grammatical unit of speech; it may be a word, like
"place" or "an," or an element of a word, like re- and -ed in "reappeared."[^britannica]

[^britannica]: [Britannica's morpheme definition](https://www.britannica.com/topic/morpheme)

### Seen

When a card has been reviewed and a morph was in the targeted field of the card, the morph will be considered "seen".

### Unknown

A Morph that has never been “seen”.

### Mature

A card that has an interval of at least 21 days is considered "mature" and any morphs in the targeted field of the
card will also be considered mature. Morphs added through “external.db” are automatically counted as mature.

### Unmature

A Morph that is “seen” but not yet “mature”.

### Focus Morph

The unknown morph(s) of [the field you specified in the Note Filter](setup/preferences/note-filter.md)

### sub2srs

You can get automatically generated Anki cards from tv-shows or movies by using a tool called sub2srs. Generating decks
with sub2srs is pretty technical so I recommend finding sub2srs decks other people
have already made.

[You can download many different anime sub2srs decks from this site.](https://www.mediafire.com/folder/p17g5uk4phb41/User_Uploaded_Anki_Decks)

[Read more about sub2srs here](https://learnanylanguage.fandom.com/wiki/Subs2srs)

### Databases

MorphMan uses seven different databases to keep track of what you know and how well you know it. Four of the seven are
necessary for MorphMan to function and are generated automatically. The other two are for additional features and must
be manually created by the user.

The databases are stored in the following directory:

* Windows: `C:\Users\[user]\AppData\Roaming\Anki2\[profile_name]\dbs.`
* Mac: `/Users/[user]/Library/Application Support/Anki2/[profile_name]/dbs`
* Linux: `/home/[user]/.local/share/Anki2/[profile_name]/dbs`



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

