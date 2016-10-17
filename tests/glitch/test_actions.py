import unittest

from matrix.plugins.glitch.actions import ACTIONS, action


class TestAction(unittest.TestCase):
    def test_define(self):
        self.assertFalse('faux_action' in ACTIONS)

        @action
        def faux_action(model, unit, **kwargs):
            pass

        self.assertTrue('faux_action' in ACTIONS)

if __name__ == '__main__':
    unittest.main()
