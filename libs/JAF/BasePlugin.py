import base64
import logging
import queue
import sys
from urllib.parse import urlparse

import requests.exceptions as req_exc

from libs import jenkinslib


def _logging_fatal(msg, *args, **kwargs):
    logging.critical(msg, *args, **kwargs)
    exit(1)


class HijackStdOut:
    def __enter__(self):
        # Preserve old stdout because we may already have hijacked it
        self.old_stdout = sys.stdout
        sys.stdout = sys.stderr

        return sys.stdout

    def __exit__(self, _type, value, traceback):
        sys.stdout = self.old_stdout


class BasePlugin:
    """JAF Plugin Base Class"""

    results_queue = queue.Queue()
    jobs_queue = queue.Queue()

    def __init__(self, args):
        self.args = args

        logging.basicConfig(format="%(asctime)s - %(message)s")

        self.logging = logging.getLogger()
        self.logging.fatal = _logging_fatal

        self.server_url = urlparse(self.args.server)

        if args.output_file:
            try:
                sys.stdout = open(args.output_file, "w")
            except Exception:
                self.logging.fatal("Specified Output File Path is invalid or inaccessible.")

    def _get_jenkins_server(self, cred):
        """Setup initial connection to the jenkins server and handle authentication

        :param cred: Credential dict"""

        try:
            if cred:
                if "cookie" in cred:
                    return jenkinslib.Jenkins(
                        self.args.server,
                        cookie=cred["cookie"],
                        crumb=cred["crumb"],
                        timeout=self.args.timeout,
                        headers={"User-Agent": self.args.user_agent},
                    )
                elif "authheader" in cred:
                    return jenkinslib.Jenkins(
                        self.args.server,
                        authheader="Basic "
                        + base64.b64encode(cred["authheader"].encode("utf8")).decode("ascii"),
                        timeout=self.args.timeout,
                        headers={"User-Agent": self.args.user_agent},
                    )
                else:
                    return jenkinslib.Jenkins(
                        self.args.server,
                        username=cred["username"],
                        password=cred["password"],
                        timeout=self.args.timeout,
                        headers={"User-Agent": self.args.user_agent},
                    )
            else:
                return jenkinslib.Jenkins(
                    self.args.server,
                    timeout=self.args.timeout,
                    headers={"User-Agent": self.args.user_agent},
                )
        except jenkinslib.JenkinsException as ex:
            if "[403]" in str(ex).split("\n")[0]:
                self.logging.fatal(
                    "%s authentication failed or no access", self._get_username(cred)
                )
            else:
                self.logging.fatal(
                    "Unable to access Jenkins at: %s With User: %s For Reason:\n\t%s"
                    % (
                        (
                            self.server_url.netloc
                            if len(self.server_url.netloc) > 0
                            else self.args.server
                        ),
                        self._get_username(cred),
                        str(ex).split("\n")[0],
                    )
                )

        except (req_exc.SSLError, req_exc.ConnectionError):
            self.logging.fatal(
                "Unable to connect to: "
                + (self.server_url.netloc if len(self.server_url.netloc) > 0 else self.args.server)
            )

        except Exception:
            self.logging.exception("")

    def _get_username(self, cred):
        """Utility function to return the user based on the cred type to display in error messages."""

        if not cred:
            return "Anonymous"
        elif "username" in cred:
            return cred["username"]
        elif "authheader" in cred:
            return cred["authheader"].split(":")[0]
        elif not cred:
            return "Anonymous"
        else:
            return "Cookie (User Unknown)"

    def _validate_jenkins_server_accessible(self):
        """Utility function to return if we appear to have access to the jenkins server or not"""

        # Catch inaccessible server before slamming a bunch of threads at it.
        cred = None
        server = self._get_jenkins_server(cred)

        if server.basic_access_check() != 500:
            return True
        else:
            return False
