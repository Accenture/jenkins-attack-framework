import os
import re

import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class DumpCreds(BasePlugin):
    """Class for managing DumpCreds SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        with open(os.path.join("data", "groovy", "dump_creds.groovy")) as f:
            dumpcreds = f.read()

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            if not server.can_access_script_console():
                self.logging.fatal(
                    "%s: Is not a valid Jenkins Admin or unable to access Jenkins server.",
                    self._get_username(cred),
                )

            result = server.execute_script(dumpcreds, node=self.args.node)

            result = re.sub(
                r"---------------------------------------------------[\r\n][\r\n]{2,}",
                "\n\n",
                result,
            ).strip()

            print(result)
        except jenkinslib.JenkinsException as ex:
            if "[403]" in str(ex).split("\n")[0]:
                self.logging.fatal(
                    "%s authentication failed or not an admin with script privileges",
                    self._get_username(cred),
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


class DumpCredsParser:
    def cmd_DumpCreds(self):
        """Handles parsing of DumpCreds Subcommand arguments"""

        self._create_contextual_parser("DumpCreds", "Dump all Stored Credentials on Jenkins")
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-N",
            "--node",
            metavar="<Node>",
            help='Node (Slave) to execute against. Executes against "master" if not specified.',
            action="store",
            dest="node",
            required=False,
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return self._handle_authentication(args)
