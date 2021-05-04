import sys
import threading
from urllib.parse import urlparse

import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class ConsoleOutput(BasePlugin):
    """Class for managing ConsoleOutput SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        threads = []

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            if not server.can_read_jenkins():
                self.logging.fatal(
                    "%s: Invalid Credentials or unable to access Jenkins server.",
                    self._get_username(cred),
                )

            jobs = server.get_all_jobs()

            for _ in range(self.args.thread_number):
                t = threading.Thread(target=self._get_job_console_output, args=(server,))
                t.start()
                threads.append(t)

            for job in jobs:
                job["folder"] = urlparse(job["url"]).path[len(self.server_url.path) :]
                self.jobs_queue.put(job)

            jobs_exist = False

            for job in jobs:
                output = self.results_queue.get()

                if output:
                    jobs_exist = True
                    print("----------------------------------------------------------------")
                    print(output)
                    print("----------------------------------------------------------------")
                else:
                    print("%s has no builds" % (job["folder"]), file=sys.stderr)

            for _ in range(self.args.thread_number):
                self.jobs_queue.put(None)

            if not jobs_exist:
                self.logging.fatal(
                    "%s: No Jobs or Unable to see Jobs on Server.", self._get_username(cred)
                )

            for t in threads:
                t.join()
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

    def _get_job_console_output(self, server):
        while True:
            job = self.jobs_queue.get()

            if job is None:
                break

            try:
                console = server.get_build_console_output(job["folder"], "lastBuild")
                output = "Job: %s\n\n" % (job["url"])
                output = output + console
                self.results_queue.put(output)

            except Exception:
                print(job["folder"], "failed")
                self.results_queue.put(None)

            self.jobs_queue.task_done()


class ConsoleOutputParser:
    def cmd_ConsoleOutput(self):
        """Handles parsing of ConsoleOutput Subcommand arguments"""

        self._create_contextual_parser(
            "ConsoleOutput", "Get Latest Console Output from All Jenkins Jobs"
        )
        self._add_common_arg_parsers(allows_threading=True)

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_thread_number(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return self._handle_authentication(args)
