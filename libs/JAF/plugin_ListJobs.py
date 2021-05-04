from urllib.parse import urlparse

import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class ListJobs(BasePlugin):
    """Class for managing ListJobs SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            result = server.basic_access_check()

            if result == 500 or result == 401:
                self.logging.fatal(
                    "Either no access to read jobs or Unable to access Jenkins at: %s",
                    (
                        self.server_url.netloc
                        if len(self.server_url.netloc) > 0
                        else self.args.server
                    ),
                )
                return

            jobs = server.get_all_jobs()

            for job in jobs:
                print(urlparse(job["url"]).path[len(self.server_url.path) :])

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
            exit(1)


class ListJobsParser:
    def cmd_ListJobs(self):
        """Handles parsing of ListJobs Subcommand arguments"""

        self._create_contextual_parser("ListJobs", "Get List of All Jenkins Job Names")
        self._add_common_arg_parsers()

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return self._handle_authentication(args)
