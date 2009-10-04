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

class DirName(object): # {{{
    cache = {}
    def norm(cls, p):
        return normpath(expanduser((p or cwd()).replace(' +','')))
    norm = classmethod(norm)
    def fetch(cls, p):
        if isinstance(p, DirName): return p
        if p and p[:3] == '../': p = cls.norm(cwd()+'/../')
        else:                    p = cls.norm(p)
        x = cls.cache.get(p)
        if x: return x
        x = DirName(p)
        cls.cache[x.p] = x
        return x
    fetch = classmethod(fetch)
    #
    def __init__(self, p=None):
        self.p = normpath(expanduser(p or cwd()))
        self.c = self._has_dir()
        self._examine()
    def _has_dir(self):
        try:    l = listdir(self.p)
        except: return False
        for n in [ x for x in l if x[0] != '.' ]:
            if isdir(self.p+'/'+n):
                return True
        return False
    def _examine(self, H=Env.get('HOME')):
        p = self.p
        if p and p.find(H) == 0:        p = '~'+p[len(H):]
        else:
            for u,d in HOMES.items():
                if p.find(d) == 0:      p = J('~'+u, p[len(d):])
        self.s = p
        self.d = p + ['',' +'][self.c]
        return p or './'
    #
    def __cmp__(self, other):
        if isinstance(other,    DirName): return cmp(self.p, other)
        if isinstance(other, basestring): return cmp(self.p, other)
        raise TypeError, self, other
    def parent(self):         return normpath(J, '..')
    def is_root(self):        return self.p == '/'
    def __len__(self):        return len(self.d)
    def __add__(self, other): return J(self.p, unicode(other))
    def __str__(self):        return self.d
    def __unicode__(self):    return self.p
    # }}}

class BookmarkFile(object): # {{{
    """Abstraction for bookmark file.

    Remember to make sure objects are explicitly destructed.
    """
    def __init__(self):
        try:    self.l = sorted([ DirName.fetch(l)
                                  for l in file(expanduser('~/.dirt_bm')) ])
        except: self.l = []
        self.c = False
    def __del__(self):
        """Save if changed."""
        self.save()
    def save(self):
        if not self.c: return
        try:
            f = file(expanduser('~/.dirt_bm'), 'w')
            f.write("\n".join(self.l))
            f.close()
        except:
            pass
    def append(self, d):
        d = ( DirName.fetch(d) ).s
        if d not in self.l: self.c, self.l = True, sorted(self.l+[d])
    def remove(self, d):
        d = ( DirName.fetch(d) ).s
        if d in self.l: self.c, self.l = True, [x for x in self.l if x != d]
    def __contains__(self, d): return ( DirName.fetch(d) ).s in self.l
    def __iter__(self):        return self.l.__iter__()
    # }}}

# {{{ conveniences
class sym: pass

def read_homes():
    try:
        f = file('/etc/passwd')
        l = [ x.split(':') for x in f ]
        f.close()
    except:
        l = []
    return dict([ (x[0],x[5]) for x in l
                  if 999 < int(x[2]) < 1999 or int(x[2]) == 0])

DIRT=sorted([ x for x in Env.get('DIRT','~/').split(':') if x ])
OLDD=DIRT[:]
HOME=Env.get('HOME')
HOMES=read_homes()
BOOK=BookmarkFile()

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
        n = self.__class__.__name__.replace('Menu','')
        w.clear()
        w.addstr(0, 1, n, C.A_BOLD)
        #
        for i in range(len(l)): p.addstr(i, 0, str(l[i]), cc[i==s])
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
    _desc = lambda o: o.l[o.s].c and TreeMenu(o.w, o.l[o.s])
    _ascd = lambda o: TreeMenu(o.w, o.l[o.s].s+'/../../', o.x['here'])
    _tree = lambda o: TreeMenu(o.w)
    def _book(o):
        p = twiddle(o.l[o.s])
        if p not in BOOK: BOOK.append(p.s)
    def _save(o):
        p = twiddle(o.l[o.s])
        if p not in DIRT: DIRT.append(p.s)
    m = dict(Menu.m.items() + {
            C.KEY_RIGHT: _desc,
            C.KEY_LEFT:  _ascd,
            ord('B'):    _book,
            ord('S'):    _save,
            ord('b'):    lambda o: BookmarkMenu(o.w),
            ord('s'):    lambda o: SessionMenu(o.w),
            ord('d'):    _tree,
            ord('h'):    lambda o: TreeMenu(o.w, '~'),
            ord('q'):    Menu._done,
            ord('~'):    lambda o: HomeMenu(o.w, o.x['here']),
            }.items())
    # }}}

class TreeMenu(DirtMenu): # {{{
    def _dots(o):
        o.dots = not o.dots
        o.l = o.mklist(o.x['here'])
        o.s = min(o.s, len(o.l)-1)
    m = dict(DirtMenu.m.items() + {
            ord('.'):    _dots,
            }.items())
    def mklist(self, p):
        p = DirName.fetch(p)
        l = sorted([ DirName.fetch(p+x)
                     for x in listdir(p.p)
                     if isdir(p+x) and (self.dots or x[0] != '.') ])
        if not l:
            if not p.is_root(): return self.mklist(p+'/../')
            else:               return [DirName.fetch('/')]
        else:
            return l
    def __init__(self, w, p=None, h=None):
        self.dots = False
        h = DirName.fetch(h)
        p = DirName.fetch(p)
        l = self.mklist(p)
        s = (h in l and l.index(h) or len(l)/2)
        super(TreeMenu, self).__init__(w, l, s, {'here': p})
    # }}}

class SessionMenu(DirtMenu): # {{{
    _ascd = lambda o: TreeMenu(o.w, o.l[o.s].s+'/../', o.x['here'])
    def _del(o):
        DIRT.remove(o.l[o.s].s)
        Menu._del(o)
    m = dict(DirtMenu.m.items() + {
            C.KEY_LEFT:  _ascd,
            ord('x'):    _del,
            }.items())
    def __init__(self, w, h=None):
        h = DirName.fetch(h)
        l = sorted([ DirName.fetch(x) for x in DIRT ])
        s = (h in l and l.index(h) or len(l)/2)
        super(SessionMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class HomeMenu(DirtMenu): # {{{
    def __init__(self, w, h=None):
        h = DirName.fetch(h)
        l = sorted([ DirName('~'+x) for x in HOMES.keys() ])
        s = (h in l and l.index(h) or len(l)/2)
        super(HomeMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class BookmarkMenu(DirtMenu): # {{{
    def _del(o):
        BOOK.remove(o.l[o.s].s)
        Menu._del(o)
    def __init__(self, w, h=None):
        h = DirName.fetch(h or cwd())
        l = sorted([ DirName.fetch(x) for x in BOOK ])
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
        m = SessionMenu(s)
        while isinstance(m, Menu): m = m.run()
        return m.s.replace(' +','')
    p = wrap(run_menus)
    if OLDD != DIRT:     print >>sys.stderr, 'DIRT=' + ':'.join(DIRT), ';',
    if p and p != cwd(): print >>sys.stderr, 'cd ' + p, ';'
    del BOOK
    # }}}
