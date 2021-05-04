import random
import string
import unittest
import warnings

from libs import jenkinslib
from libs.JAF.BaseCommandLineParser import BaseCommandLineParser
from libs.JAF.plugin_CreateAPIToken import CreateAPIToken, CreateAPITokenParser
from libs.JAF.plugin_DeleteAPIToken import DeleteAPIToken, DeleteAPITokenParser
from libs.JAF.plugin_ListAPITokens import ListAPITokens, ListAPITokensParser

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


class CreateAPITokenTest(unittest.TestCase, TestFramework):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "CreateAPIToken"
        self.TestParserClass = CreateAPITokenParser
        self.TestClass = CreateAPIToken

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

    def test_valid_jenkins_valid_normal_creds_with_user_argument(self):
        """Make sure that calling with valid jenkins (normal creds) and user flag returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_normal, "-U", user_admin],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )


class CreateAPITokenParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "CreateAPIToken"
        self.TestClass = CreateAPIToken
        self.TestParserClass = CreateAPITokenParser

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


class DeleteAPITokenTest(unittest.TestCase, TestFramework):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "DeleteAPIToken"
        self.TestParserClass = DeleteAPITokenParser
        self.TestClass = DeleteAPIToken

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

    def test_valid_jenkins_valid_normal_creds_with_user_argument(self):
        """Make sure that calling with valid jenkins (normal creds) and user flag returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_normal, "-U", user_admin],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )


class DeleteAPITokenParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

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


class ListAPITokensTest(unittest.TestCase, TestFramework):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        self.testcommand = "ListAPITokens"
        self.TestParserClass = ListAPITokensParser
        self.TestClass = ListAPITokens

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

    def test_valid_jenkins_valid_read_no_job_creds_token_list(self):
        """Make sure that calling CreateAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "ListAPITokens"
        self.TestClass = ListAPITokens
        self.TestParserClass = ListAPITokensParser

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_read_no_job_access],
            [r"Current API Tokens:"],
        )

    def test_valid_jenkins_valid_normal_creds_with_user_argument(self):
        """Make sure that calling with valid jenkins (normal creds) and user flag returns expected results"""

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_normal, "-U", user_admin],
            [r"- \w+: Invalid Credentials or unable to access Jenkins server."],
            1,
        )


class ListAPITokensParserTest(unittest.TestCase, TestFramework):
    def setUp(self):
        self.testcommand = "ListAPITokens"
        self.TestClass = ListAPITokens
        self.TestParserClass = ListAPITokensParser

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


class CombinedAPITokenNormalUserCredentialsTest(unittest.TestCase, TestFramework):
    @classmethod
    def setUpClass(cls):
        cls.token_name = "testtoken" + "".join(
            random.choices(string.ascii_letters + string.digits, k=26)
        )

    def test_1_valid_jenkins_valid_read_no_job_creds_token_create(self):
        """Make sure that calling CreateAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "CreateAPIToken"
        self.TestClass = CreateAPIToken
        self.TestParserClass = CreateAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_read_no_job_access,
                self.token_name,
            ],
            [r"Your new API Token is: "],
        )

    def test_2_valid_jenkins_valid_read_no_job_creds_token_list(self):
        """Make sure that calling CreateAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "ListAPITokens"
        self.TestClass = ListAPITokens
        self.TestParserClass = ListAPITokensParser

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_read_no_job_access],
            [r"Token Name: " + self.token_name],
        )

    def test_3_valid_jenkins_valid_read_no_job_creds_token_delete_list(self):
        """Make sure that calling DeleteAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

        self.basic_test_harness(
            ["jaf.py", self.testcommand, "-s", server, "-a", user_read_no_job_access],
            [r"Token Name: " + self.token_name],
        )

    def test_4_valid_jenkins_valid_read_no_job_creds_token_delete(self):
        """Make sure that calling DeleteAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_read_no_job_access,
                self.token_name,
            ],
            [r"Token Deleted Successfully."],
        )


# For now this is commented out because we can only test this on a cloudbees federated setup, which we don't have
'''
class CombinedAPITokenNormalUserCookieTest(unittest.TestCase, TestFramework):
    """
    We need to specifically test auth with cookies because code has to do extra work to derive the logged-in user's username
    """

    @classmethod
    def setUpClass(cls):
        cls.token_name = "testtoken" + "".join(
            random.choices(string.ascii_letters + string.digits, k=26)
        )

        try:
            js = jenkinslib.Jenkins(
                server,
                username=user_read_no_job_access.split(':')[0],
                password=':'.join(user_read_no_job_access.split(':')[1:]),
                timeout=30,
            )

            cls.cookie = js.get_cookie()
        except Exception:
            print(cls.cookie)
            #Failure will cause tests to fail, so we ignore here
            pass

    def test_1_valid_jenkins_valid_read_no_job_creds_token_create(self):
        """Make sure that calling CreateAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "CreateAPIToken"
        self.TestClass = CreateAPIToken
        self.TestParserClass = CreateAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                self.cookie,
                self.token_name,
            ],
            [r"Your new API Token is: "],
        )

    def test_2_valid_jenkins_valid_read_no_job_creds_token_list(self):
        """Make sure that calling CreateAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "ListAPITokens"
        self.TestClass = ListAPITokens
        self.TestParserClass = ListAPITokensParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                self.cookie,
            ],
            [r"Token Name: " + self.token_name],
        )

    def test_3_valid_jenkins_valid_read_no_job_creds_token_delete_list(self):
        """Make sure that calling DeleteAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                self.cookie,
            ],
            [r"Token Name: " + self.token_name],
        )

    def test_4_valid_jenkins_valid_read_no_job_creds_token_delete(self):
        """Make sure that calling DeleteAPIToken with valid jenkins (read only [no job access] creds) returns expected results"""

        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                self.cookie,
                self.token_name,
            ],
            [r"Token Deleted Successfully."],
        )
