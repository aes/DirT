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

import sys,os,curses as C,os.path
import time

from os import listdir, environ as Env, getcwd as cwd
from os.path import isdir, normpath, expanduser, join as J

# {{{ conveniences
class sym: pass

DIRT=sorted([ x for x in Env.get('DIRT','~/').split('\\n') if x ])
OLDD=DIRT[:]
HOME=Env.get('HOME')

def has_dir(p):
    for n in [ x for x in listdir(p) if x[0] != '.' ]:
        if isdir(p+'/'+n):
            return True

def twiddle(p, plus=False, H=HOME):
    p = untwid(p)
    if plus and has_dir(p):  p = p+' +'
    if p and p.find(H) == 0: p = '~'+p[len(H):]
    if p:                    p = normpath(p)
    return p or './'

def untwid(p=None):
    return normpath(expanduser((p or cwd()).replace(' +','')))
# }}}

class Menu(object): # {{{
    QUIT = sym()
    step = 10
    def _prev(o):     o.s = max(           0, o.s - 1)
    def _next(o):     o.s = min(len(o.l) - 1, o.s + 1)
    def _pgup(o):     o.s = max(           0, o.s - o.step)
    def _pgdn(o):     o.s = min(len(o.l) - 1, o.s + o.step)
    def _first(o):    o.s = 0
    def _last(o):     o.s = len(o.l) - 1
    def _del(o):      o.l, o.s = o.l[:o.s]+o.l[o.s+1:], min(len(o.l) - 2, o.s)
    def _done(o, *a): raise StopIteration, a
    m = { C.KEY_UP:     _prev,
          C.KEY_DOWN:   _next,
          C.KEY_PPAGE:  _pgup,
          C.KEY_NPAGE:  _pgdn,
          C.KEY_HOME:   _first,
          C.KEY_END:    _last,
          ord("\n"):    lambda o: o.l[o.s],
          ord("\r"):    lambda o: o.l[o.s],
          ord('q'):     _done,
          27:           _done,
    }

    def __init__(self, w, l, s=0, extra={}):
        self.w, self.l, self.s, self.x = w, l, s, extra
    def draw(self):
        w, l, s = self.w, self.l, self.s
        w.clear()
        for i in range(len(l)):
            w.addstr(1+i, 1, l[i], [C.A_NORMAL, C.A_REVERSE][i==s])
        w.refresh()
    def run(self):
        while True:
            self.draw()
            try:                      c = self.w.getch()
            except KeyboardInterrupt: c = 27
            f = self.m.get(c)
            if callable(f):
                c = f(self)
                if c: return c != Menu.QUIT and c or None
    # }}}

_desc = lambda o: o.l[o.s][-1]=='+' and TreeMenu(o.w, o.l[o.s])
_ascd = lambda o: TreeMenu(o.w, o.l[o.s]+'/../../', o.x['here'])
_tree = lambda o: TreeMenu(o.w)

class TreeMenu(Menu): # {{{
    def _dots(o):
        o.dots = not o.dots
        o.l = o.mklist(o.x['here'])
    def _save(o):
        p = twiddle(o.l[o.s])
        if p not in DIRT: DIRT.append(p)
    m = dict(Menu.m.items() + {
            C.KEY_RIGHT: _desc,
            C.KEY_LEFT:  _ascd,
            ord('s'):    _save,
            ord('d'):    _tree,
            ord('e'):    lambda o: EnvMenu(o.w),
            ord('h'):    lambda o: TreeMenu(o.w, '~'),
            ord('.'):    _dots,
            }.items())
    def mklist(self, p):
        l = sorted([ twiddle(J(p,x), True)
                     for x in listdir(untwid(p))
                     if isdir(J(p,x)) and (self.dots or x[0] != '.') ])
        return l or self.mklist(p+'/../')
    def __init__(self, w, p=None, h=None):
        self.dots = False
        h = twiddle(h or cwd(), True)
        p = untwid(p or cwd())
        l = self.mklist(p)
        s = (h in l and l.index(h) or len(l)/2)
        super(TreeMenu, self).__init__(w, l, s, {'here': twiddle(p)})
    # }}}


class EnvMenu(Menu): # {{{
    def _del(o):
        DIRT.remove(twiddle(o.l[o.s]))
        Menu._del(o)
    m = dict(Menu.m.items() + {
            C.KEY_RIGHT: _desc,
            C.KEY_LEFT:  _ascd,
            ord('d'):    _tree,
            ord('q'):    Menu._done,
            ord('x'):    _del,
            }.items())
    def __init__(self, w):
        h = twiddle(cwd(), True)
        l = sorted([ twiddle(x, True) for x in DIRT ])
        s = (h in l and l.index(h) or len(l)/2)
        super(EnvMenu, self).__init__(w, l, s, {'here': h})
    # }}}

def wrap(f): # {{{
    try:
        import locale
        locale.setlocale(locale.LC_ALL, '')
        code = locale.getpreferredencoding()

        stdscr = C.initscr(); C.noecho(); C.cbreak()
        stdscr.keypad(1)
        C.curs_set(0)

        return f(stdscr)

        C.curs_set(1);
        stdscr.refresh()
    except StopIteration:
        return None
    finally:
        C.nocbreak(); stdscr.keypad(0); C.echo(); C.endwin()
    # }}}

if __name__ == '__main__': # {{{
    def run_menus(s):
        m = EnvMenu(s)
        while isinstance(m, Menu): m = m.run()
        return m.replace(' +','')
    p = untwid(wrap(run_menus))
    if OLDD != DIRT:     print >>sys.stderr, 'DIRT=' + ':'.join(DIRT)
    if p and p != cwd(): print >>sys.stderr, 'cd ' + p
    # }}}
