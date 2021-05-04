import os
import re

import requests.exceptions as req_exc

from libs import jenkinslib, quik

from .BasePlugin import BasePlugin


class RunCommand(BasePlugin):
    """Class for managing RunCommand SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        loader = quik.FileLoader(os.path.join("data", "groovy"))
        cmd_template = loader.load_template("run_command_template.groovy")

        cmd = cmd_template.render(
            {"command": self.args.system_command.replace("\\", "\\\\").replace('"', '\\"')}
        )

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            result = server.execute_script(cmd, not self.args.no_wait, node=self.args.node)

            if result:
                result = re.sub(r"[\r\n][\r\n]{2,}", "\n\n", result).strip()
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


class RunCommandParser:
    def cmd_RunCommand(self):
        """Handles parsing of RunCommand Subcommand arguments"""

        self._create_contextual_parser(
            "RunCommand", "Run System Command on Jenkins via Jenkins Console"
        )
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-x",
            "--no_wait",
            help="Do not wait for Output",
            action="store_true",
            dest="no_wait",
            required=False,
        )

        self.parser.add_argument(
            "-N",
            "--node",
            metavar="<Node>",
            help='Node (Slave) to execute against. Executes against "master" if not specified.',
            action="store",
            dest="node",
            required=False,
        )

        self.parser.add_argument(
            metavar="<System Command>",
            help="System Command To Run",
            action="store",
            dest="system_command",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return self._handle_authentication(args)
