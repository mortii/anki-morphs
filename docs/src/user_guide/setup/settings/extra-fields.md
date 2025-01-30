# Extra Fields

![extra-fields.png](../../../img/extra-fields.png)


The text found in the [note filter: field](../settings/note-filter.md#field) is extracted and analyzed by AnkiMorphs.
AnkiMorphs can then place
information about that text into dedicated fields on your cards.

> **Note**: The first time you select an extra field, you will need to perform a full sync upload to AnkiWeb. If you
> have a large number of cards (500K+), syncing might become an issue. For more details, refer to 
> the [Anki FAQ](https://faqs.ankiweb.net/are-there-limits-on-file-sizes-on-ankiweb.html).

> **Important**: Extra fields add more data to your collection, so only select the fields that will be useful to you.

The fields contain the following:

- **am-all-morphs**:  
  A list of the morphs.

- **am-all-morphs-count**:  
  The number of morphs.
- **am-unknown-morphs**:  
  A list of the morphs that are still unknown to you.
- **am-unknown-morphs-count**:  
  The number of morphs that are still unknown to you.
- **am-highlighted**:  
  An HTML version of the text that highlights the morphs based on learning status.
- **am-score**:  
  The [score](../../usage/recalc.md#scoring-algorithm) AnkiMorphs determined the card to have
- **am-score-terms**:  
  The individual [score](../../usage/recalc.md#scoring-algorithm) terms
- **am-study-morphs**:  
  A list of the morphs that were unknown to you when you first studied the card.


The following fields will only update on [new cards](../../glossary.md#new-cards):
- am-all-morphs
- am-all-morphs-count
- am-score
- am-score-terms
- am-study-morphs

and these fields will always update, even on [reviewed cards](../../glossary.md#reviewed-cards):
- am-unknown-morphs
- am-unknown-morphs-count
- am-highlighted


<br>
Here is an example card where all the extra-fields have been selected:

![extra_fields_example_output.png](../../../img/extra_fields_example_output.png)

<br>

**The extra fields display morphs in this form**:

You can chose to display morphs in their inflected forms:
   ``` text
  "walking and talking" -> [walking, and, talking]
   ```

or their lemma (base) forms:
  ``` text
  "walking and talking" -> [walk, and, talk]
  ```

This effects the following three fields:
- am-all-morphs
- am-study-morphs
- am-unknown-morphs


## Using am-study-morphs

![unknown-morphs.png](../../../img/unknown-morphs.png)

Adding this field to your card-template can give you a quick way to see which morphs are/were unknown to you on the first encounter.
Here is a simplified version of the card template used in the example above:

![am-study-morphs-template.png](../../../img/am-study-morphs-template.png)


## Using am-*-morphs-count

This is useful if you want to sort your cards in the browser based on how many total/unknown morphs they have.

![unknowns-count-search-field.png](../../../img/unknowns-count-search-field.png)

![unknowns-sort-browser-result.png](../../../img/unknowns-sort-browser-result.png)

## Using am-highlighted

<video autoplay loop muted controls>
    <source src="../../../img/highlighting.mp4" type="video/mp4">
</video>

This field is used for static highlighting. For more details, see the [highlighting section](../../setup/highlighting.md).

