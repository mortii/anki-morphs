# Note Filter

![settings-note-filter.png](../../../img/settings-note-filter.png)

AnkiMorphs only analyzes and sorts cards that match at least one note filter; if you don't specify any note filters,
then AnkiMorphs won't do anything, so this is a necessary step. This can seem overly complicated and overwhelming, but
hopefully things will make sense after reading to the end of this page. This is really the heart of the add-on, and it
has some powerful options (notably [tags](note-filter.md#tags)), so having a good understanding of note filters work
might significantly improve how much you benefit from AnkiMorphs.

Each note filter contains:

* [Note Type](note-filter.md#note-type)
* [Tags](note-filter.md#tags) (optional)
* [Field](note-filter.md#field)
* [Morphemizer](note-filter.md#morphemizer)
* [Morph Priority](note-filter.md#morph-priority)
* [Read & Modify](note-filter.md#read--modify) (optional)

## Note Type

To find a card's note type do the following:

<video autoplay loop muted controls>
    <source src="../../../img/note-type.mp4" type="video/mp4">
</video>

1. Go to Browse
2. Find a card you want AnkiMorphs to analyze and sort
3. Right-click the card
4. Click Info
5. See `Note Type`

All the cards in my `Japanese Sentences` deck (and sub-decks) have the same note type, but that might not be the case
for your decks.

Another thing you can do is look through the `Note Types` in the left sidebar and until you find the cards you are
after.

![note-types-browser.png](../../../img/note-types-browser.png)

## Tags

You can further filter AnkiMorphs to only work on cards with a certain note type **and** with/without specific tag(s).

Let's use an example of having a note type: `anime_sub2srs`. The card break-down of the note type is the following:

- Total cards: 20K
- Cards with the tag `demon-slayer`: 6k
- Cards with the tag `movie`: 3k
- Cards with the tag `fight-scene`: 2k
- Cards that have **both** `demon-slayer` and `movie` tags: 1k

If you want all the 20K cards of note type `anime_sub2srs` then leave the tags empty (default):

![default-tag-selection.png](../../../img/default-tag-selection.png)

If you want the 6K cards with the `demon-slayer` tag:

![tag-include-one.png](../../../img/tag-include-one.png)

If you want the 1k cards that have **both** `demon-slayer` and `movie` tags, i.e. the intersection:

![tag-include-two.png](../../../img/tag-include-two.png)

If you want the 8K cards that have **either** `demon-slayer` or `movie` tags, i.e. the union, then you have to create
two note-filters like this:

![intersection-tags.png](../../../img/intersection-tags.png)

If you want the 18K cards that don't have the `fight-scene` tag:

![tag-exclude-one.png](../../../img/tag-exclude-one.png)

## Field

This is the field on the card AnkiMorphs reads and analyzes, which is then used to sort the card.

![browser-note-fields.png](../../../img/browser-note-fields.png)

1. Go to Browse
2. Find the note type in the left sidebar
3. Find the field you care about

In my case the field I'm interested in is `Japanese`

> **Note**: Fields with complete sentences are preferable over fields that only have isolated words. The more context 
> the morphemizers are given, the less likely they are to produce false positives.

## Morphemizer

This is the tool AnkiMorphs uses to split text into morphs. See the [installation section](../../installation.md) for 
how to add morphemizers. 

![morphemizer-selection.png](../../../img/morphemizer-selection.png)


### Simple Space Splitter
As the name suggests, this morphemizer just splits words based on whitespace and does not perform any
linguistic analysis, meaning they won't provide accurate [lemmas](../../glossary.md#lemma). You should only
use this if no other morphemizers are available for your particular target language.

If you use this morphemizer, punctuation and other unwanted characters will likely be included in the morphs. To fix this,
you can specify custom characters to ignore in [the preprocess settings](preprocess.md).


## Morph Priority

The calculated [score](../../usage/recalc.md#scoring-algorithm) of the card, and as a result, the sorting of the card, depends on
the [priority](../prioritizing.md) you give the morphs. You can either set the priorities to be `Collection frequency` (how often the
morphs occur in your card collection), or you could use a [custom priority file](../prioritizing.md#custom-priority-files) that specifies the priorities of
the morphs.

AnkiMorphs automatically finds `.csv` files placed
in [[anki profile folder](../../glossary.md#profile-folder)]`/priority-files/`.

> **Note:** using `Collection frequency` is not recommended because it can be volatile; if you make any changes to your
> cards (delete, suspend, move, etc.), then a cascade of sorting changes can occur.

## Read & Modify

If, for whatever reason, you don't want AnkiMorphs to read one of the note filters you have set up, then you
can uncheck the `Read` option.

If you uncheck `Modify`, AnkiMorphs will analyze the
specified fields of cards (and update the database of known morphs based on them), but won’t reorder
or change the cards in any way.

<br>
<br>

# Usage

There are some nuances that are important to be aware of when it comes to note filters:

### Order of the note filters

![filter-order.png](../../../img/filter-order.png)

Order matters. In the image above all the cards that have note type `japanese_sub2srs` will have the text found in
the `Japanese` field analyzed, and then those cards will be sorted based on
the score of that text.

**After those cards are analyzed and sorted** then the next note filter will take effect: All the cards that have the
note type `kanji` will have the text found in the `Front` field analyzed and then those cards will be sorted based on
the score of that text.


### Overlapping filters

If a card matches multiple filters, then it will **only** be analyzed and sorted based on the **first matching filter**.
Any subsequent filters will not analyze and sort the card.

If you were to do something like this:

![overlapping-filters.png](../../../img/overlapping-filters.png)

Then the second filter would do nothing because all the cards would have already been used by the first filter.

If you find yourself in a situation where you have overlapping note filters, then there are two things you can do:

- Make the filters more restrictive by using [tags](#tags)
- Create a new note type.

> **Tip:** All your cards should
> follow [the minimum information principle](https://supermemo.guru/wiki/Minimum_information_principle), not only will
> that help you remember them better, but it might make the note filters less complicated.