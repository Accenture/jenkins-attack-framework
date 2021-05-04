import base64

import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin, HijackStdOut


class UploadFile(BasePlugin):
    """Class for managing UploadFile SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        try:
            i = 0
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            with open(self.args.local_file_path, "rb") as f:
                fail = False

                while True:
                    data = f.read(45000)
                    if not data:
                        break

                    result = server.execute_script(
                        'new File("{0}").append("{1}".decodeBase64())'.format(
                            self.args.remote_file_path.replace("\\", "\\\\"),
                            base64.b64encode(data).decode("ascii"),
                        ),
                        node=self.args.node,
                    ).strip()

                    if len(result) == 0:
                        i += 1
                        print("Successfully Uploaded Chunk {0}".format(i))
                    else:
                        fail = True
                        print("File failed to upload completely.  See following error:")
                        print(result)
                        break

                if not fail:
                    print("Successfully uploaded file.")

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

        except OSError:
            self.logging.fatal(
                "Error: The specified local file does not exist or is not accessible."
            )

        except Exception:
            self.logging.exception("")


class UploadFileParser:
    def cmd_UploadFile(self):
        """Handles parsing of UploadFile Subcommand arguments"""

        self._create_contextual_parser(
            "UploadFile",
            "Upload file to Jenkins Server via chunked upload through Jenkins Console (slow for large files)",
        )
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

        self.parser.add_argument(
            metavar="<Upload File>",
            help="Local Path to File to Upload",
            action="store",
            dest="local_file_path",
        )

        self.parser.add_argument(
            metavar="<Upload File Path>",
            help="Remote Full File Path to Upload To. SHOULD NOT ALREADY EXIST! (Upload is appended to existing file)",
            action="store",
            dest="remote_file_path",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return_data = self._handle_authentication(args)

        if not self._file_accessible(args.local_file_path):
            with HijackStdOut():
                self.parser.print_usage()
                print("\nError: Specified Upload File does not exist or cannot be accessed.")
                exit(1)

        return return_data
