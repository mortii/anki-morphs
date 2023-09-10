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

The seven databases are:

* **all.db**:  
  Automatically generated; contains all Morphs contained within specified fields + all Morphs that have been
  imported from external.db.
* **mature.db**:  
  Automatically generated; contains all mature Morphs.
* **known.db**:   
  Automatically generated; The name of this db is misleading, it contains all morphs ever seen. It will be changed in
  the future.
* **seen.db**:  
  Automatically generated; contains all seen Morphs.
* **priority.db _[Legacy option, will be removed soon]_**:  
  Manually generated using the Database Manager; cards containing Morphs in this database will be
  prioritized over cards that would otherwise have the same MorphMan Index.
* **frequency.txt**:  
  Manually generated; functions as a frequency list. Cards with Morphs positioned higher on this list
  will be prioritized over cards with Morphs positioned lower.
* **external.db**:  
  Manually generated using the Database Manager; user-managed database that tracks outside-Anki
  knowledge.
  MorphMan assumes that all Morphs in this database are mature.

### MorphMan Index (MMI)

MorphMan sorts your cards in accordance with their MorphMan Index, the lower the MMI the sooner the card will be shown.
The formula is:

$$ MMI = 100000U_k + 1000L + \round{U_n} $$

where
$$
\begin{align*}
& U_k = \text{Unknown morphs} \\
& L = \text{Distance from ideal sentence length} \\
& U_n = \text{Usefulness}
\end{align*}
$$

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

### config.py

**[This is a legacy file that will be removed soon! The variables will be moved to the preferences GUI instead.]**

Originally, the config.py file was used to control all of MorphMan’s settings. Which
decks/note-types/fields you want MorphMan to look through, what tags you want MorphMan to add, etc., was all configured
through this file. Portions of the file are completely obsolete in the current version of MorphMan and changing
them won’t have any effect; they will simply be overwritten by whatever is specified in Preferences. But there still are
some there are some options that are controlled in config.py.

The default config.py settings are just fine, so you don’t need to mess with them if you don’t want to.

#### Editing config.py

The file is located in the following directory when installing MorphMan:

* Windows: `C:\Users\[user]\AppData\Roaming\Anki2\addons21\900801631\morph\config.py`
* Mac: `/Users/[user]/Library/Application Support/Anki2/addons21/900801631/morph/config.py`
* Linux: `/home/[user]/.local/share/Anki2/addons21/900801631/morph/config.py`

Code editors with like Notepad++ or Sublime Text have syntax highlighting, which makes viewing and editing config.py
much easier. But ultimately any text editor will do.

Once you open up config.py in your text editor of choice, here is a list of the following options you can tinker with (
remember, some options are obsolete and don’t influence MorphMan at all):

* Line 24: Mature threshold. How many days a card’s interval must be before the Morphs contained in the card are
  considered “mature”.
* Line 25: Known threshold. How many seconds has passed since a card was initially seen before the Morphs contained in
  the card are considered “known”. Once a card graduates from the learning queue, its Morphs will be considered “known”
  regardless of whether it has reached the threshold or not. If left at the default value of “10 seconds,” there will be
  no distinction between Seen and Known cards; all will be considered Known.
* Line 26: Seen threshold. How many seconds has passed since a card was initially seen before the Morphs contained in
  the card are considered “seen”.
* Line 27: Text file import maturity. Default interval given to Morphs that are manually imported by the user via the
  external.db database.
* Line 30: Ignore grammar position. If this is set to “True”, words that can function as multiple parts of speech will
  all be counted as the same Morph, regardless of what part of speech they are being used as. By default, words that can
  function as multiple parts of speech are counted as a unique Morph for each part of speech they are being used as.
  Because of this, setting this option to “True” will reduce the total number of known Morphs. Delete all.db and run
  Recalc each time you change this setting.
* Line 34: Default morphemizer. Controls which parsing dictionary the Readability Analyzer uses. Set to
  “SpaceMorphemizer” for languages with spaces between words, “CjkCharMorphemizer” for languages that use CJK
  characters, and “JiebaMorphemizer” for Chinese.
* Line 37: Set “Browse Morphs” hotkey.
* Line 38: Set “Already Known Tagger” hotkey.
* Line 39: Set “Batch Play” hotkey.
* Line 40: Set “Extract Morphemes” hotkey.
* Line 41: Set “Learn Now” hotkey.
* Line 42: Set “Mass Tagger” hotkey.
* Line 43: Set “View Morphemes” hotkey.
* Line 45: Print number of alternatives skipped. If “Skip card if focus morph was already seen today” is checked off in
  “MorphMan Preferences” > “General,” MorphMan will continue to reorder the New Card Queue while you rep to ensure that
  you only see cards that are 1T. If “Print number of alternatives skipped” is set to “True,” whenever this reordering
  happens while you are reviewing, a small notification box will briefly appear. If set to “False,” the reordering will
  still happen, but this notification box will not appear.
* Line 50: LoadAllDb. If this is set to “False”, all.db will be generate from scratch each time Recalc is run. This will
  make running Recalc take much longer.
* Line 65: Batch media fields. By specifying the fields that contain audio on your cards, you can enable the Batch Play
  option in the browser.
* Line 68: Min good sentence length. The minimum number of Morphs for a sentence to not be considered “too short”. Cards
  with sentences considered “too short” will receive a lower MorphMan Index. For Japanese, a “5” may be a good minimum.
* Line 69: Max good sentence length. The maximum number of Morphs for a sentence to not be considered “too long”. Cards
  with sentences considered “too long” will receive a lower Morph Man Index. For Japanese, a “15” may be a good maximum.
* Line 70: Reinforce new vocab weight. When a card contains unmature Morphs, the amount specified here will be divided
  by the interval of the most mature card containing that Morph, and that amount will be subtracted from the MorphMan
  Index of that card.
* Line 71: Verb bonus. The amount specified here will be subtracted from the MorphMan Index of cards that contain an
  unknown verb. The idea is that verbs tend to be more useful to learn than other parts of speech.
* Line 74: Priority.db weight. The amount specified here will be subtracted from the MorphMan Index of cards that
  contain an unknown Morph that appears in the priority.db database.
* Line 79: Frequency weight. For cards with Morphs contained within frequency.txt, the amount specified here will be
  multiplied by the “total number of words in frequency.txt” minus “Morph’s position in frequency.txt”, and that amount
  will be subtracted from the MorphMan Index of the card.
* Line 82: Only update k+2 and below. If this option is set to “True,” cards that contain more than two unknown morphs
  won’t be sorted by MorphMan. This reduces how many notes are changed after a Recalc by not updating notes that aren’t
  as important, in return reducing the sync burden.

