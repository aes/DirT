#!/usr/bin/env python
# {{{ head comment
"""
dirt is an interactive curses user interface for changing directory in shells.

It's nice, but there are a lot things that need to be done.

Put this in your .bashrc :

function pcmd()
{
  DIRT=$( echo ${DIRT}:${PWD} |\
          tr : "\n" |\
          sed "s@^${HOME}@\~@" |\
          sort -u |\
           tr "\n" : )
}
export DIRT=""
PROMPT_COMMAND=pcmd
alias d='eval $(dirt 2>&1 1>/dev/tty)'
"""
# }}}

import sys,os,curses as C,os.path
import time

from os import listdir, environ as Env, getcwd as cwd
from os.path import isdir, normpath, expanduser, join as J

class BookmarkFile(object): # {{{
    """Abstraction for bookmark file.

    Remember to make sure objects are explicitly destructed.
    """
    def __init__(self):
        self.l = sorted([ l for l in file(expanduser('~/.dirt_bm')) ])
        self.c = False
    def __del__(self):
        """Save if changed."""
        self.save()
    def save(self):
        if not self.c: return
        f = file(expanduser('~/.dirt_bm'), 'w')
        f.write("\n".join(self.l))
        f.close()
    def append(self, d):
        d = twiddle(d)
        if d not in self.l: self.c, self.l = True, sorted(self.l+[d])
    def remove(self, d):
        d = twiddle(d)
        if d in self.l: self.c, self.l = True, [x for x in self.l if x != d]
    def __contains__(self, d): return twiddle(d) in self.l
    def __iter__(self):        return self.l.__iter__()
    # }}}

# {{{ conveniences
class sym: pass


def read_homes():
    f = file('/etc/passwd')
    l = [ x.split(':') for x in f ]
    f.close()
    return dict([ (x[0],x[5]) for x in l
                  if 999 < int(x[2]) < 1999 or int(x[2]) == 0])

DIRT=sorted([ x for x in Env.get('DIRT','~/').split(':') if x ])
OLDD=DIRT[:]
HOME=Env.get('HOME')
HOMES=read_homes()
BOOK=BookmarkFile()

def has_dir(p):
    try:    l = listdir(p)
    except: return False
    for n in [ x for x in l if x[0] != '.' ]:
        if isdir(p+'/'+n):
            return True

def twiddle(p, plus=False, H=HOME):
    p = untwid(p)
    if plus and has_dir(p):    p = p+' +'
    if p and p.find(H) == 0:   p = '~'+p[len(H):]
    else:
        for u,d in HOMES.items():
            if p.find(d) == 0: p = J('~'+u, p[len(d):])
    if p:                      p = normpath(p)
    return p or './'

def untwid(p=None):
    return normpath(expanduser((p or cwd()).replace(' +','')))
# }}}

class Menu(object): # {{{
    QUIT = sym()
    step = 10
    cc   = [ C.A_NORMAL, C.A_REVERSE ]
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
        self.w, self.l, self.s, self.x, self._z = w, l, s, extra, None
    def _repad(self):
        _z = (len(self.l)+1, max([len(x)+1 for x in self.l]))
        if self._z != _z:
            self._z = _z
            self._p = C.newpad(*self._z)
        return self._p
    def draw(self):
        p = self._repad()
        w, l, s, z, cc = self.w, self.l, self.s, self._z, self.cc
        y, x = w.getmaxyx()
        if y < 2 or x < 4: raise RuntimeError
        #
        w.clear()
        for i in range(len(l)): p.addstr(i, 0, l[i], cc[i==s])
        #
        #destwin[, sminrow, smincol, dminrow, dmincol, dmaxrow, dmaxcol ]
        q = max(s - y/2, 0)
        #raise RuntimeError, (z, q,0, 1,1, min(y, z[0]-1-q), min(x, z[1]-1))
        p.overlay(w, q,0, 1,1, min(y-1, z[0]-1-q), min(x-1, z[1]-1))
        #
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

class DirtMenu(Menu): # {{{
    _desc = lambda o: o.l[o.s][-1]=='+' and TreeMenu(o.w, o.l[o.s])
    _ascd = lambda o: TreeMenu(o.w, o.l[o.s]+'/../../', o.x['here'])
    _tree = lambda o: TreeMenu(o.w)
    def _book(o):
        p = twiddle(o.l[o.s])
        if p not in BOOK: BOOK.append(p)
    def _save(o):
        p = twiddle(o.l[o.s])
        if p not in DIRT: DIRT.append(p)
    m = dict(Menu.m.items() + {
            C.KEY_RIGHT: _desc,
            C.KEY_LEFT:  _ascd,
            ord('B'):    _book,
            ord('S'):    _save,
            ord('d'):    _tree,
            ord('h'):    lambda o: TreeMenu(o.w, '~'),
            ord('b'):    lambda o: BookmarkMenu(o.w),
            ord('~'):    lambda o: HomeMenu(o.w, o.x['here']),
            }.items())
    # }}}

class TreeMenu(DirtMenu): # {{{
    def _dots(o):
        o.dots = not o.dots
        o.l = o.mklist(o.x['here'])
    m = dict(DirtMenu.m.items() + {
            ord('e'):    lambda o: EnvMenu(o.w),
            ord('.'):    _dots,
            }.items())
    def mklist(self, p):
        p = untwid(p)
        l = sorted([ twiddle(J(p,x), True)
                     for x in listdir(p)
                     if isdir(J(p,x)) and (self.dots or x[0] != '.') ])
        return l or (untwid(p) != '/' and self.mklist(p+'/../')) or ['~']
    def __init__(self, w, p=None, h=None):
        self.dots = False
        h = twiddle(h or cwd(), True)
        p = untwid(p or cwd())
        l = self.mklist(p)
        s = (h in l and l.index(h) or len(l)/2)
        super(TreeMenu, self).__init__(w, l, s, {'here': twiddle(p)})
    # }}}

class EnvMenu(DirtMenu): # {{{
    _ascd = lambda o: TreeMenu(o.w, o.l[o.s]+'/../', o.x['here'])
    def _del(o):
        DIRT.remove(twiddle(o.l[o.s]))
        Menu._del(o)
    m = dict(DirtMenu.m.items() + {
            C.KEY_LEFT:  _ascd,
            ord('q'):    Menu._done,
            ord('x'):    _del,
            }.items())
    def __init__(self, w, h=None):
        h = twiddle(cwd(), True)
        l = sorted([ twiddle(x, True) for x in DIRT ])
        s = (h in l and l.index(h) or len(l)/2)
        super(EnvMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class HomeMenu(DirtMenu): # {{{
    def __init__(self, w, h=None):
        h = twiddle(cwd(), True)
        l = sorted([ '~'+x for x in HOMES.keys() ])
        s = (h in l and l.index(h) or len(l)/2)
        super(HomeMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class BookmarkMenu(DirtMenu): # {{{
    def _del(o):
        BOOK.remove(twiddle(o.l[o.s]))
        Menu._del(o)
    def __init__(self, w, h=None):
        h = twiddle(cwd(), True)
        l = sorted([ twiddle(x, True) for x in BOOK ])
        s = (h in l and l.index(h) or len(l)/2)
        super(BookmarkMenu, self).__init__(w, l, s, {'here': h})
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
    if OLDD != DIRT:     print >>sys.stderr, 'DIRT=' + ':'.join(DIRT), ';',
    if p and p != cwd(): print >>sys.stderr, 'cd ' + p, ';'
    del BOOK
    # }}}
