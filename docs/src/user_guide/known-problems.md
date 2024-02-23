# Known Problems

<details>
  <summary style="display:list-item">Undoing 'set known and skip'</summary>

> There is a bug that occurs when you do the following:
>    1. Open Anki
>    2. Go to a deck and click 'Study Now'
>    3. Only 'set known and skip' cards
        > <br>
>
>  If you do this then those actions cannot be undone immediately.
> You can easily fix this by simply answering (or basically doing anything to) the next card, and you can now just undo
> twice and the previous 'set known and skip' will be undone.
>
>  This is a weird bug, but I suspect it is due to some guards Anki has about not being able to undo something until the
> user has made a change manually first ('set known and skip' only makes changes programmatically).
>
</details>


<details>
  <summary style="display:list-item">Redo is not supported</summary>

> Redoing, i.e. undoing an undo (Ctrl+Shift+Z), is a nightmare to handle with the current Anki API. Since it is a rarely
> used feature, it is not worth the required time and effort to make sure it always works. Redo _might_ work just fine,
> but
> it also might not. Use it at your own risk.
</details>



<details>
  <summary style="display:list-item">Freezing when reviewing</summary>

> AnkiMorphs uses the Anki API to run in the background after you answer a card, which then
> displays a progress bar of how many cards have been skipped:
>
> <img src="../img/skipping-progress.png" alt="image" width="40%" height="auto">
>
> The Anki API has a rare bug where it sometimes gets in a deadlock and just says 'Processing...' forever.
>
> <img src="../img/skipping-freeze.png" alt="image" width="40%" height="auto">
>
> When this happens you have to restart Anki.

</details>


<details>
  <summary style="display:list-item">Morphs don't split on punctuation marks</summary>

> Most morphemizers don't split text on punctuation marks because it would split phrases like `10 a.m.`
> into `[10, a, m]`, which would be unideal.
>
>This can cause problems when there are line breaks on Anki cards:
>
>```plaintext
>Hello.
>Goodbye.
>```
>
>The text is actually stored as:
>
>```plaintext
>Hello.<br>Goodbye.
>```
>
>Most morphemizers completely ignore the unicode equivalent of `<br>`, which results in them interpreting the text as:
>
>```plaintext
>Hello.Goodbye.
>```
>
>To fix this problem, you can add a whitespace between the punctuation mark and the `<br>` tag.
>```plaintext
>.<br>
>. <br>
>```
>This can be done in bulk with
> the `find and replace` feature in the Anki browser:
![find_and_replace_split.png](../img/find_and_replace_split.png)


</details>


<details>
  <summary style="display:list-item">Ruby characters (furigana, etc.) are displayed wrong in am-highlighted</summary>

> When morphs are not recognized in the same way that the ruby characters intended, then we can get ugly things like this:
>
> <img src="../img/furigana-bug.png" alt="image" width="70%" height="auto">
>
> This is because `錬金術師` gets split into -> `[錬金術, 師]` and the ruby characters are after the second morph, so
> they only attach to that one. Fixing this programmatically is not possible, unfortunately. 
> 
>If you _really_ wanted to
> fix this particular card then you would have to do some manual editing to the ruby characters in the original field,
> e.g. splitting it into two different parts:
> ``` 
> original:
> 錬金術師[れんきんじゅつし]
> 
> split:
> 錬金術[れんきんじゅ]師[つし]
> ```
> then you get this:
> 
> <img src="../img/furigana-bug-fixed.png" alt="image" width="60%" height="auto">

</details>

