This is the source code that was created as part of "Expressions of Change".

An overview of that project can be found on its [website](https://www.expressionsofchange.org/)

## Nerf0 and Nerf1

We can actually distinguish 2 projects, "nerf0" and "nerf1" ("nerf", the Dutch word for wood grain, being yet another metaphore of how the mechanism of growth has a direct effect on the grown product)

The present project is nerf1.

The brief summary of which project to refer to is:

### Nerf0:

* Static Analysis (first steps)
* mini-interpreter
* Alternative Clef, in which a note `Replace` may replace a given node with one that can be constructed from an arbitrary history (not just a history that's the result of extending the given history) -- this approach also has consequences on how undo may be modelled.
* merging ("weaving") of 2 histories (first steps only)

### Nerf1:

* the most up to date Clef
* work on visualising modifications in a more human friendly way

(Nerf1 was created by "scavenging" code from nerf0; The primary goal: to adhere much more closely to the Clef that is presented in the paper "Clef Design", as presented on ELS '18. In fact, the Clef in this project differs from the presented Clef in one important way: Insert & Delete take a single note, rather than a score, as an argument This is the program that was used in the demo for the presentation at ELS.)

Both projects should be seen as sketches, as bases for experiments, more so than as a finished product that is in any sense ready for production.

Don't hesitate to ask if anything is unclear.

## Installing

AFAIK all that's needed to run this is Python 3.5 or 3.6 with Kivy 1.10. Let me know if that isn't sufficient.

I'm personally using the provided nix shell expression (but I haven't yet pushed Kivy to nixpkgs, so this will be hard to reproduce).

## Available commands

Editing is done using vim-style keyboard shortcuts, some mouse input handling is also available.

There is no manual available (yet); best to refer to `widgets/tree.py`, `generalized_key_press` and `vim.py` to get a sense of what these commands are.

