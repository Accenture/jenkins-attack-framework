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
                # First, try to get job info to see if there are any builds
                job_info = server.get_job_info(job["fullname"])
                
                if not job_info.get("builds") or len(job_info["builds"]) == 0:
                    # No builds exist for this job
                    self.results_queue.put(None)
                    continue
                
                # Try to get console output from the last build
                console = None
                build_number = None
                build_attempts = getattr(self.args, 'build_attempts', 3)
                include_failed = getattr(self.args, 'include_failed', False)
                
                # First try lastBuild
                try:
                    console = server.get_build_console_output(job["folder"], "lastBuild")
                    build_number = "lastBuild"
                except jenkinslib.JenkinsException:
                    # If lastBuild fails, try the most recent build numbers
                    for build in job_info["builds"][:build_attempts]:
                        try:
                            # Check if we should skip failed builds
                            if not include_failed:
                                build_info = server.get_build_info(job["fullname"], build["number"])
                                if build_info.get("result") != "SUCCESS":
                                    continue
                            
                            build_number = build["number"]
                            console = server.get_build_console_output(job["folder"], build_number)
                            break
                        except jenkinslib.JenkinsException:
                            continue
                
                if console:
                    output = "Job: %s (Build: %s)\n\n" % (job["url"], build_number)
                    output = output + console
                    self.results_queue.put(output)
                else:
                    # No console output could be retrieved
                    self.results_queue.put(None)

            except Exception:
                print(job["folder"], "failed")
                self.results_queue.put(None)

            self.jobs_queue.task_done()


class ConsoleOutputParser:
    def cmd_ConsoleOutput(self):
        """Handles parsing of ConsoleOutput SubCommand arguments"""

        self._create_contextual_parser(
            "ConsoleOutput", "Get Console Output from Jenkins Jobs (including failed builds)"
        )
        self._add_common_arg_parsers(allows_threading=True)

        self.parser.add_argument(
            "-b",
            "--builds",
            metavar="<Number>",
            help="Number of recent builds to try if the last build fails (default: 3)",
            action="store",
            dest="build_attempts",
            type=int,
            default=3,
            required=False,
        )

        self.parser.add_argument(
            "-f",
            "--failed",
            help="Include console output from failed builds (default: only successful builds)",
            action="store_true",
            dest="include_failed",
            required=False,
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_thread_number(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)
        
        # Validate build_attempts
        if args.build_attempts < 1 or args.build_attempts > 50:
            self.logging.fatal("Build attempts must be between 1 and 50")

        return self._handle_authentication(args)
