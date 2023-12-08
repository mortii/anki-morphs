# Tips & Tricks

### FSRS4Anki

I _**highly**_ recommend using the [FSRS4Anki add-on](https://ankiweb.net/shared/info/759844606). If you have a
non-trivial amount of cards this will change your life. It optimizes the scheduling of cards and will drastically reduce
the amount of due cards you have everyday.

### Learning specific media

If you want to learn a specific piece of media, e.g. a book, a movie, etc., then using a more specialized/targeted
[frequency.csv](prioritizing.md#frequencycsv) can help you reach your goal faster than if you were to use a more general
frequency.csv. You should only really do this after you have already learned **at least** the most frequent 2k morphs
from a general frequency.csv--If you start to specialize too early you can fall into the trap of 'over-fitting'
your vocabulary and understanding of the language.

### Reverting AnkiMorphs changes

There are a couple of ways to revert the changes AnkiMorphs has made to your card collection:

- Restore from a previous backup you made.
- if you haven't made a backup in a while, then you can use the following method to revert your collection to
  how it was the last time you synced:  
  `Browse -> Fields -> add a new field -> save -> Download from AnkiWeb`
  <br>
  <br>
  <video autoplay loop muted controls><source src="../../img/revert_changes.mp4" type="video/mp4"></video>
  <br>
- If you only want to revert how AnkiMorphs sorted the cards, then you can do the following:    
  `Browse -> Card State -> New cards -> Select all (Ctrl + A) -> Forget -> Restore original position where possible`