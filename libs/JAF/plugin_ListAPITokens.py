import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class ListAPITokens(BasePlugin):
    """Class for managing ListAPITokens SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

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

        except jenkinslib.JenkinsException as ex:
            if "[403]" in str(ex).split("\n")[0]:
                self.logging.fatal(
                    "%s: Invalid Credentials or unable to access Jenkins server.",
                    self._get_username(cred),
                )
            else:
                self.logging.fatal(
                    "ListAPITokens Failed With User: %s For Reason:\n\t%s"
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


class ListAPITokensParser:
    def cmd_ListAPITokens(self):
        """Handles parsing of ListAPITokens Subcommand arguments"""

        self._create_contextual_parser("ListAPITokens", "List API Tokens for your user")
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-U",
            "--user",
            metavar="<User Name>",
            help='If provided, will use Jenkins Script Console to query tokens for this user.  (Requires Admin "/script" permissions)',
            action="store",
            dest="user_name",
            required=False,
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)

        return self._handle_authentication(args)
