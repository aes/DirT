#!/usr/bin/env python

"""
dirt is an interactive curses user interface for changing directory in shells.

It's nice, but there are a lot things that need to be done.

Put this in your .bashrc :

function pcmd()
{
  local WD="$(pwd|sed "s@^${HOME}@\~@")"
  echo "$DIRT" | grep "^${WD}$" - >/dev/null || DIRT="${DIRT}\n${WD}"
}
export DIRT=""
PROMPT_COMMAND=pcmd
alias d='eval $(dirt 2>&1 1>/dev/tty)'
"""


import sys,os, curses as C
import time

HOME = None

class Menu:
    def __init__(self, l=[]):
        self.l, self.s = l or ['~/'], 0
    def draw(self, w):
        l, s = self.l, self.s
        for i in range(len(l)):
            w.addstr(2+i, 2, l[i], [C.A_NORMAL, C.A_REVERSE][i==s])
        w.refresh()
    def run(self, w):
        while True:
            self.draw(w)
            c = w.getch()
            if   c == C.KEY_UP:   self.s = max(self.s-1, 0)
            elif c == C.KEY_DOWN: self.s = min(self.s+1, len(self.l)-1)
            elif c in map(ord, '\r\n'):
                return 'DONE', os.path.expanduser(self.l[self.s])

class EnvMenu(Menu):
    def __init__(self):
        l = os.environ.get('DIRT','~/').split('\\n')
        l = [ x for x in l if x ] or [ os.getcwd() ]
        l = [ p.replace(HOME, '~/') for p in sorted(l) ]
        self.l, self.s = l, 0
        p = os.environ.get('PWD','')
        p = p.replace(HOME, '~/')
        p = p.replace('//', '/')
        if p in l: self.s = l.index(p)

def do_menu():
    try:
        import locale
        locale.setlocale(locale.LC_ALL, '')
        code = locale.getpreferredencoding()

        stdscr = C.initscr(); C.noecho(); C.cbreak()
        stdscr.keypad(1)
        C.curs_set(0)

        x = None
        while x != 'DONE': x, l = EnvMenu().run(stdscr)

        C.curs_set(1)
        stdscr.refresh()
    finally:
        C.nocbreak(); stdscr.keypad(0); C.echo(); C.endwin()
    return l


def main():
    global HOME
    HOME = os.environ.get('HOME','')
    x = do_menu()
    print >>sys.stderr, "cd '"+x.replace("'","'\"'\"'")+"'"

main()

