#!/usr/bin/env python
# {{{ head comment
"""
dirt is an interactive curses user interface for changing directory in shells.

It's nice, but there are a lot things that need to be done.

Put the contents of dirt.sh in your .bashrc, or just source it.
"""
# }}}

import sys
import os
import curses
import os.path
import re
import pwd

from os import listdir, environ, getcwd
from os.path import isdir, normpath, expanduser, join

# {{{ utils
def u8(s):
    if not isinstance(s, unicode): s = unicode(s, 'utf-8', 'replace')
    return s.encode('utf-8')

def shellsafe(s, z=re.compile('[^/0-9A-Za-z,.~=+-]')):
    if isinstance(s, DirName): s = str(s)
    if isinstance(s, basestring): return z.sub(lambda mo: '\\'+mo.group(0), s)
    else:                         return [shellsafe(x) for x in s]

def levenshtein(a,b): # {{{
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m: a,b, n,m = b,a, m,n
    cur = range(n+1)
    for i in range(1,m+1):
        prev, cur = cur, [i]+[0]*n
        for j in range(1,n+1):
            add,rem,chg = prev[j]+1, cur[j-1]+1, prev[j-1]+int(a[j-1]!=b[i-1])
            cur[j] = min(add, rem, chg)
    return cur[n]
    # }}}

def dist(a, b):
    a, b = a.lower(), b.lower()
    d = levenshtein(a, b) - len(b)
    if a in b:  d -= len(a) + b.find(a) / len(b)
    return d
#}}}

class Subber(object): # {{{
    cfg_re = re.compile('^([^\\t]+)\\t+(.*)$')
    def _comp(cls, p):
        try:    return re.compile(p)
        except: return None
    _comp = classmethod(_comp)
    #
    def __init__(self):
        try:    s = [ x for x in open(expanduser('~/.dirt_subs')) ]
        except: s = []
        s = [ self.cfg_re.match(x) for x in s ]
        s = [ (self._comp(x.group(1)), x.group(2)) for x in s if x ]
        self.subs = [ x for x in s if x[0] ]
        self.active = True
    def add(self, pat, repl):
        pat = self._comp(pat)
        if pat: self.subs.append( (pat,repl) )
    def __call__(self, q):
        for pat,repl in self.subs: q = pat.sub(repl, q)
        return q
    # }}}

class BaseList(object): # {{{
    def append(self, d):
        d = DirName.fetch(d)
        if d not in self.l: self.c, self.l[:] = True, self.l+[d]
        self.l.sort()
    def remove(self, d):
        d = DirName.fetch(d)
        if d in self.l: self.c, self.l[:] = True, [x for x in self.l if x != d]
    def __contains__(self, d):  return DirName.fetch(d) in self.l
    def __iter__(self):         return [ x for x in self.l if x ].__iter__()
    def __len__(self):          return len(self.l)
    def __getitem__(self, k):   return self.l[k]
    def index(self, x):         return self.l.index(x)
    # }}}

class AbstractList(BaseList): # {{{
    _ll = {}
    _w = {}
    def l():
        def _get(self):
            if self not in self._ll: self._ll[self] = self.load()
            self._w[self] = getattr(self, 'fn', 'x')
            return self._ll[self]
        return property(_get)
    l = l()
    def __init__(self, *al, **kw):
        self.c = False
        self.al = al
	self.kw = kw
    # }}}

class Homes(AbstractList): # {{{
    _userhome  = normpath(expanduser('~'))
    _homecache = None
    _homesdict = {}
    def homes(cls):
        if not cls._homesdict:
            try:
                s = [x.strip() for x in open('/etc/shells') if x and x[0]=='/']
            except:
                s = []
            h = dict([(x[0],x[5]) for x in pwd.getpwall() if x[6] in s])
            cls._homesdict = h
        return cls._homesdict
    homes = classmethod(homes)
    def homedirs(cls):
        if not cls._homecache:
            cls._homecache = [ DirName.fetch('~'+x) for x in cls.homes() ]
        return cls._homecache
    homedirs = classmethod(homedirs)
    def normhome(cls, p=None):
        if not p: return p
        p = normpath(expanduser(p))
        if p.find(cls._userhome) == 0:  return '~'+p[len(cls._userhome):]
        for u,d in cls.homes().items():
            if p.find(d) == 0:          return '~'+u+p[len(d):]
        return p
    def load(self):            return self.homedirs()
    def save(self, *al, **kw): pass
    append = save
    remove = save
    # }}}

