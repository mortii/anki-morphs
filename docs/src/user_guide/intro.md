<br>
<div style="text-align: center;">
<i>
A huge thank you to Matt Vs Japan (<a href="https://www.youtube.com/@mattvsjapan">Youtube</a>, <a href="https://twitter.com/mattvsjapan">Twitter</a>) for his absolutely <br> amazing work on the original version of the user guide!
</i>
</div>
<br>

# Intro

AnkiMorphs is an Anki add-on that keeps track of what words you know and uses that to reorder your new cards into an
optimal order for learning.

You tell AnkiMorphs which decks/cards/fields you want it to look at, and it goes through and parses all the text in those
fields into [“Morphs”](glossary.md#morph) (basically, words). It assumes you already know all the Morphs contained
within the cards you’ve learned. In this way, it creates a database of your current knowledge and uses that database to
analyze how many unknown Morphs are contained within each of your new cards.

It then reorders your new cards based on difficulty so that you see the easiest cards (i.e., the cards with the fewest
number of unknown Morphs) first. AnkiMorphs only reorders your new cards; it doesn’t touch the scheduling of cards you’ve
already learned. You can tell AnkiMorphs to re-analyze and reorder your cards as often as you like. This allows you to
always learn new cards in a [1T](glossary.md#1t-sentence) fashion.

This guide is an attempt to explain how AnkiMorphs functions as simply as
possible. Feel free to skip straight to [Installation](installation.md), [Setup](setup.md), or [Usage](usage.md), and
refer back to
the [Glossary](glossary.md) whenever clarification is needed. 