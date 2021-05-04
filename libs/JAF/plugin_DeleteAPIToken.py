import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class DeleteAPIToken(BasePlugin):
    """Class for managing DeleteAPIToken SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            if not self.args.token_name:
                tokens = server.list_api_tokens(self.args.user_name)

                print("Current API Tokens:")

                for i, token in enumerate(tokens):
                    print(
                        "\tToken Name: {0}\n\tCreate Date: {1}\n\tUUID: {2}".format(
                            token["name"], token["creation_date"], token["uuid"]
                        )
                    )
                    if i != len(tokens) - 1:
                        print("")

                if len(tokens) == 0:
                    print("\tThere are no API tokens for this user.")
            else:
                server.delete_api_token(self.args.token_name, self.args.user_name)

                print("Token Deleted Successfully.")

        except jenkinslib.JenkinsException as ex:
            if "[403]" in str(ex).split("\n")[0]:
                self.logging.fatal(
                    "%s: Invalid Credentials or unable to access Jenkins server.",
                    self._get_username(cred),
                )
            else:
                self.logging.fatal(
                    "DeleteAPIToken Failed With User: %s For Reason:\n\t%s"
                    % (self._get_username(cred), str(ex).split("\n")[0])
                )

        except (req_exc.SSLError, req_exc.ConnectionError):
            self.logging.fatal(
                "Unable to connect to: "
                + (self.server_url.netloc if len(self.server_url.netloc) > 0 else self.args.server)
            )

        except Exception:
            self.logging.exception("")
            exit(1)


class DeleteAPITokenParser:
    def cmd_DeleteAPIToken(self):
        """Handles parsing of DeleteAPIToken Subcommand arguments"""

        self._create_contextual_parser("DeleteAPIToken", "Delete an API Token for your user")
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-U",
            "--user",
            metavar="<User Name>",
            help='If provided, will use Jenkins Script Console to delete token for this user.  (Requires Admin "/script" permissions)',
            action="store",
            dest="user_name",
            required=False,
        )

        self.parser.add_argument(
            metavar="<Token Name or UUID>",
            help="If not specified, command will return list of tokens for subsequent calls.",
            action="store",
            dest="token_name",
            nargs="?",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)

        return self._handle_authentication(args)
