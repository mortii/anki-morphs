# Glossary

## 1T Sentence

Abbreviation for “one-target sentence”. A sentence that contains one unknown word or grammar structure. The unknown word
or structure is referred to as the “target word” or “target structure”.

Learning through 1T sentences can be thought of as “picking low-hanging fruit”. It makes the target word/structure easy
to understand and retain. As you continue to learn, sentences that were previously one-target will become zero-target,
and sentences that were previously [multi-target](glossary.md#mt-sentence) will become one-target. In this way, one-target sentences can take you
all the way to fluency.

[Learn about the "Input Hypothesis"](https://en.wikipedia.org/wiki/Input_hypothesis)

## MT Sentence
Abbreviation for “multi-target sentence”. A sentence that contains **more than** one unknown word or grammar structure.

## Morph

A morph is a basic unit of meaning in language. It's short for the word "morpheme," which is the smallest grammatical
unit of speech. A morpheme can be a whole word, like "book" or "run," or a part of a word, like prefixes
(re- in "rewrite") or suffixes (-ed in "walked").


### Lemma

A lemma is the base form of a word. It's the version you would typically find in a dictionary. For example:
- The lemma for "running," "ran," and "runs" is "run."
- The lemma for "better" and "best" is "good."

### Inflection

An inflection is a variation of the base form that shows different grammatical features such as tense, case, voice,
aspect, person, number, gender, mood, or comparison. For example:
- "run" (base form) can change to "running," "ran," or "runs" to show different tenses.
- "good" (base form) can change to "better" or "best" to show comparison.

### Morphs as tuples

In many language learning systems, morphs are considered as tuples containing two values: a lemma (base form) and
an inflection. Here's a simple example table showing different morphs for the verb "to break":

<table>
    <colgroup>
    <col>
    <col>
  </colgroup>
<tr>
    <th>Lemma</th>
    <th>Inflection</th>
</tr>
<tr>
    <td>break</td>
    <td>break</td>
</tr>
<tr>
    <td>break</td>
    <td>broke</td>
</tr>
<tr>
    <td>break</td>
    <td>breaking</td>
</tr>
<tr>
    <td>break</td>
    <td>broke</td>
</tr>
</table>

Understanding and breaking down morphs into lemmas and inflections can be incredibly useful for language learning.
It allows you to focus on the fundamental building blocks of words, making it easier to grasp new vocabulary and
grammatical structures. This approach can help in creating more effective and personalized study methods, potentially
leading to faster and more efficient learning.


## sub2srs

You can get automatically generated Anki cards from tv-shows or movies by using a tool called sub2srs. Generating decks
with sub2srs is pretty technical, so I recommend finding sub2srs decks other people have already made.

[You can download many different anime sub2srs decks from this site.](https://www.mediafire.com/folder/p17g5uk4phb41/User_Uploaded_Anki_Decks)

[Read more about sub2srs here](https://learnanylanguage.fandom.com/wiki/Subs2srs)

## New cards

A card is considered 'new' by Anki if it hasn't been reviewed yet, meaning you have never answered the card with
'Again', 'Hard', 'Good', or 'Easy'.

You can tell if a card is in the 'new' state when its `due` value looks like this: `New #....`

After reviewing a card, you can change its state back to 'new' by using the reset option.

###Reviewed cards

Once a card has been reviewed once, i.e. answered with either 'Again', 'Hard', 'Good', or 'Easy', it will move
from the 'new' state into the 'review' state.

## Profile folder

For AnkiMorphs to work, it needs to use some dedicated files and folders, namely:
- `ankimorphs.db`
- `names.txt`
- `priority-files/`
- `known-morphs/`

Those can be found in the Anki profile folder. The path to the Anki profile folder depends on your operating system:

* Windows: `C:\Users\[user]\AppData\Roaming\Anki2\[profile_name]`
* Mac: `/Users/[user]/Library/Application Support/Anki2/[profile_name]`
* Linux: `/home/[user]/.local/share/Anki2/[profile_name]`


