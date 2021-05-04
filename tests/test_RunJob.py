import concurrent.futures
import os
import random
import string
import tempfile
import unittest
import warnings

from libs.JAF.BaseCommandLineParser import BaseCommandLineParser
from libs.JAF.plugin_RunJob import RunJob, RunJobParser

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
from .helpers import DummyWebServer, RemoteFeedbackTester, TestFramework


class DumpCredsViaJobTest(unittest.TestCase, TestFramework):
    @classmethod
    def setUpClass(cls):
        cls.credential_test_job1 = "testRunJob1" + "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        )
        cls.credential_test_job2 = "testRunJob2" + "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        )
        cls.remote_feedback = RemoteFeedbackTester(12345, 50)
        f, cls.ping_script_windows = tempfile.mkstemp(text=True, suffix=".bat")
        os.write(f, cls.remote_feedback.get_script("python").encode("utf8"))
        os.close(f)
        f, cls.ping_script_linux = tempfile.mkstemp(text=True, suffix=".sh")
        os.write(f, cls.remote_feedback.get_script("python").encode("utf8"))
        os.close(f)

    @classmethod
    def teardownClass(cls):
        os.remove(cls.ping_script_windows)
        os.remove(cls.ping_script_linux)

    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "RunJob"
        self.TestParserClass = RunJobParser
        self.TestClass = RunJob

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
                self.credential_test_job1,
                self.ping_script_linux,
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
                    self.credential_test_job1,
                    self.ping_script_linux,
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
                    self.credential_test_job1,
                    self.ping_script_linux,
                ],
                [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
                1,
            )

    def test_valid_jenkins_invalid_creds(self):
        """Make sure that calling with valid jenkins (but bad creds) fails gracefully"""

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_bad,
                self.credential_test_job1,
                self.ping_script_linux,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_anonymous_creds(self):
        """Make sure that calling with valid jenkins (but no creds)"""

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                self.credential_test_job1,
                self.ping_script_linux,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    def test_valid_jenkins_valid_unprivileged_creds(self):
        """Make sure that calling with valid jenkins (unprivileged creds) returns expected results"""

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_noaccess,
                self.credential_test_job1,
                self.ping_script_linux,
            ],
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
                self.credential_test_job1,
                self.ping_script_linux,
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
                self.credential_test_job1,
                self.ping_script_linux,
            ],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )

    # Swapping order because last test doesn't clean up completely.
    def test_1_valid_jenkins_valid_admin_creds_posix(self):
        """Make sure that calling with valid jenkins (admin creds, POSIX) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    server,
                    "-a",
                    user_admin,
                    "-N",
                    computer_linux,
                    "-T",
                    "posix",
                    self.credential_test_job1,
                    self.ping_script_linux,
                ]
            )

            self.assertTrue(future.result())

    def test_1_valid_jenkins_valid_admin_creds_windows(self):
        """Make sure that calling with valid jenkins (admin creds, Windows) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    server,
                    "-a",
                    user_admin,
                    "-N",
                    computer_windows_admin,
                    "-T",
                    "windows",
                    self.credential_test_job1,
                    self.ping_script_windows,
                ]
            )

            self.assertTrue(future.result())

    def test_2_valid_jenkins_valid_admin_creds_ghost_job_windows_unprivileged(self):
        """Make sure that calling with valid jenkins (admin creds, Windows, unprivileged ghost job) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    server,
                    "-a",
                    user_admin,
                    "-g",
                    "-N",
                    computer_windows_normal,
                    "-T",
                    "windows",
                    self.credential_test_job1,
                    self.ping_script_windows,
                ]
            )

            self.assertTrue(future.result())

    def test_2_valid_jenkins_valid_admin_creds_ghost_job_windows_elevated(self):
        """Make sure that calling with valid jenkins (admin creds, Windows, elevated ghost job) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    server,
                    "-a",
                    user_admin,
                    "-g",
                    "-N",
                    computer_windows_admin,
                    "-T",
                    "windows",
                    self.credential_test_job1,
                    self.ping_script_windows,
                ]
            )

            self.assertTrue(future.result())

    def test_3_valid_jenkins_valid_normal_creds_linux(self):
        """Make sure that calling with valid jenkins (normal creds, POSIX) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    server,
                    "-a",
                    user_normal,
                    "-N",
                    computer_linux,
                    "-T",
                    "posix",
                    self.credential_test_job1,
                    self.ping_script_linux,
                ]
            )

            self.assertTrue(future.result())

    def test_3_valid_jenkins_valid_normal_creds_windows(self):
        """Make sure that calling with valid jenkins (normal creds, Windows) returns expected results"""

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.remote_feedback.got_connect_back)

            self.basic_test_harness(
                [
                    "jaf.py",
                    self.testcommand,
                    "-s",
                    server,
                    "-a",
                    user_normal,
                    "-N",
                    computer_windows_normal,
                    "-T",
                    "windows",
                    self.credential_test_job2,
                    self.ping_script_windows,
                ]
            )

            self.assertTrue(future.result())


class DumpCredsViaJobParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "RunJob"
        self.TestClass = RunJob
        self.TestParserClass = RunJobParser

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
