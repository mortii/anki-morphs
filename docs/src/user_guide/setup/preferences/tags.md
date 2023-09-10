# Tags


![tags-tab.png](../../../img/tags-tab.png)

As part of the process of sorting cards based on their difficult, MorphMan automatically adds and removes tags to the
cards you specified in the “Note Filter” tab. 

In the “Tags” tab, you can customize the names of the different tags if you want, or you can just leave them as they are and move on.

The different tags are as follows:

* **Vocab note**:  
  Note that is [1T](../../glossary.md#1t-sentence) (contains one unknown Morph).
* **Fresh vocab note**:  
  Note that contains no unknown Morphs, but one or more [unmature](../../glossary.md#unmature) Morphs.
* **Comprehension note**:  
  Note that is 0T (contains only [mature](../../glossary.md#mature) Morphs).
* **Not ready**:  
  Note that is MT (contains two or more unknown Morphs).
* **Already known**:  
  A tag that you can manually add to notes to tell MorphMan that you already know all the Morphs
  contained in the note. After a Recalc, MorphMan will add all the Morphs contained in notes with this tag to the
  database of Mature Morphs. “K” (for Known) is the hotkey for adding this tag to a card while reviewing or in the
  browser.
* **Priority**:  
  Note contains a Morph that is contained in [priority.db](../../glossary.md#databases). Will be ordered higher than Notes that would
  otherwise have the same MorphMan Index.
* **Too Short**:  
  Sentence in the specified field is too short. The threshold can be edited in [config.py](../../glossary.md#configpy).
* **Too Long**:  
  Sentence in the specified field is too long. The threshold can be edited in [config.py](../../glossary.md#configpy).
* **Frequency**:  
  Note contains a Morph that is contained in [frequency.txt](../prioritizing.md#frequencytxt).

By unchecking the “Add tags even if not required” box, only the “Vocab”, “Fresh Vocab”, “Comprehension” and “Not Ready”
tags will be added to cards.

Note that, although MorphMan will only ever change the scheduling of new cards, tags will still be added to cards you’ve
already learned. This means that, for example, the “Comprehension” tag will be added to cards you know, signifying that
they are 0T. But this doesn’t mean that those cards will be skipped when you review. Only new cards with the
“Comprehension” tag will be skipped.

Also note that, with the exception of the “Already known” tag, manually adding tags to cards will not affect MorphMan.
For example, let’s say that MorphMan said a certain card is 1T, but in reality, it’s MT. Even if you manually add the
“Not ready” tag to this card, MorphMan will simply ignore this and remove the tag after the next Recalc.
