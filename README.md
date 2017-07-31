# Frotzbot
Telegram bot to play text adventure games. Inspired by [z5bot](https://github.com/sneaksnake/z5bot).
I'll try to keep [an instance](http://telegram.me/test_frotzbot) running.

## Installation
Runs on python 3.x.x (tested with 3.4.5), requires packages:
- python-telegram-bot
- splitstream

all of which can be installed via pip

You also need a bunch of interpreters compiled with [remglk](https://github.com/erkyrath/remglk).
Compilation instructions for each differ, though it usually involves placing remglk sources inside 
interpreter's sources directory, then editing Makefile to tell compiler where to look for glk implementation.

Frotzbot supports any interpreter, as long as it accepts valid remglk input and generates valid remglk response.


After that, you need to rename config.json.example to config.json and edit it according to your needs.

...And, you're set! All that's left is to run frotzbot.py

## Known issues
- To quit a game, you must issue /quit (or /start, if you want to start a new game) command because bot cannot determine when interpreter process died
- Bot reacts to every incoming message, which is fine for single player, but might be troublesome when playing in group. To get it to shut up, issue a /quit command.
