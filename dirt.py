#!/usr/bin/env python
# {{{ head comment
"""
dirt is an interactive curses user interface for changing directory in shells.

It's nice, but there are a lot things that need to be done.

Put the contents of dirt.sh in your .bashrc, or just source it.
"""
# }}}

import sys,os,curses as C,os.path, re, pwd

from os import listdir, environ as Env, getcwd as cwd
from os.path import isdir, normpath, expanduser, join as J

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
    cfg_re = re.compile('^([^\t]*)\t+(.*)$')
    def _comp(cls, p):
        try:    return re.compile(p)
        except: return None
    _comp = classmethod(_comp)
    #
    def __init__(self):
        try:    s = [ x.strip() for x in file(expanduser('~/.dirt_subs')) ]
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

class Homes(object): # {{{
    _userhome  = Env.get('HOME')
    _homecache = None
    _homesdict = {}
    def homes(cls):
        if not cls._homesdict:
            s = [x.strip() for x in file('/etc/shells') if x and x[0]=='/']
            h = dict([(x[0],x[5]) for x in pwd.getpwall() if x[6] in s])
            cls._homesdict = h
        return cls._homesdict
    homes = classmethod(homes)
    def homedirs(cls):
        if not cls._homecache:
            cls._homecache = [ cls.fetch('~'+x) for x in cls.homes() ]
        return cls._homecache
    homedirs = classmethod(homedirs)
    def normhome(cls, p=None):
        if not p: return p
        if p.find(cls._userhome) == 0:  return '~'+p[len(cls._userhome):]
        for u,d in cls.homes().items():
            if p.find(d) == 0:          return J('~'+u, p[len(d):])
        return p
    # }}}


class DirName(Homes): # {{{
    subs = Subber()
    cache = {}
    def norm(cls, p):
        return normpath(expanduser(p or cwd()))
    norm = classmethod(norm)
    def fetch(cls, p):
        if isinstance(p, DirName): return p
        if p and p[:3] == '../': p = cls.norm(J(cwd(), p))
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
        self.d = self.subs(p) + ['',' +'][self.c]
        return p or './'
    #
    def parent(self):         return normpath(J, '..')
    def is_root(self):        return self.p == '/'
    def __bool__(self):       return bool(self.d)
    def __cmp__(self, other):
        if isinstance(other,    DirName): return cmp(self.p, other)
        if isinstance(other, basestring): return cmp(self.p, other)
        raise TypeError, type(other)
    def __len__(self):        return len(self.d)
    def __add__(self, other):
        if isinstance(other, DirName): return J(self.p, other.p)
        else:                          return J(self.p, u8(other))
    def __str__(self):        return self.d
    def __unicode__(self):    return self.d
    def __repr__(self):       return self.p
    # }}}

class AbstractList(object): # {{{
    def __init__(self, *x):
        self.c = False
        self.load(*x)
        self.l.sort()
    def append(self, d):
        d = DirName.fetch(d)
        if d not in self.l: self.c, self.l = True, self.l+[d]
        self.l.sort()
    def remove(self, d):
        d = DirName.fetch(d)
        if d in self.l: self.c, self.l = True, [x for x in self.l if x != d]
    def __contains__(self, d): return DirName.fetch(d) in self.l
    def __iter__(self):        return self.l.__iter__()
    # }}}

class BookmarkFile(AbstractList): # {{{
    """Abstraction for bookmark file.

    Remember to make sure objects are explicitly destructed.
    """
    def load(self, fn='~/.dirt_bm'):
        try:    self.l = ([ DirName.fetch(l.strip())
                           for l in file(expanduser(fn)) ]
                          or [DirName.fetch('~')])
        except: self.l = [DirName.fetch('~')]
        self.fn = expanduser(fn)
    def save(self):
        if not self.c: return
        try:
            f = file(self.fn, 'w')
            f.write("".join([ d.s+"\n" for d in self.l ]))
            f.close()
        except: pass
    # }}}

class EnvList(AbstractList): # {{{
    def load(self):
        df = DirName.fetch
        self.l = [ df(x) for x in Env.get('DIRT','~/').split(':') if x ]
    def save(self):
        if self.c: print >>E, "DIRT="+":".join(map(lambda x: x.p, self.l)),";",
    # }}}

# {{{ conveniences
class sym: pass

