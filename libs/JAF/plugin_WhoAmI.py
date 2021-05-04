import json
import pprint
import threading

import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class WhoAmI(BasePlugin):
    """Class for managing WhoAmI SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        threads = []

        self._validate_jenkins_server_accessible()

        thread_number = min(self.args.thread_number, len(self.args.credentials))

        pp = pprint.PrettyPrinter(indent=4)

        for _ in range(thread_number):
            t = threading.Thread(target=self._get_job_whoami_output)
            t.start()
            threads.append(t)

        for cred in self.args.credentials:
            # Necessary to wrap cred in tuple as an anonymous query uses None and None also is used to signal the end of a job
            self.jobs_queue.put((cred,))

        for _ in range(len(self.args.credentials)):
            result = self.results_queue.get()

            if result:
                if "name" in result and "authorities" in result:
                    for entitlement in ["anonymous", "authenticated"]:
                        if entitlement in result and result[entitlement]:
                            result["authorities"].append(entitlement)

                    groups = list(set(result["authorities"]))
                    groups.sort(key=str.casefold)

                    print(result["name"] + ": " + json.dumps(groups))
                else:
                    data = pp.pformat(result)
                    data = " " + data[1:][:-1]

                    for line in data.replace("\r", "\n").replace("\n\n", "\n").split("\n"):
                        print(line[4:])

        for _ in range(thread_number):
            self.jobs_queue.put(None)

        for t in threads:
            t.join()

    def _get_job_whoami_output(self):
        while True:
            job = self.jobs_queue.get()

            if job is None:
                break

            cred = job[0]

            result = None

            try:
                server = self._get_jenkins_server(cred)
                if not server.can_read_jenkins():
                    result = {
                        "name": self._get_username(cred),
                        "authorities": ["Invalid Credentials or unaccessible Jenkins Server."],
                    }
                else:
                    result = server.get_whoAmI()
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
                    + (
                        self.server_url.netloc
                        if len(self.server_url.netloc) > 0
                        else self.args.server
                    )
                )

            except Exception:
                self.logging.exception("")
                exit(1)

            self.results_queue.put(result)
            self.jobs_queue.task_done()


class WhoAmIParser:
    def cmd_WhoAmI(self):
        """Handles parsing of WhoAmI Subcommand arguments"""

        self._create_contextual_parser("WhoAmI", "Get Users Roles and Possibly Domain Groups")
        self._add_common_arg_parsers(allows_threading=True, allows_multiple_creds=True)

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_thread_number(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return self._handle_authentication(args)
