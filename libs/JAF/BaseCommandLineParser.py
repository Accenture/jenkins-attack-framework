import sys
from urllib.parse import urlparse

from .CustomArgumentParser import ArgumentParser, Formatter


class BaseCommandLineParser:
    """Base Class to wrap common commandline parsing functionality, since it is complicated"""

    _description = "Jenkins Attack Framework"

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    THREADNUMBER = 4
    TIMEOUT = 30

    def parse(self):
        """Top-level method to handle argument parsing and return parsed, sanity checked arguments"""

        self.parser = ArgumentParser(formatter_class=Formatter, description=self._description)

        # Dynamically derive sub commands:
        choices = [name[4:] for name in dir(self) if name.startswith("cmd_")]

        self.parser.add_argument(
            dest="command",
            metavar="<Command>",
            help="Subcommand to run (pass sub command for more detailed help):\n"
            + " ".join(choices),
            choices=choices,
        )

        if len(sys.argv) < 2:
            self.parser.print_help()
            exit(-1)

        args = self.parser.parse_args(sys.argv[1:2])

        if len(sys.argv) == 2:
            # Ensure user gets full help if they don't specify subcommand args
            sys.argv.append("-h")

        return getattr(self, "cmd_" + args.command)()

    def _create_contextual_parser(self, cmd, description):
        """Creates context-specific argparse parser after subcommand is choosen"""

        self.parser = ArgumentParser(description=self._description, formatter_class=Formatter)
        self.parser.add_argument(dest="subcommand", metavar=cmd, help=description, action="store")

        return self.parser

    def _add_common_arg_parsers(self, allows_threading=False, allows_multiple_creds=False):
        """Utility method to handle adding common variations of common arguments"""

        self.parser.add_argument(
            "-s",
            "--server",
            metavar="<Server>",
            help="Jenkins Server",
            action="store",
            dest="server",
            required=True,
        )

        self.parser.add_argument(
            "-u",
            "--useragent",
            metavar="<User-Agent>",
            help="JAF User-Agent. Defaults to: %s" % self.UA,
            action="store",
            dest="user_agent",
            required=False,
            default=self.UA,
        )

        self.parser.add_argument(
            "-n",
            "--timeout",
            metavar="<Timeout>",
            help="HTTP Request Timeout (in seconds). Defaults to: %d" % self.TIMEOUT,
            action="store",
            dest="timeout",
            type=int,
            required=False,
            default=self.TIMEOUT,
        )

        self.parser.add_argument(
            "-o",
            "--output",
            metavar="Output File",
            help="Write Output to File",
            action="store",
            dest="output_file",
            required=False,
        )

        if allows_threading:
            self.parser.add_argument(
                "-t",
                "--threads",
                metavar="<Threads>",
                help="Number of max concurrent HTTP requests.  Defaults to: %d" % self.THREADNUMBER,
                type=int,
                required=False,
                dest="thread_number",
                action="store",
                default=self.THREADNUMBER,
            )

        self.parser.add_argument(
            "-a",
            "--authentication",
            metavar="[<User>:[<Password>|<API Token>]|<Cookie>]",
            help="User + Password or API Token, or full JSESSIONID cookie string",
            action="store",
            dest="credential",
            required=False,
        )

        if allows_multiple_creds:
            self.parser.add_argument(
                "-c",
                "--credentialfile",
                metavar="<Credential File>",
                help='Credential File ("-" for stdin). Creds in form "<User>:<Password>" or "<User>:<API Token>"',
                action="store",
                dest="credential_file",
                required=False,
            )

        return self.parser

    def _parse_credential(self, cred):
        """Utility method to parse out credential strings into useful formats"""

        if ":" in cred and not cred.startswith("{COOKIE}"):
            temp = cred.split(":")
            username = temp[0]
            password = ":".join(temp[1:])

            if username.startswith("{APITOKEN}"):
                return {"authheader": cred[10:]}
            elif username.startswith("{USERPASS}"):
                return {"username": username[10:], "password": password}
            elif len(password) == 34:
                return {"authheader": cred}
            else:
                return {"username": username, "password": password}
        elif "=" in cred:
            if "|" in cred:
                cred = cred.split("|")
                return {"cookie": cred[0], "crumb": "|".join(cred[1:])}
            else:
                return {"cookie": cred, "crumb": None}
        else:
            return None

    def _file_accessible(self, path):
        """Utility method to check if file exists and is read-accessible"""

        try:
            with open(path, "rb"):
                return True
        except Exception:
            return False

    def _validate_output_file(self, args):
        """Utility method to check if provided output file location is write-accessible"""

        if args.output_file:
            try:
                with open(args.output_file, "wb"):
                    return
            except Exception:
                sys.stdout = sys.stderr
                self.parser.print_usage()
                print("\nError: Specified Output File Path is invalid or inaccessible.")
                exit(1)

    def _validate_thread_number(self, args):
        """Utility method to check if provided thread number > 0"""

        if args.thread_number < 1:
            sys.stdout = sys.stderr
            self.parser.print_usage()
            print("\nError: Specified Thread Number is invalid.")
            exit(1)

    def _validate_timeout_number(self, args):
        """Utility method to check if provided timeout number > 0"""

        if args.timeout < 1:
            sys.stdout = sys.stderr
            self.parser.print_usage()
            print("\nError: Specified Timeout Number is invalid.")
            exit(1)

    def _validate_server_url(self, args):
        """Utility method to check if provided server is a valid url"""

        try:
            result = urlparse(args.server)
            if not all([result.scheme, result.netloc]):
                raise Exception()
        except Exception:
            sys.stdout = sys.stderr
            self.parser.print_usage()
            print("\nError: Specified Server is not a valid URL.")
            exit(1)

    def _handle_authentication(self, args):
        """Utility method to handle parsing of credentials and credential files"""

        creds = []

        if hasattr(args, "credential_file") and args.credential_file:
            try:
                if args.credential_file == "-":
                    f = sys.stdin
                else:
                    f = open(args.credential_file)

                for cred in f:
                    temp = self._parse_credential(cred.replace("\r", "").replace("\n", ""))

                    if temp:
                        creds.append(temp)

                f.close()

                if len(creds) == 0:
                    raise Exception()

                delattr(args, "credential_file")
            except Exception:
                sys.stdout = sys.stderr
                self.parser.print_usage()
                print("\nError: Invalid Credential File Path was passed or no credentials present.")
                exit(1)

        elif args.credential:
            temp = self._parse_credential(args.credential)

            if temp:
                creds.append(temp)

            if len(creds) == 0:
                sys.stdout = sys.stderr
                self.parser.print_usage()
                print("\nError: Invalid Credential Format.")
                exit(1)

            delattr(args, "credential")
        else:
            creds.append(None)

        setattr(args, "credentials", creds)

        return args
