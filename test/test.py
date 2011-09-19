import sys
import os.path
import unittest
from mock_vfs import MockVfs

sys.path.insert(0, os.path.normpath(os.path.join(__file__, '../../')))
import dirt


class DirtTestBase(unittest.TestCase):
    def assertShown(self, *needles):
        c = self.capture()
        for n in needles:
            self.assertTrue(n in c,
                            "Excpected %s on screen. Instead:\n"
                            "%s" % (n, c))

    def capture(self):
        sy, sx = dirt.stdscr.getmaxyx()
        return ('\n'.join(
            (''.join(
                chr(dirt.stdscr.inch(y, x) % 256)
                for x in range(sx)))
            for y in range(sy))).rstrip()

    def run_it(self, cls=dirt.SessionMenu, obj=None, vfs=None,
               refresh=None, getch=None,
               see=None, expect=StopIteration,):

        def default_refresh(menu):
            if see:
                self.assertShown(*see)
            menu.orig_refresh()
            pass

        def default_getch(menu):
            return ord('q')

        dirt.Menu.refresh = refresh or default_refresh
        dirt.Menu.getch   = getch   or default_getch
        with vfs or MockVfs(scope=dirt):
            obj = obj or cls(dirt.stdscr)

            if issubclass(expect, Exception,):
                self.assertRaises(expect, obj.run)
            else:
                self.assertEqual(expect, obj.run())


class DirtTest(DirtTestBase):
    def test_session_items(self):
        self.run_it(cls=dirt.SessionMenu,
                    see=('/etc/cron.d', '/var/games'))

    def test_directory_items(self, ):
        self.run_it(cls=dirt.TreeMenu,
                    see=('Documents', 'Downloads', 'Music', 'Video'))

    def test_shared_items(self, ):
        dirt.SHAR.kw['fn'] = '/tmp/apu.dirt'
        self.run_it(cls=dirt.SharedMenu,
                    see=('/usr/lib/X11', '/usr/share', '/home/apu/Music'))

        self.assertEqual(dirt.SHAR.fn, '/tmp/apu.dirt')


class DirtTestSuite(unittest.TestSuite):
    def run(self, result):
        with dirt.CursesContext():
            super(DirtTestSuite, self).run(result)

def load_tests(*al):
    return DirtTestSuite(( DirtTest('test_directory_items'),
                           DirtTest('test_session_items'),
                           DirtTest('test_shared_items'),
                           ))

def run_tests():
    dirt.Menu.orig_refresh = dirt.Menu.refresh
    dirt.Menu.orig_getch   = dirt.Menu.getch
    unittest.TextTestRunner().run(load_tests())

if __name__ == '__main__':
    run_tests()