class DirName(Homes): # {{{
    subs = Subber()
    cache = {}
    def norm(cls, p):
        return normpath(expanduser(p or getcwd()))
    norm = classmethod(norm)
    def fetch(cls, p):
        if isinstance(p, DirName): return p
        if p and p[:3] == '../': p = cls.norm(join(getcwd(), p))
        else:                    p = cls.norm(p)
        x = cls.cache.get(p)
        if x: return x
        x = DirName(p)
        cls.cache[x.p] = x
        return x
    fetch = classmethod(fetch)
    def __init__(self, p=None):
        self.p = self.norm(p)
        self.c = self._has_dir()
        self._examine()
    def _has_dir(self):
        try:    l = listdir(self.p)
        except: return False
        for n in [ x for x in l if x[0] != '.' ]:
            if isdir(u8(self.p+'/'+n)):
                return True
        return False
    def _examine(self):
        p = self.normhome(self.p)
        self.s = p
        self.d = self.subs(p)
        self.d = self.d and self.d + ['',' +'][self.c] # leave empty if empty
        return p or './'
    def parent(self):         return normpath(join(self.p, '..'))
    def is_root(self):        return self.p == '/'
    def __bool__(self):       return bool(self.d)
    def __cmp__(self, other):
        if isinstance(other,    DirName): return cmp(self.p, other)
        if isinstance(other, basestring): return cmp(self.p, other)
        raise TypeError(type(other))
    def __len__(self):        return len(self.d)
    def __add__(self, other):
        if isinstance(other, DirName): return join(self.p, other.p)
        else:                          return join(self.p, u8(other))
    def __str__(self):        return self.d
    def __unicode__(self):    return self.d
    def __repr__(self):       return self.p
    def list(self, dots = False):
        l = [ DirName.fetch(join(self.p, x))
              for x in listdir(self.p)
              if isdir(join(self.p, x)) and (dots or x[0] != '.') ]
        w = BaseList()
        w.l = sorted([ x for x in l if x ])
        return w
    # }}}

class BookmarkFile(AbstractList): # {{{
    """Abstraction for bookmark file.

    Remember to make sure objects are explicitly destructed.
    """
    def load(self):
        fn= self.kw.get('fn', '~/.dirt_bm')
        self.fn = expanduser(fn)
        try:    return ([ DirName.fetch(l.strip())
                          for l in open(self.fn) ]
                        or [DirName.fetch('~')])
        except: return [DirName.fetch('~')]
    def save(self):
        if not self.c: return
        try:
            f = open(self.fn, 'w')
            f.write("".join([ d.s+"\n" for d in self.l ]))
            f.close()
        except: pass
    # }}}

class EnvList(AbstractList): # {{{
    def load(self):
        df = DirName.fetch
        return [ df(x) for x in environ.get('DIRT','~/').split(':') if x ]
    def save(self):
        if self.c: print "DIRT="+":".join(map(lambda x: x.p, self.l)),";",
    # }}}

# {{{ conveniences
class sym: pass

HOME=Homes()
DIRT=EnvList()
BOOK=BookmarkFile()
SHAR=BookmarkFile(fn=environ.get('DIRT_SHARED',
                                 '/tmp/' + environ.get('USER') + '.dirt'))
# }}}