DIRT=EnvList()
BOOK=BookmarkFile()
SHAR=BookmarkFile(Env.get('DIRT_SHARED','/dev/null'))
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
    def _srch(o):     return InteractiveMenu(o)
    m = { C.KEY_UP:     _prev,
          C.KEY_DOWN:   _next,
          C.KEY_PPAGE:  _pgup,
          C.KEY_NPAGE:  _pgdn,
          C.KEY_HOME:   _first,
          C.KEY_END:    _last,
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
            self._p = C.newpad(*self._z)
        self._p.clear()
        return self._p
    def draw(self):
        p = self._repad()
        w, l, s, z, cc = self.w, self.l, self.s, self._z, self.cc
        y, x = w.getmaxyx()
        if y < 2 or x < 4: raise RuntimeError
        #
        w.clear()
        w.addstr(0, 1, self.t, C.A_BOLD)
        #
        for i in range(len(l)): p.addstr(i, 0, u8(l[i].d), cc[i==s])
        #
        #destwin[, sminrow, smincol, dminrow, dmincol, dmaxrow, dmaxcol ]
        q = max(s - y/2, 0)
        #raise RuntimeError, (z, q,0, 1,1, min(y, z[0]-1-q), min(x, z[1]-1))
        p.overlay(w, q,0, 1,1, min(y-1, z[0]-1-q), min(x-1, z[1]-1))
        #
        w.refresh()
    def input(self, c): return self.m.get(c)
    def run(self):
        while True:
            self.draw()
            try:                      c = self.w.getch()
            except KeyboardInterrupt: c = 27
            f = self.input(c)
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
            C.KEY_BACKSPACE: _bs,
            C.KEY_LEFT:      lambda o: o.ctx,
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
    def input(self, c):
        if not (31 < c < 127): return self.m.get(c) or self.ctx.input(c)
        self.q += chr(c)
        self.redo()
    # }}}

class DirtMenu(Menu): # {{{
    _desc = lambda o: o.l[o.s].c and TreeMenu(o.w, o.l[o.s])
    _ascd = lambda o: TreeMenu(o.w, o.l[o.s].s+'/../../', o.x['here'])
    def _subs(o):
        DirName.subs.active = not DirName.subs.active
    def _book(o):
        p = DirName.fetch(o.l[o.s]).s
        if p not in BOOK: BOOK.append(p)
    def _save(o):
        p = DirName.fetch(o.l[o.s]).s
        if p not in DIRT: DIRT.append(p)
    m = dict(Menu.m.items() + {
            C.KEY_RIGHT: _desc,
            C.KEY_LEFT:  _ascd,
            C.KEY_DC:    lambda o: o._del(),
            ord('B'):    _book,
            ord('S'):    _save,
            ord('b'):    lambda o: BookmarkMenu(o.w),
            ord('s'):    lambda o: SessionMenu(o.w),
            ord('d'):    lambda o: TreeMenu(o.w, cwd(), o.x['here']),
            ord('h'):    lambda o: TreeMenu(o.w, '~', o.x['here']),
            ord('q'):    Menu._done,
            ord('r'):    _subs,
            ord('x'):    lambda o: o._del(),
            ord('z'):    lambda o: SharedMenu(o.w),
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
        l = [ DirName.fetch(J(p.p, x))
              for x in listdir(p.p)
              if isdir(J(p.p, x)) and (self.dots or x[0] != '.') ]
        if not l:
            if not p.is_root(): return self.mklist(J(p.p, '../'))
            else:               return [DirName.fetch('/')]
        else:
            l.sort()
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
    it = DIRT
    def _del(o):
        DIRT.remove(o.l[o.s].s)
        Menu._del(o)
    def __init__(self, w, h=None):
        h = DirName.fetch(h or cwd())
        l = [ DirName.fetch(x) for x in self.it ]
        s = (h in l and l.index(h) or len(l)/2)
        l.sort()
        super(SessionMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class HomeMenu(DirtMenu): # {{{
    def __init__(self, w, h=None):
        h = DirName.fetch(h)
        l = DirName.homedirs()
        s = (h in l and l.index(h) or len(l)/2)
        super(HomeMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class BookmarkMenu(DirtMenu): # {{{
    it = BOOK
    def _del(o):
        o.it.remove(o.l[o.s])
        Menu._del(o)
    def __init__(self, w, h=None):
        h = DirName.fetch(h or cwd())
        l = [ DirName.fetch(x) for x in self.it ]
        s = (h in l and l.index(h) or len(l)/2)
        l.sort()
        super(BookmarkMenu, self).__init__(w, l, s, {'here': h})
    # }}}

class SharedMenu(BookmarkMenu): # {{{
    it = SHAR
    # }}}

def wrap(f): # {{{
    try:
        import locale
        locale.setlocale(locale.LC_ALL, '')
        code = locale.getpreferredencoding()

        stdscr = C.initscr(); C.noecho(); C.cbreak()
        stdscr.keypad(1)
        C.curs_set(0)

        ret = f(stdscr)

    except Exception, e:
        ret = None
        C.curs_set(1); C.nocbreak(); stdscr.keypad(0); C.echo(); C.endwin()
        raise

    C.curs_set(1); C.nocbreak(); stdscr.keypad(0); C.echo(); C.endwin()
    return ret
    # }}}

if __name__ == '__main__': # {{{
    x = len(sys.argv) > 1 and sys.argv[1] or None
    if   x == '-b': Begin, x = BookmarkMenu, None
    elif x == '-t': Begin, x = TreeMenu,     None
    elif x == '-s': Begin, x = SessionMenu,  None
    elif x == '-z': Begin, x = SharedMenu,   None
    elif x == '-h': Begin, x = HomeMenu,     None
    elif x:         Begin, x = TreeMenu,     isdir(x) and x or None
    else:           Begin, x = SessionMenu,  None
    def run_menus(w):
        m = Begin(w, x)
        while isinstance(m, Menu): m = m.run()
        return repr(m.s)[1:-1]
    p = wrap(run_menus)
    E = sys.stderr
    BOOK.save()
    SHAR.save()
    DIRT.save()
    if p and p != cwd(): print >>E, 'cd ' + str(shellsafe(p)),
    # }}}
