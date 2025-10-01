# General

![general-tab.png](../../../img/general-tab.png)

## Morph Evaluation

* **Evaluate morphs based on their lemma or inflection**:  
  This impacts the two things:
  * [scoring algorithm](../../usage/recalc.md#scoring-algorithm): use the [morph priority](../prioritizing.md) associated with the [inflection or the lemma](../../glossary.md#morph).
  * [skipping](card_handling.md): skip morphs based on their lemma or inflection.


## Known Morphs

* **Morphs are considered known when [...]**:  
  This is variable is used when text is [highlighted](../../setup/settings/extra-fields.md#using-am-highlighted), and it
  determines the [L and I numbers](../../installation/changes-to-anki.md#toolbar).

* **Use FSRS card stability instead of card interval for known threshold**:  
  With the introduction of FSRS cards are now described with "Stability", which is defined as the interval when the
  Desired Retention is set to 90%. For example, if your Desired Retention is 90%, 1d interval means 1d stability.
  For 80%, a 1d stability might be equal to 2d interval, but it depends on your parameters.
  By checking this option, AnkiMorphs will use stability instead of interval. **Make sure to use FSRS** since SM2, 
  the default scheduler, doesn't compute stability. 

  This option is useful when you want have different DR in different decks that AnkiMorphs read, it avoid setting morphs
  as known if the DR being low means the interval growing too fast.

  To read more on this topic, please refer to the official
  [Anki's documentation about FSRS](https://faqs.ankiweb.net/what-spaced-repetition-algorithm.html#fsrs)

* **Read files in 'known-morphs' folder and register morphs as known**:  
  Import known morphs from the `known-morphs` folder. Read more in [Settings Known Morphs](../setting-known-morphs.md).


## On Sync

* **Automatically Recalc before Anki sync**:  
  Recalc automatically runs before Anki syncs your card collection.
  > **Note**: If you use the [FSRS4Anki Helper add-on](https://ankiweb.net/shared/info/759844606) with an `Auto [...]
  after sync`-option enabled, then this can cause a bug where sync and recalc occurs simultaneously.


## Toolbar

* **Hide toolbar items:**:  
  If you want to declutter the toolbar you can choose to hide any of the
  [toolbar items](../../installation/changes-to-anki.md#toolbar) provided by the addon.

* **Toolbar counter ('L' and 'I') shows**:  
    * **Seen morphs**:  
      Shows all morphs that have been reviewed at least once. This can be more motivating than only seeing known morphs
      since it goes up every time you study new cards, but it can also give you a false sense of confidence.

    * **Known morphs**:  
      Only show known morphs, which is determined by `Morphs are considered known when [...]` option in the [general setting](general.md).
