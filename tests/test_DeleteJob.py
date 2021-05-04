import random
import string
import unittest
import warnings

from libs import jenkinslib
from libs.JAF.BaseCommandLineParser import BaseCommandLineParser
from libs.JAF.plugin_DeleteJob import DeleteJob, DeleteJobParser

from .configuration import (
    computer_linux,
    computer_windows_admin,
    computer_windows_normal,
    server,
    user_admin,
    user_bad,
    user_noaccess,
    user_normal,
    user_read_job_access,
    user_read_no_job_access,
)
from .helpers import DummyWebServer, TestFramework


class DeleteJobTest(unittest.TestCase, TestFramework):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore", ResourceWarning)

        cls.test_job1 = "testDeleteJob" + "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        )

        jenkins_server = jenkinslib.Jenkins(
            server, username=user_admin.split(":")[0], password=":".join(user_admin.split(":")[1:])
        )

        jenkins_server.create_job(
            cls.test_job1, "<?xml version='1.1' encoding='UTF-8'?><project></project>"
        )

    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "DeleteJob"
        self.TestParserClass = DeleteJobParser
        self.TestClass = DeleteJob

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
                self.test_job1,
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
                    self.test_job1,
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
                    self.test_job1,
                ],
                [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
                1,
            )

    def test_valid_jenkins_invalid_creds(self):
        """Make sure that calling with valid jenkins (but bad creds) fails gracefully"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_bad, self.test_job1],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_anonymous_creds(self):
        """Make sure that calling with valid jenkins (but no creds)"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, self.test_job1],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_unprivileged_creds(self):
        """Make sure that calling with valid jenkins (unprivileged creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_noaccess, self.test_job1],
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
                self.test_job1,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_2_valid_jenkins_valid_normal_creds(self):
        """Make sure that calling with valid jenkins (normal creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_normal, self.test_job1],
            [
                r"WARNING: Unable to delete the job, attempting secondary clean-up\.  You should double check\."
            ],
            1,
        )

    def test_3_valid_jenkins_valid_admin_creds(self):
        """Make sure that calling with valid jenkins (admin creds) returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_admin, self.test_job1],
            [r"Successfully deleted the job\."],
        )


class DeleteJobParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "DeleteJob"
        self.TestClass = DeleteJob
        self.TestParserClass = DeleteJobParser

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
