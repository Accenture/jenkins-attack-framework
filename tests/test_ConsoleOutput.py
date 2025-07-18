import unittest
import warnings

from libs.JAF.BaseCommandLineParser import BaseCommandLineParser
from libs.JAF.plugin_ConsoleOutput import ConsoleOutput, ConsoleOutputParser

from .configuration import (
    server,
    user_admin,
    user_bad,
    user_noaccess,
    user_normal,
    user_read_job_access,
    user_read_no_job_access,
)
from .helpers import DummyWebServer, TestFramework


class ConsoleOutputTest(unittest.TestCase, TestFramework):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "ConsoleOutput"
        self.TestParserClass = ConsoleOutputParser
        self.TestClass = ConsoleOutput

    def test_invalid_url(self):
        """Make sure that calling with invalid url fails gracefully"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", "https://127.0.0.1:59321/", "-a", user_bad],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_url_bad_protocol(self):
        """Make sure that calling with valid url (that isn't Jenkins or right protocol) fails gracefully"""

        with DummyWebServer():
            self.basic_test_harness(
                ["jaf.py", self.testcommand, "-s", "https://127.0.0.1:59322/", "-a", user_bad],
                [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
                1,
            )

    def test_valid_url_and_protocol(self):
        """Make sure that calling with valid url (that isn't Jenkins but right protocol) fails gracefully"""

        with DummyWebServer():
            self.basic_test_harness(
                ["jaf.py", self.testcommand, "-s", "http://127.0.0.1:59322/", "-a", user_bad],
                [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
                1,
            )

    def test_valid_jenkins_invalid_creds(self):
        """Make sure that calling with valid jenkins (but bad creds) fails gracefully"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_bad],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_anonymous_creds(self):
        """Make sure that calling with valid jenkins (but no creds)"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_unprivileged_creds(self):
        """Make sure that calling with valid jenkins (unprivileged creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_noaccess],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_read_no_job_creds(self):
        """Make sure that calling with valid jenkins (read only [no job access] creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_read_no_job_access],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_read_job_creds(self):
        """Make sure that calling with valid jenkins (read only [job access] creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_read_job_access], [r"Job: "]
        )

    def test_valid_jenkins_valid_normal_creds(self):
        """Make sure that calling with valid jenkins (normal creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_normal], [r"Job: "]
        )

    def test_valid_jenkins_valid_admin_creds(self):
        """Make sure that calling with valid jenkins (admin creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin], [r"Job: "]
        )


class ConsoleOutputParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "ConsoleOutput"
        self.TestClass = ConsoleOutput
        self.TestParserClass = ConsoleOutputParser

    def test_no_args(self):
        """Ensure that calling with no arguments results in help output and not an error"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand],
            [
                r"usage: jaf.py {0} \[-h\]".format(self.testcommand),
                r"Jenkins Attack Framework",
                r"positional arguments:",
            ],
        )

    def test_build_attempts_argument(self):
        """Test the --builds argument"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, "-b", "5"],
            [r"Job: "]
        )

    def test_include_failed_argument(self):
        """Test the --failed argument"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, "-f"],
            [r"Job: "]
        )

    def test_all_builds_argument(self):
        """Test the --builds -1 argument for all builds"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, "-b", "-1"],
            [r"Job: "]
        )

    def test_invalid_build_attempts(self):
        """Test invalid build attempts value"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, "-b", "0"],
            [r"Build attempts must be -1 \(for all builds\) or a positive number"],
            1,
        )

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, "-b", "-2"],
            [r"Build attempts must be -1 \(for all builds\) or a positive number"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
