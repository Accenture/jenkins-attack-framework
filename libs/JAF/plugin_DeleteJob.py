import requests.exceptions as req_exc

from libs import jenkinslib

from .BasePlugin import BasePlugin, HijackStdOut


class NonCriticalException(Exception):
    pass


class DeleteJob(BasePlugin):
    """Class for managing DeleteJob SubCommand"""

    def __init__(self, args):
        super().__init__(args)

        cred = self.args.credentials[0]
        server = self._get_jenkins_server(cred)

        try:
            server.delete_job(self.args.task_name)

            print("Successfully deleted the job.")
            return
        except (
            jenkinslib.JenkinsException,
            req_exc.SSLError,
            req_exc.ConnectionError,
            req_exc.HTTPError,
        ):
            with HijackStdOut():
                print(
                    "WARNING: Unable to delete the job, attempting secondary clean-up.  You should double check."
                )

        # We were unable to delete the the task, so we need to do secondary clean-up as best we can:
        # First we delete all console output and run history:
        try:
            server.delete_all_job_builds(self.args.task_name)
        except (
            jenkinslib.JenkinsException,
            req_exc.SSLError,
            req_exc.ConnectionError,
            req_exc.HTTPError,
        ):
            print(
                "WARNING: Unable to clean-up console output.  You should definitely try to do this yourself."
            )

        # Second, overwrite the job with an empty job:
        try:
            server.reconfig_job(
                self.args.task_name, "<?xml version='1.1' encoding='UTF-8'?><project></project>"
            )
        except (
            jenkinslib.JenkinsException,
            req_exc.SSLError,
            req_exc.ConnectionError,
            req_exc.HTTPError,
        ):
            print(
                "WARNING: Unable to wipeout job to hide the evidence.  You should definitely try to do this yourself."
            )

        # Third, attempt to disable the job:
        try:
            server.disable_job(self.args.task_name)
        except (
            jenkinslib.JenkinsException,
            req_exc.SSLError,
            req_exc.ConnectionError,
            req_exc.HTTPError,
        ):
            print("WARNING: Unable to disable job.  You should definitely try to do this yourself.")

        exit(1)


class DeleteJobParser:
    def cmd_DeleteJob(self):
        """Handles parsing of DeleteJob Subcommand arguments"""

        self._create_contextual_parser("DeleteJob", "Delete Jenkins Jobs")
        self._add_common_arg_parsers()

        self.parser.add_argument(
            metavar="<Task Name>", help="Task to Delete", action="store", dest="task_name"
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)

        return_data = self._handle_authentication(args)

        return return_data
