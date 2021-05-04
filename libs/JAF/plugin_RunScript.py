import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin, HijackStdOut


class RunScript(BasePlugin):
    """Class for managing RunScript SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            with open(self.args.script_path) as f:
                result = server.execute_script(f.read(), not self.args.no_wait, node=self.args.node)

                if result:
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

        except OSError:
            self.logging.fatal("Specified Groovy Script does not exist or is not accessible.")

        except Exception:
            self.logging.exception("")
            exit(1)


class RunScriptParser:
    def cmd_RunScript(self):
        """Handles parsing of RunScript Subcommand arguments"""

        self._create_contextual_parser(
            "RunScript", "Run Specified Groovy Script via Jenkins Console"
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
            metavar="<Groovy File Path>",
            help="Groovy File Path to Run via Script Console",
            action="store",
            dest="script_path",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return_data = self._handle_authentication(args)

        if not self._file_accessible(args.script_path):
            with HijackStdOut():
                self.parser.print_usage()
                print("\nError: Specified Groovy File does not exist or cannot be accessed.")
                exit(1)

        return return_data