class Menu(object): # {{{
    QUIT = sym()
    step = 10
    cc   = [ curses.A_NORMAL, curses.A_REVERSE ]
    def _prev(o):     o.s = max(           0, o.s - 1)
    def _next(o):     o.s = min(len(o.l) - 1, o.s + 1)
    def _pgup(o):     o.s = max(           0, o.s - o.step)
    def _pgdn(o):     o.s = min(len(o.l) - 1, o.s + o.step)
    def _first(o):    o.s = 0
    def _last(o):     o.s = len(o.l) - 1
    def _del(o):      o.l, o.s = o.l[:o.s]+o.l[o.s+1:], min(len(o.l) - 2, o.s)
    def _done(o, *a): raise StopIteration(a)
    def _srch(o):     return InteractiveMenu(o)
    m = { curses.KEY_UP:     _prev,
          curses.KEY_DOWN:   _next,
          curses.KEY_PPAGE:  _pgup,
          curses.KEY_NPAGE:  _pgdn,
          curses.KEY_HOME:   _first,
          curses.KEY_END:    _last,
          ord("\n"):    lambda o: o.l[o.s],
          ord("\r"):    lambda o: o.l[o.s],
          ord('/'):     _srch,
          ord('_'):     _srch,
          ord('q'):     _done,
          27:           _done,
    }
    def __init__(self, w, l, s=0, extra={}):
        self.w, self.l, self.s, self.x, self._z = w, l, s, extra, None
        self.t = getattr(self, 't', self.__class__.__name__.replace('Menu',''))
    def _repad(self):
        _z = (len(self.l)+1, max([2]+[len(x)+1 for x in self.l]))
        if self._z != _z:
            self._z = _z
            self._p = curses.newpad(*self._z)
        self._p.clear()
        return self._p
    def draw(self):
        p = self._repad()
        w, l, s, z, cc = self.w, self.l, self.s, self._z, self.cc
        y, x = w.getmaxyx()
        if y < 2 or x < 4: raise RuntimeError
        #
        w.clear()
        w.addstr(0, 1, self.t, curses.A_BOLD)
        #
        for i in range(len(l)): p.addstr(i, 0, u8(l[i].d), cc[i==s])
        #
        #destwin[, sminrow, smincol, dminrow, dmincol, dmaxrow, dmaxcol ]
        q = max(s - y/2, 0)
        #raise RuntimeError, (z, q,0, 1,1, min(y, z[0]-1-q), min(x, z[1]-1))
        p.overlay(w, q,0, 1,1, min(y-1, z[0]-1-q), min(x-1, z[1]-1))
        #
        self.refresh()
    def refresh(self):  return self.w.refresh()
    def mapch(self, c): return self.m.get(c)
    def getch(self):    return self.w.getch()
    def run(self):
        while True:
            self.draw()
            try:                      c = self.getch()
            except KeyboardInterrupt: c = 27
            f = self.mapch(c)
            if callable(f):
                c = f(self)
                if c: return c != Menu.QUIT and c or None
    # }}}

class InteractiveMenu(Menu): # {{{
    def _bs(o):
        if not o.q: return o.ctx
        o.q = o.q[:-1]
        o.redo()
    m = dict(Menu.m.items() + {
            curses.KEY_BACKSPACE: _bs,
            curses.KEY_LEFT:      lambda o: o.ctx,
            27:              lambda o: o.ctx,
        }.items())
    def __init__(self, ctx):
        self.ctx, self.q = ctx, ''
        super(InteractiveMenu, self).__init__(ctx.w, ctx.l[:])
    def redo(self):
        q = self.q
        m = [ (dist(q, y.s), y) for y in self.l ]
        m.sort()
        l = []
        for i, x in enumerate(m):
            if i % 2:  l = [x]+l
            else:      l = l+[x]
        self.t = '/'+self.q+' '
        self.s, self.l = len(l)/2, [ y for x, y in l ]
    def mapch(self, c):
        if not (31 < c < 127): return self.m.get(c) or self.ctx.input(c)
        self.q += chr(c)
        self.redo()
    # }}}

