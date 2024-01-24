<br>
<div style="text-align: center;">
<i>
A huge thank you to Matt Vs Japan (<a href="https://www.youtube.com/@mattvsjapan">Youtube</a>, <a href="https://twitter.com/mattvsjapan">Twitter</a>) for his absolutely <br> amazing work on the original version of the user guide!
</i>
</div>
<br>

# Intro

AnkiMorphs is an Anki add-on that can reorder your cards based on how well you know the words on them and how important
the words are to learn. This makes it so your cards are in the ideal order for optimal language learning.

AnkiMorphs goes through the text on the cards you specify, and parses the text
into [morphs](user_guide/glossary.md#morph) (basically words). It assumes you already know all the morphs
contained within the cards you’ve learned. In this way, it creates a database of your current knowledge and uses that
database to analyze how many unknown morphs are contained within each of your new cards.

It then reorders your new cards based on their [difficulty](user_guide/usage/recalc.md#difficulty-algorithm) so that you
see the easiest cards (i.e., the cards with the fewest
number of unknown morphs) first. AnkiMorphs only reorders your new cards; it doesn’t touch the scheduling of cards
you’ve
already learned. You can tell AnkiMorphs to re-analyze and reorder your cards as often as you like. This allows you to
always learn new cards in a [1T](user_guide/glossary.md#1t-sentence) fashion.

This guide is an attempt to explain how AnkiMorphs functions as simply as
possible. Feel free to skip straight to [Installation](user_guide/installation.md), [Setup](user_guide/setup.md),
or [Usage](user_guide/usage.md), and
refer back to
the [Glossary](user_guide/glossary.md) whenever clarification is needed. 