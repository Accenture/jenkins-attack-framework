import concurrent.futures
import os
import tempfile
import unittest
import warnings

from libs.JAF.BaseCommandLineParser import BaseCommandLineParser
from libs.JAF.plugin_RunScript import RunScript, RunScriptParser

from .configuration import (
    server,
    user_admin,
    user_bad,
    user_noaccess,
    user_normal,
    user_read_job_access,
    user_read_no_job_access,
)
from .helpers import DummyWebServer, RemoteFeedbackTester, TestFramework


class RunScriptTest(unittest.TestCase, TestFramework):
    @classmethod
    def setUpClass(cls):
        cls.remote_feedback = RemoteFeedbackTester(12345, 50)
        f, cls.groovy_script = tempfile.mkstemp(text=True)
        os.write(f, cls.remote_feedback.get_script("groovy").encode("utf8"))
        os.close(f)

    @classmethod
    def teardownClass(cls):
        os.remove(cls.groovy_script)

    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "RunScript"
        self.TestParserClass = RunScriptParser
        self.TestClass = RunScript

    def test_invalid_url(self):
        """Make sure that calling with invalid url fails gracefully"""

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                "https://127.0.0.1:59321/",
                "-a",
                user_bad,
                self.groovy_script,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_url_bad_protocol(self):
        """Make sure that calling with valid url (that isn't Jenkins or right protocol) fails gracefully"""

        with DummyWebServer():
            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    "https://127.0.0.1:59322/",
                    "-a",
                    user_bad,
                    self.groovy_script,
                ],
                [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
                1,
            )

    def test_valid_url_and_protocol(self):
        """Make sure that calling with valid url (that isn't Jenkins but right protocol) fails gracefully"""

        with DummyWebServer():
            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    "http://127.0.0.1:59322/",
                    "-a",
                    user_bad,
                    self.groovy_script,
                ],
                [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
                1,
            )

    def test_valid_jenkins_invalid_creds(self):
        """Make sure that calling with valid jenkins (but bad creds) fails gracefully"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_bad, self.groovy_script],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_anonymous_creds(self):
        """Make sure that calling with valid jenkins (but no creds)"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, self.groovy_script],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_unprivileged_creds(self):
        """Make sure that calling with valid jenkins (unprivileged creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_noaccess, self.groovy_script],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_read_no_job_creds(self):
        """Make sure that calling with valid jenkins (read only [no job access] creds) returns expected results"""

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_read_no_job_access,
                self.groovy_script,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_read_job_creds(self):
        """Make sure that calling with valid jenkins (read only [job access] creds) returns expected results"""

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_read_job_access,
                self.groovy_script,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_normal_creds(self):
        """Make sure that calling with valid jenkins (normal creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_normal, self.groovy_script],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_admin_creds(self):
        """Make sure that calling with valid jenkins (admin creds) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, self.groovy_script]
            )

            self.assertTrue(future.result())


class RunScriptParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "RunScript"
        self.TestClass = RunScript
        self.TestParserClass = RunScriptParser

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


if __name__ == "__main__":
    unittest.main()
