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

