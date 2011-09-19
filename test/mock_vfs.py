import exceptions
import os.path
import cStringIO

class MockVfs(object):
    std_cwd = '/home/apu'
    std_tree = {
        'bin': {},
        'dev': {'block': {}, 'char': {}, 'fd': {}, 'net': {}},
        'etc': {'cron.d': {}, 'init.d': {}, 'pam.d': {}},
        'home': {
            'apu': {'Documents': {'Essays': {}, 'Notes': {}},
                     'Downloads': {}, 'Music': {}, 'Video': {}},
            'bo': {'src': {'dirt': {}}, '.config': {'thing': {}}},
        },
        'lib': {}, 'mnt': {}, 'opt': {}, 'root': {},
        'usr': {
            'bin': {}, 'games': {}, 'lib': {'X11': {}},
            'sbin': {}, 'share': {},
        },
        'var': {'cache': {}, 'games': {}, 'lib': {},
                'local': {}, 'log': {}, 'www': {}, },
        'tmp': {}
    }
    std_homes = {'apu': '/home/apu', 'bo': '/home/bo', 'root': '/root'}
    std_files = {
        '/home/apu/.dirt_bm':   "/home/apu/Documents/Notes\n/usr/share\n",
        '/home/apu/.dirt_subs': "/home/apu/Music\t~-< M u s i c >-~\n",
        '/tmp/apu.dirt':        "/usr/share\n/usr/lib/X11\n/home/apu/Music\n"
    }
    std_env = {
        'DIRT': ':/etc/cron.d:/var/games:',
        'USER': 'apu'
    }

    __slots__ = ('cwd', 'environ', 'tree', 'homes', 'files', 'stash', )

    def __init__(self, scope=None,
                 cwd=None, env=None, tree=None, homes=None, files=None, ):
        """Initializes MockVfs: cwd, env, tree, homes and files can be given.

        >>> vfs = MockVfs()
        >>> 'MockVfs' in repr(vfs)
        True
        """
        self.cwd     = str( cwd   or self.std_cwd)
        self.environ = dict(env   or self.std_env)
        self.tree    = dict(tree  or self.std_tree)
        self.homes   = dict(homes or self.std_homes)
        self.files   = dict(files or self.std_files)
        self.stash   = {'calls': [], 'scope': scope}

    def _norm(self, p):
        if p[0] != '/':
            p = os.path.normpath(os.path.join(self.cwd, p))
        return p.split('/')[1:]

    def _lookup(self, p):
        x = self.tree
        for c in self._norm(p):
            y = x.get(c)
            if y is None:  return None
            else:          x = y
        return x

    def __enter__(self):
        scope = self.stash['scope']
        for m in 'environ expanduser getcwd isdir listdir open'.split():
            self.stash[m] = getattr(scope, m, None)
            setattr(scope, m, getattr(self, m))

    def __exit__(self, exc_type, exc_value, exc_tb):
        for m in 'environ expanduser getcwd isdir listdir open'.split():
            setattr(self.stash['scope'], m, self.stash[m])

    def record(f):
        def bug(self, *al, **kw):
            self.stash['calls'].append((f.func_name, al, kw,))
            return f(self, *al, **kw)
        return bug

    def getcwd(self):
        """Return a string representing the current working directory.

        >>> vfs = MockVfs()
        >>> vfs.getcwd()
        '/home/apu'
        >>> vfs.stash['calls']
        [('getcwd',)]
        """
        self.stash['calls'].append(('getcwd',))
        return self.cwd

    def listdir(self, p):
        """Return a list containing the names of the entries in the directory.

        >>> vfs = MockVfs()
        >>> vfs.listdir('.')
        ['Video', 'Downloads', 'Documents', 'Music']
        >>> vfs.listdir('/etc')
        ['cron.d', 'pam.d', 'init.d']
        >>> try:   vfs.listdir('/fnord')
        ... except Exception, e: pass
        >>> print e
        [Errno 2] No such file or directory: '/fnord'
        """
        self.stash['calls'].append(('listdir', p))
        x = self._lookup(p)
        if x is None:
            raise exceptions.IOError(2, 'No such file or directory', p)
        return x.keys()
        #return self._lookup(p).keys()

    def isdir(self, p):
        """Return true if the pathname refers to an existing directory.

        >>> MockVfs().isdir('/usr/lib/X11')
        True
        >>> MockVfs().isdir('/cat/dog/cthulhu')
        False
        """
        self.stash['calls'].append(('isdir', p))
        return self._lookup(p) is not None

    def open(self, fn, mode=None):
        """Return a file-like object with mock contents.

        >>> vfs = MockVfs()
        >>> try:   vfs.open('catdog')
        ... except Exception, e: pass
        >>> print e
        [Errno 2] No such file or directory: 'catdog'
        >>> f = vfs.open('/tmp/apu.dirt')
        >>> f.read()
        '/usr/share\\n/usr/lib/X11\\n/home/apu/Music\\n'
        >>> f.read()
        ''
        >>> f.seek(0)
        >>> map(lambda x: len(x), f)
        [11, 13, 16]
        """
        self.stash['calls'].append(('open', fn, mode))
        if fn in self.files:
            return cStringIO.StringIO(self.files[fn])
        else:
            raise exceptions.IOError(2, 'No such file or directory', fn)

    def expanduser(self, p):
        """Expand tilde to the home directory of users.

        >>> vfs = MockVfs()
        >>> vfs.expanduser('/foo/bar/baz')
        '/foo/bar/baz'
        >>> vfs.expanduser('~apu/foo/bar/baz')
        '/home/apu/foo/bar/baz'
        >>> vfs.expanduser('~/foo/bar/baz')
        '/home/apu/foo/bar/baz'
        >>> vfs.expanduser('~/foo/bar/baz')
        '/home/apu/foo/bar/baz'
        """
        self.stash['calls'].append(('expanduser', p))
        qw = p.split('/', 1)
        q, w = qw[0], qw[1:]
        if q is '~':       q = self.homes[self.environ['USER']]
        elif q[:1] is '~': q = self.homes[q[1:]]
        return '/'.join([q] + w)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
