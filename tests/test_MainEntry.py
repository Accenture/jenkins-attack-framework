import unittest

from libs import JAF

from .helpers import TestFramework


class MainEntryTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.TestClass = None
        self.TestParserClass = None

    def test_mainentry(self):
        self.basic_test_harness(
            ["jaf.py"],
            [r"usage: \w+ <Command> \[-h\]", r"Jenkins Attack Framework", r"positional arguments:"],
            -1,
        )


if __name__ == "__main__":
    unittest.main()
