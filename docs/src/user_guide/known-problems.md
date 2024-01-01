# Known Problems

### Set known and skip

- There is a bug that occurs when you do the following:
    1. Open Anki
    2. Go to a deck and click 'Study Now'
    3. Only 'set known and skip' cards

  <br>
  If you do this then those actions cannot be undone immediately.
  You can easily fix this by simply answering (or basically doing anything to) the next card, and you can now just undo
  twice and the previous 'set known and skip' will  be undone.

  <br>
  <br>
  This is a weird bug, but I suspect it is due to some guards Anki has about not being able to undo something until the
  user has made a change manually first ('set known and skip' only makes changes programmatically).

### Redo is not supported

Redoing, i.e. undoing an undo (Ctrl+Shift+Z), is a nightmare to handle with the current Anki API. Since it is a rarely
used feature it is not worth the required time and effort to make sure it always works. Redo _might_ work just fine, but
it also might not. Use it at your own risk.

### Freezing when reviewing

AnkiMorphs uses the Anki API to run in the background after you answer a card, which then
displays a progress bar of how many cards have been skipped:

<img src="../img/skipping-progress.png" alt="image" width="40%" height="auto">

The Anki API has a rare bug where it sometimes gets in a deadlock and just says 'Processing...' forever.

<img src="../img/skipping-freeze.png" alt="image" width="40%" height="auto">

When this happens you have to restart Anki.