'''


class CombinedAPITokenAdminUserTest(unittest.TestCase, TestFramework):
    @classmethod
    def setUpClass(cls):
        cls.token_name = "testtoken" + "".join(
            random.choices(string.ascii_letters + string.digits, k=26)
        )

    def test_1_valid_jenkins_valid_admin_creds_token_create_other_user(self):
        """Make sure that calling CreateAPIToken with valid jenkins (admin creds) returns expected results"""

        self.testcommand = "CreateAPIToken"
        self.TestClass = CreateAPIToken
        self.TestParserClass = CreateAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_admin,
                "-U",
                user_read_no_job_access,
                self.token_name,
            ],
            [r"Your new API Token is: "],
        )

    def test_2_valid_jenkins_valid_admin_creds_token_list_other_user(self):
        """Make sure that calling CreateAPIToken with valid jenkins (admin creds) returns expected results"""

        self.testcommand = "ListAPITokens"
        self.TestClass = ListAPITokens
        self.TestParserClass = ListAPITokensParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_admin,
                "-U",
                user_read_no_job_access,
            ],
            [r"Token Name: " + self.token_name],
        )

    def test_3_valid_jenkins_valid_admin_creds_token_delete_list_other_user(self):
        """Make sure that calling DeleteAPIToken with valid jenkins (admin creds) returns expected results"""

        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_admin,
                "-U",
                user_read_no_job_access,
            ],
            [r"Token Name: " + self.token_name],
        )

    def test_4_valid_jenkins_valid_admin_creds_token_delete_other_user(self):
        """Make sure that calling DeleteAPIToken with valid jenkins (admin creds) returns expected results"""

        self.testcommand = "DeleteAPIToken"
        self.TestClass = DeleteAPIToken
        self.TestParserClass = DeleteAPITokenParser

        self.basic_test_harness(
            [
                "jaf.py",
                self.testcommand,
                "-s",
                server,
                "-a",
                user_admin,
                "-U",
                user_read_no_job_access,
                self.token_name,
            ],
            [r"Token Deleted Successfully."],
        )


if __name__ == "__main__":
    unittest.main()
