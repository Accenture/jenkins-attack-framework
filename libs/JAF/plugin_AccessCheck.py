import threading

import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin


class AccessCheck(BasePlugin):
    """Class for managing AccessCheck SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        access_checks = ["read", "build", "admin", "script", "scriptler"]

        self._validate_jenkins_server_accessible()

        for cred in self.args.credentials:
            username = self._get_username(cred)

            threads = []
            thread_number = min(self.args.thread_number, len(access_checks))

            server = self._get_jenkins_server(cred)

            if not server.can_read_jenkins():
                if len(self.args.credentials) == 1:
                    # Only one credential so we can just bail with a proper full error
                    self.logging.fatal(
                        "%s: Invalid Credentials or unable to access Jenkins server.", username
                    )
                else:
                    print(
                        "{0}: Invalid Credentials or unable to access Jenkins server.".format(
                            username
                        )
                    )

                continue

            for _ in range(thread_number):
                t = threading.Thread(target=self._get_user_check_access, args=(server, username))
                t.start()
                threads.append(t)

            for job in access_checks:
                self.jobs_queue.put(job)

            for _ in range(len(access_checks)):
                result = self.results_queue.get()
                if result:
                    print(result)

            for _ in range(thread_number):
                self.jobs_queue.put(None)

            for t in threads:
                t.join()

    def _get_user_check_access(self, server, username):
        error = False

        while True:
            access_type = self.jobs_queue.get()

            if access_type is None:
                break

            # We had an auth error, consume tasks, but don't make any more requests.
            if error:
                self.results_queue.put(None)
                self.jobs_queue.task_done()
                continue

            try:
                if access_type == "script":
                    self.results_queue.put(
                        username
                        + " can Access Script Console: "
                        + str(server.can_access_script_console())
                    )
                elif access_type == "admin":
                    self.results_queue.put(
                        username + " has some Administrative Access: " + str(server.is_admin())
                    )
                elif access_type == "build":
                    self.results_queue.put(
                        username + " can Create Job: " + str(server.can_create_job())
                    )
                elif access_type == "read":
                    self.results_queue.put(
                        username + " can View Jenkins: " + str(server.can_read_jenkins())
                    )
                elif access_type == "scriptler":
                    if server.can_access_scriptler():
                        self.results_queue.put(username + " can Access Scriptler: True")
                    else:
                        self.results_queue.put(None)

            except jenkinslib.JenkinsException as ex:
                error = True

                if "[403]" in str(ex).split("\n")[0]:
                    self.logging.error("%s authentication failed or no access", username)
                else:
                    self.logging.error(
                        "Unable to access Jenkins at: %s With User: %s For Reason:\n\t%s"
                        % (
                            (
                                self.server_url.netloc
                                if len(self.server_url.netloc) > 0
                                else self.args.server
                            ),
                            username,
                            str(ex).split("\n")[0],
                        )
                    )

            except (req_exc.SSLError, req_exc.ConnectionError):
                error = True

                self.logging.error(
                    "Unable to connect to: "
                    + (
                        self.server_url.netloc
                        if len(self.server_url.netloc) > 0
                        else self.args.server
                    )
                )

            except Exception:
                error = True
                self.logging.exception("")

            self.jobs_queue.task_done()

        if error:  # So we have consistent exit codes on major error
            exit(1)


class AccessCheckParser:
    def cmd_AccessCheck(self):
        """Handles parsing of AccessCheck Subcommand arguments"""

        self._create_contextual_parser(
            "AccessCheck", "Get Users Rough Level of Access on Jenkins Server"
        )
        self._add_common_arg_parsers(allows_threading=True, allows_multiple_creds=True)

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_thread_number(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return self._handle_authentication(args)