class DirtMenu(Menu): # {{{
    _desc = lambda o: o.l[o.s].c and TreeMenu(o.w, o.l[o.s])
    _ascd = lambda o: TreeMenu(o.w, o.x['here'].parent(), o.x['here'])
    def _subs(o):
        DirName.subs.active = not DirName.subs.active
    def _book(o):
        p = DirName.fetch(o.l[o.s]).s
        if p not in BOOK: BOOK.append(p)
    def _save(o):
        p = DirName.fetch(o.l[o.s]).s
        if p not in DIRT: DIRT.append(p)
    m = dict(Menu.m.items() + {
            curses.KEY_RIGHT: _desc,
            curses.KEY_LEFT:  _ascd,
            curses.KEY_DC:    lambda o: o._del(),
            ord('B'):    _book,
            ord('S'):    _save,
            ord('b'):    lambda o: BookmarkMenu(o.w),
            ord('s'):    lambda o: SessionMenu(o.w),
            ord('d'):    lambda o: TreeMenu(o.w, getcwd(), o.x['here']),
            ord('h'):    lambda o: HomeMenu(o.w, o.x['here']),
            ord('q'):    Menu._done,
            ord('r'):    _subs,
            ord('x'):    lambda o: o._del(),
            ord('z'):    lambda o: SharedMenu(o.w),
            ord('~'):    lambda o: TreeMenu(o.w, '~', o.x['here']),
            }.items())
    # }}}

class TreeMenu(DirtMenu): # {{{
    def _dots(o):
        o.dots = not o.dots
        o.l = DirName.fetch(o.x['here']).list(o.dots)
        o.s = min(o.s, len(o.l)-1)
    m = dict(DirtMenu.m.items() + {
            ord('.'):    _dots,
            }.items())
    def __init__(self, w, p=None, h=None):
        self.dots = False
        h = DirName.fetch(h)
        p = DirName.fetch(p)
        l = p.list(self.dots)
        s = (h in l and l.index(h) or len(l)/2)
        super(TreeMenu, self).__init__(w, l, s, {'here': p})
    # }}}

class ListMenu(DirtMenu): # {{{
    it = DIRT
    def _del(o):
        o.it.remove(o.l[o.s].s)
        Menu._del(o)
    def __init__(self, w, h=None):
        h = DirName.fetch(h or getcwd())
        l = [ DirName.fetch(x) for x in self.it ]
        s = (h in l and l.index(h) or len(l)/2)
        l.sort()
        super(ListMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class SessionMenu(ListMenu): # {{{
    it = DIRT
    # }}}

class HomeMenu(ListMenu): # {{{
    it = HOME
    # }}}

class BookmarkMenu(SessionMenu): # {{{
    it = BOOK
    # }}}

class SharedMenu(SessionMenu): # {{{
    it = SHAR
    # }}}

stdscr = None

class CursesContext:
    def __init__(self):
        pass
    def __enter__(self):
        self.i = os.dup(sys.stdin.fileno())
        self.o = os.dup(sys.stdout.fileno())
        self.r = open('/dev/tty', 'r')
        self.w = open('/dev/tty', 'w')
        os.dup2(self.r.fileno(), 0)
        os.dup2(self.w.fileno(), 1)

        global stdscr
        self.old_stdscr = stdscr
        self.stdscr = stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
        curses.curs_set(0)
        return stdscr
    def __exit__(self, exc_type, exc_value, exc_tb):
        global stdscr
        if stdscr:
            curses.curs_set(1)
            curses.nocbreak()
            stdscr.keypad(0)
            curses.echo()
            curses.endwin()
            stdscr = self.old_stdscr
        if self.i: os.dup2(self.i, 0)
        if self.o: os.dup2(self.o, 1)
        return exc_type in (StopIteration, KeyboardInterrupt,)

def parse_args(argv):
    if   argv[1:2] == ['-b']: return BookmarkMenu, ()
    elif argv[1:2] == ['-t']: return TreeMenu,     ()
    elif argv[1:2] == ['-s']: return SessionMenu,  ()
    elif argv[1:2] == ['-z']: return SharedMenu,   ()
    elif argv[1:2] == ['-h']: return HomeMenu,     ()
    elif argv[1:2]:           return TreeMenu,     (isdir(x),) if x else ()
    else:                     return SessionMenu,  ()

if __name__ == '__main__': # {{{
    M, al = parse_args(sys.argv)
    with CursesContext() as stdscr:
        m = M(stdscr, *al)
        while isinstance(m, Menu):
            try:    m = m.run()
            except: break
        p = repr(m.s)[1:-1]

    for x in (BOOK, SHAR, DIRT):
        x.save()

    if p and expanduser(p) != getcwd():
        print 'cd ' + str(shellsafe(p))
    # }}}
