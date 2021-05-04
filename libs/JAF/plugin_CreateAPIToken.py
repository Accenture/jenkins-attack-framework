import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class CreateAPIToken(BasePlugin):
    """Class for managing CreateAPIToken SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            result = server.create_api_token(
                token_name=self.args.token_name, selected_username=self.args.user_name
            )

            print("Your new API Token is: {0}".format(result))

        except jenkinslib.JenkinsException as ex:
            if "[403]" in str(ex).split("\n")[0]:
                self.logging.fatal(
                    "%s: Invalid Credentials or unable to access Jenkins server.",
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


class CreateAPITokenParser:
    def cmd_CreateAPIToken(self):
        """Handles parsing of CreateAPIToken Subcommand arguments"""

        self._create_contextual_parser("CreateAPIToken", "Create an API Token for your user")
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-U",
            "--user",
            metavar="<User Name>",
            help='If provided, will use Jenkins Script Console to add token for this user.  (Requires Admin "/script" permissions)',
            action="store",
            dest="user_name",
            required=False,
        )

        self.parser.add_argument(
            metavar="<Token Name>",
            help="Token Name which is shown under the user's configuration page (so pick something that is not too suspicious). Can be duplicated (There do not appear to be any restrictions on token names). If not provided, only token creation date will be shown on user's page.",
            action="store",
            dest="token_name",
            nargs="?",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)

        return self._handle_authentication(args)
