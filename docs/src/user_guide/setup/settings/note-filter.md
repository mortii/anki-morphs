# Note Filter

![settings-note-filter.png](../../../img/settings-note-filter.png)

AnkiMorphs only analyzes and sorts cards that matches at least one "note filter"; if you don't specify any note filters
then AnkiMorphs
won't do anything, so this is a necessary step.

Each note filter contains:

* [Note Type](note-filter.md#note-type)
* [Tags](note-filter.md#tags) (optional)
* [Field](note-filter.md#field)
* [Morphemizer](note-filter.md#morphemizer)
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
5. See Note Type

All the cards in my "Japanese Sentences" deck (and sub-decks) have the same note type, but that might not be the case
for your decks.

Another thing you can do is look through the "Note Types" in the left sidebar and until you find the cards you are
after.

![note-types-browser.png](../../../img/note-types-browser.png)

## Tags

You can further filter AnkiMorphs to only work on cards with a certain note type **and** specific tag(s).

Let's use an example of having a note type: `note_type1`. The card break-down of the note type is the following:
- Total cards: 20K
- Cards with the tag `demon-slayer`: 6k
- Cards with the tag `movie`: 3k
- Cards that have **both** `demon-slayer` and `movie` tags: 1k


If you want all the 20K cards of note type `note_type1` then leave the tags empty:
```
Note Type                   Tags            
1. note_type1               
```

If you want the 6K cards with the `demon-slayer` tag:
```
Note Type                   Tags            
1. note_type1               demon-slayer
```

If you want the 1k cards that have **both** `demon-slayer` and `movie` tags, i.e. the intersection,:
```
Note Type                   Tags            
1. note_type1               demon-slayer, movie
```

If you want the 8K cards that have **either** `demon-slayer` or `movie` tags, i.e. the union,:
```
Note Type                   Tags          
1. note_type1               demon-slayer
2. note_type1               movie 
```

## Field

This is the field on the card AnkiMorphs reads and analyzes, which is then used to sort the card.

![browser-note-fields.png](../../../img/browser-note-fields.png)

1. Go to Browse
2. Find the note type in the left sidebar
3. Find the field you care about

In my case the field I'm interested in is "Japanese"

## Morphemizer

This is the [parsing dictionary](../../installation/parsing-dictionary.md) AnkiMorphs uses to find morphs.

## Read & Modify

If for whatever reason you don't want AnkiMorphs to read one of the note filters you have set up then you
can uncheck the "Read" option.

If you uncheck “Modify”, AnkiMorphs will analyze the
specified fields of cards (and update the database of learned/mature Morphs based on them), but won’t actually reorder
or change the cards in any way.




