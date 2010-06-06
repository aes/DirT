# DirT

DirT is an interactive browsing enhancement for the 'cd' shell builtin.

Currently, it has the following features:

 * Memory of paths visited in this shell instance. (uses environment variable)
 * Bookmarks where you can permanently remember commonly used paths.
 * Tree browser that helps alleviate the (cd, tab-tab-tab, expletive, ls)-loop
 * Dotfile hiding/unhiding
 * Homedir recognition
 * Name and path substitutions, to cope with long paths, preferred symlinked
   paths and perhaps other uses.
 * Interactive search, which does a lot for usability when branching factor is
   high.

Planned features:

 * Ignore patterns, to be rid of common nuisances. (e.g. .xvpics but not .git)

## Keys:

| Key        | Effect
| ---------- | ----------------------------------------------------------
| Up / Down  | Browse
| Enter      | Exit and cd to this directory
| Escape, q  | Quit, without doing 'cd'.
|            |
| Right      | Tree-browse directory
| Left       | Tree-browse parent directory
|            |
| b          | Browse bookmarks
| B          | Bookmark highlighted entry
|            |
| s          | Browse session (dirs visited in session)
| S          | Save highlighted entry in session
|            |
| ~          | Homes browser
| h          | Tree browse from home
| d          | Tree browse from current dir
|            |
| x          | Remove entry (from Session / Bookmarks)
|            |
| /, _       | Enter interactive search

### In interactive search mode:

| Key         | Effect
| ----------- | ---------------------------------------------------------
| Escape      | Exit interactive search mode
| Backspace   | Remove last search string char, or exit mode if empty
| ' '..'~'    | Add to search string

## Interactive search mode

After you've entered IS, just type a few characters. As you type each char,
the display list is re-sorted to place the best matches in the middle and
highlights the middle. IS also shows the current string at the top of the
screen. Placing best matches in the middle halves is done so that the browse
distance to an entry is halved.

## (Display) Substition File

If you want some dirs to be displayed as something other than the path, you
can enter substitution patterns in a file called ~/.dirt_subs. In the subs
file patterns and replacements are listed, one per line separated by one or
more tabs:

    pattern (one or more tabs) replacement

Lines that don't follow this pattern are ignored. If you need the pattern to
include tabs, you can use \\t. Replacements can also include \\1 or \\g<foo>
as the replacements are done using the standard python re package.

## LICENCE

For now, it's GPLv2. If you know what that means, good for you, enjoy.

If not, well, you can...

 * contact me to negotiate a licence properly, or
 * obey whatever all the applicable laws say regardless of license, or
 * figure out what I meant, or
 * be naughty, and take the risk.

UNDER NO CIRCUMSTANCES WILL I ACCEPT ANY LEGAL RESPONSIBILITY FOR DEFECTS.

This software may be used for evil as well as for good. (none of my business.)

Copyright (C) 2009-2010
Anders Eurenius <aes@nerdshack.com>
