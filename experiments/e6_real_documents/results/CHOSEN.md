# E6: the methods judged on the closed pile, written down before it is touched

Committed after the open pile was scored and its errors were read, and before any detector
was run on the closed pile. The commit order shows that this file came before the closed
pile's run files and tables were committed; that no detector was run on the closed pile
before it rests on the author's word and on the dates of the run files.

Between backticks in this file stand the methods that are judged and nothing else: the
harness scores the closed pile for a name it finds here between backticks. Other methods
are named without them.

The eight, by the list of PREREGISTRATION.md, "What is judged on the closed pile":

1. `joint + whole words`
2. `joint + carry`
3. `joint + titles, carry`
4. `golem + whole words`
5. `golem + carry`
6. `golem at 0.03 + titles, carry`
7. `joint + titles, carry strong`
8. the same as 7
9. `joint + carry strong, titles`

**Item 7**, the open pile's method with the highest recall, by E5's order. Eight methods
find all 242 counted names of the open pile. Of those, joint with titles and carry strong
marks the fewest words for nothing without titles, 62; the next, the union of joint and
large with no step, marks 87 (results/open.md, the first rows).

**Item 8**, the method with the highest recall among those that mark fewer than 5 more words
per 1,000 for nothing, titles left out, than their base row. Two of the eight that find
every name pass that limit: joint with titles and carry strong (3.05 per 1,000 against 0.69
of its base row, 2.36 more) and the union of joint and large with no step, which is its own
base row. E5's order puts the first before the second, so item 8 is item 7.

**Item 9**, the one fitted method. After the open pile's errors were read: in the stack of
titles and then carry, the word after a title is marked whatever it is, and carry spreads
it. The fitted method is E5's two steps in the other order, on the plan's model. On the
open pile it finds 242 of 242 and marks 57 words for nothing, 2.80 per 1,000
(results/open_fitted.md). That number says how well it was fitted and nothing else. No
other method is fitted; the pre-registration allows three.

Only the detectors joint and golem are needed for these, so only those two detectors are run on the
closed pile.

## What was seen of the open pile before this was written

The table of all 70 methods (results/open.md), and for seven methods, the six of items 1
to 6 and item 7, every counted name each did not find and every word each marked outside
the key, with the text around it, in a file outside the repository: 155 different words.

- The plan's model with whole words misses 4 of 242: two initials of judges that stand
  before a surname the model marked, one surname alone, and half of a full name on a line
  of its own. Carry finds the last two; the titles find the two initials.
- Among the 155 words marked outside the key there is no person's name that the key
  lacks as a counted name. So the open pile's numbers are not given a second time: they
  would be the same. Three of the words may be a person's name inside the name of a
  company in the title of a cited decision, which the key would hold as not counted.
- Most of the words marked for nothing by carry are one everyday word spread through one
  document: a role word that the model marked once inside the title of a cited decision
  (about 35 times), the name of a court (9 times), a relative word that is also a given
  name. With carry strong the first of these is gone.

Nothing of the closed pile was seen but the counts of its labels.
