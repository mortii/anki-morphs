# Extra Fields

![extra-fields.png](../../../img/extra-fields.png)

The text found in the [note filter: field](../settings/note-filter.md#field) is extracted and analyzed by AnkiMorphs.
AnkiMorphs can then place
information about that text into dedicated fields on your cards.

> **Note**: The first time you select an extra field you have to do a full sync upload to AnkiWeb. If you have _a lot_
> of cards (500K+), then syncing might become a problem. Read more about it on
> the [Anki FAQ](https://faqs.ankiweb.net/are-there-limits-on-file-sizes-on-ankiweb.html).

The fields contain the following:

- **am-unknowns**:  
  A list of the morphs that are still unknown to you that was found in the text
- **am-unknowns-count**:  
  The number of unknowns found
- **am-highlighted**:  
  An HTML version of the text that highlights the morphs based on learning status
- **am-difficulty**:  
  The difficulty AnkiMorphs calculated the text to have

<br>
Here is an example where all the extra-fields have been selected:

![extra_fields_example_output.png](../../../img/extra_fields_example_output.png)

## Using am-unknowns

![unknown-morphs.png](../../../img/unknown-morphs.png)

Adding this field to your card-template can give you a quick way to see which morphs are unknown to you. The example
above uses the following card-template:

![unknown-morphs-template.png](../../../img/unknown-morphs-template.png)

## Using am-unknowns-count

This is useful if you want to sort your cards in the browser based on how many unknowns they have.

![unknowns-count-search-field.png](../../../img/unknowns-count-search-field.png)

![unknowns-sort-browser-result.png](../../../img/unknowns-sort-browser-result.png)

## Using am-highlighted

<video autoplay loop muted controls>
    <source src="../../../img/highlighting.mp4" type="video/mp4">
</video>

AnkiMorphs can automatically color-code morphs based on their learning status, i.e., how well you know them.

I recommend only putting the highlighted-field on the back of cards. The reason for this is that, in order to get the
best
results, you want your SRS experience to simulate real life as much as possible. When reading in real life, you aren’t
going to be told which words you know and which you don’t. So, it makes sense to have your sentence cards reflect this.

Here is a simplified example of some of the changes you need to make to your card template to get the results shown
above. Notice that the `am-highlighted`-field is substituted for the `Japanese`-field on the back of the card.

![highlight-front-template.png](../../../img/highlight-front-template.png)

![highlight-back-template.png](../../../img/highlight-back-template.png)

You also need to add the following to the "Styling" section (choose any color you want):

``` css
[morph-status=unknown] { color: #f75464; } /* red */
[morph-status=learning] { color: #8bb33d; } /* light-green */
[morph-status=known] { color: green; }
```

You don't have to add all three, if you only want the unknown morphs to be highlighted then just add the first line.

It’s also possible to use “background-color”:

``` css
[morph-status=unknown] { background-color: #ffff99; } /* yellow */
[morph-status=learning] { background-color: #f2f2f2; } /* gray */
[morph-status=known] { background-color: #b3e6cc; } /* green */
```

![styling.png](../../../img/styling.png)

### Duplicate Audio Problem

![duplicate-audio.png](../../../img/duplicate-audio.png)

When the back of a card also has an audio field and not just the front, then both might play after each other when you
press "Show Answer". To prevent both playing you can do the following:

1. Go to deck-options
2. Scroll down to the "Audio" section
3. Activate "Skip question when replaying answer"

## Using am-difficulty

This field is really just for debugging purposes, so I recommend that you **don't** add this field to your card-template
to make it visible--it would just end up making your cards more cluttered.