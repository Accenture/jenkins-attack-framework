#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2010, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Authors:
# Ken Conley <kwc@willowgarage.com>
# James Page <james.page@canonical.com>
# Tully Foote <tfoote@willowgarage.com>
# Matthew Gertner <matthew.gertner@gmail.com>
#
# Originally based on: https://github.com/ceph/python-jenkins
#
# Heavily Modified by Shelby Spencer
"""
.. module:: jenkins
    :platform: Unix, Windows
    :synopsis: Python API to interact with Jenkins
    :noindex:

See examples at :doc:`examples`
"""

import json
import os
import re
import socket
import sys
import threading
import warnings
from http.client import BadStatusLine
from multiprocessing import Process
from urllib.error import URLError
from urllib.parse import quote, urlencode, urljoin

import requests
import requests.exceptions as req_exc
from bs4 import BeautifulSoup
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from libs import quik

try:
    import requests_kerberos
except ImportError:
    requests_kerberos = None

if sys.version_info < (2, 7, 0):
    warnings.warn("Support for python 2.6 is deprecated and will be removed.")

DEFAULT_HEADERS = {"Content-Type": "text/xml; charset=utf-8"}

# REST Endpoints
INFO = "api/json"
CRUMB_URL = "crumbIssuer/api/json"
JOBS_QUERY = "?tree=%s"
JOBS_QUERY_TREE = "jobs[url,color,name,%s]"
JOB_INFO = "%(folder_url)sjob/%(short_name)s/api/json?depth=%(depth)s"
JOB_NAME = "%(folder_url)sjob/%(short_name)s/api/json?tree=name"
ALL_BUILDS = "%(folder_url)sjob/%(short_name)s/api/json?tree=allBuilds[number,url]"
CREATE_JOB = "%(folder_url)screateItem?name=%(short_name)s"
CONFIG_JOB = "%(folder_url)sjob/%(short_name)s/config.xml"
BUILD_JOB = "%(folder_url)sjob/%(short_name)s/build"
BUILD_WITH_PARAMS_JOB = "%(folder_url)sjob/%(short_name)s/buildWithParameters"
BUILD_INFO = "%(folder_url)sjob/%(short_name)s/%(number)s/api/json?depth=%(depth)s"
STOP_BUILD = "%(folder_url)sjob/%(short_name)s/%(number)s/stop"
DELETE_JOB = "%(folder_url)sjob/%(short_name)s/doDelete"
DISABLE_JOB = "%(folder_url)sjob/%(short_name)s/disable"
DELETE_BUILD = "%(folder_url)sjob/%(short_name)s/%(number)s/doDelete"
GET_CREDENTIAL_LIST = "%(folder_url)sjob/%(short_name)s/descriptorByName/%(credential_provider)s/fillCredentialsIdItems"
GET_API_TOKEN_LIST = "user/%(user)s/configure"
CREATE_API_TOKEN = (
    "user/%(user)s/descriptorByName/jenkins.security.ApiTokenProperty/generateNewToken"
)
DELETE_API_TOKEN = "user/%(user)s/descriptorByName/jenkins.security.ApiTokenProperty/revoke"
BUILD_CONSOLE_OUTPUT = "%(folder_url)s%(number)s/consoleText"
SCRIPT_URL = "%(node)sscriptText"
WHOAMI_URL = "whoAmI/api/json"
NODE_LIST = "computer/api/json?depth=%(depth)s"
NODE_RAW = "computer/?depth=%(depth)s"
NODE_INFO = "computer/%(name)s/api/json?depth=%(depth)s"


class JenkinsException(Exception):
    """General exception type for jenkins-API-related failures."""


class NotFoundException(JenkinsException):
    """A special exception to call out the case of receiving a 404."""


class EmptyResponseException(JenkinsException):
    """A special exception to call out the case receiving an empty response."""


class BadHTTPException(JenkinsException):
    """A special exception to call out the case of a broken HTTP response."""


class TimeoutException(JenkinsException):
    """A special exception to call out in the case of a socket timeout."""


class WrappedSession(requests.Session):
    """A wrapper for requests.Session to override 'verify' property, ignoring REQUESTS_CA_BUNDLE environment variable.

    This is a workaround for https://github.com/kennethreitz/requests/issues/3829 (will be fixed in requests 3.0.0)
    """

    def merge_environment_settings(self, url, proxies, stream, verify, *args, **kwargs):
        if self.verify is False:
            verify = False

        return super(WrappedSession, self).merge_environment_settings(
            url, proxies, stream, verify, *args, **kwargs
        )


class Jenkins(object):
    """Main Class for Jenkins Server Request Management"""

    _timeout_warning_issued = False

    # Hold root url page result for permission checks to save requests.
    _cache_result = None
    _cache_status = None
    username = None

    _thread_lock = threading.Lock()

    def __init__(
        self,
        url,
        username=None,
        password=None,
        cookie=None,
        crumb=None,
        authheader=None,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        headers={},
    ):
        """Create handle to Jenkins instance.

        All methods will raise :class:`JenkinsException` on failure.

        :param url: URL of Jenkins server, ``str``
        :param username: Server username, ``str``
        :param password: Server password, ``str``
        :param timeout: Server connection timeout in secs (default: not set), ``int``
        """
        if url[-1] == "/":
            self.server = url
        else:
            self.server = url + "/"

        self.auth = None
        self.crumb = None

        if cookie:
            headers["Cookie"] = cookie
            self._auth_resolved = True

        if crumb:
            crumb = crumb.split("=")
            self.crumb = {
                "_class": "hudson.security.csrf.DefaultCrumbIssuer",
                "crumb": "=".join(crumb[1:]),
                "crumbRequestField": crumb[0],
            }

            headers[self.crumb["crumbRequestField"]] = self.crumb["crumb"]

        if authheader:
            headers["Authorization"] = authheader
            self._auth_resolved = True
        else:
            if username is not None and password is not None:
                self.username = username
                self._auth_resolved = False
                self._auths = [
                    (
                        "basic",
                        requests.auth.HTTPBasicAuth(
                            username.encode("utf-8"), password.encode("utf-8")
                        ),
                    )
                ]
            else:
                self._auth_resolved = False
                self._auths = [("anonymous", None)]

            if requests_kerberos is not None:
                self._auths.append(("kerberos", requests_kerberos.HTTPKerberosAuth()))

        self.timeout = timeout
        self._session = WrappedSession()

        for key in headers:
            self._session.headers[key] = headers[key]

        # Disable TLS Errors
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self._session.verify = False

    def _get_encoded_params(self, params):
        for k, v in params.items():
            if k in [
                "name",
                "msg",
                "short_name",
                "from_short_name",
                "to_short_name",
                "folder_url",
                "from_folder_url",
                "to_folder_url",
            ]:
                params[k] = quote(v.encode("utf8"))
        return params

    def _build_url(self, format_spec, variables=None):

        if variables:
            url_path = format_spec % self._get_encoded_params(variables)
        else:
            url_path = format_spec

        return str(urljoin(self.server, url_path))

    def maybe_add_crumb(self, req):
        # We don't know yet whether we need a crumb
        if self.crumb is None:
            try:
                response = self.jenkins_open(
                    requests.Request("GET", self._build_url(CRUMB_URL)), add_crumb=False
                )
                if not response:
                    raise EmptyResponseException("Empty response for crumb")
            except (NotFoundException, EmptyResponseException):
                self.crumb = False
            except JenkinsException:
                pass
            else:
                try:
                    self.crumb = json.loads(response)
                except json.JSONDecodeError:
                    raise JenkinsException(
                        "Unexpected Response from Server.  Is this really a Jenkins server?"
                    )

        if self.crumb:
            req.headers[self.crumb["crumbRequestField"]] = self.crumb["crumb"]

    def _maybe_add_auth(self):

        if self._auth_resolved:
            return

        if len(self._auths) == 1:
            # If we only have one auth mechanism specified, just require it
            self._session.auth = self._auths[0][1]
        else:
            # Attempt the list of auth mechanisms and keep the first that works
            # otherwise default to the first one in the list (last popped).
            # This is a hack to allow the transparent use of kerberos to work
            # in future, we should require explicit request to use kerberos
            failures = []
            for name, auth in reversed(self._auths):
                try:
                    self.jenkins_open(
                        requests.Request("GET", self._build_url(INFO), auth=auth),
                        add_crumb=False,
                        resolve_auth=False,
                    )
                    self._session.auth = auth
                    break
                except TimeoutException:
                    raise
                except Exception as exc:
                    # assume authentication failure
                    failures.append("auth(%s) %s" % (name, exc))
                    continue
            else:
                raise JenkinsException(
                    "Unable to authenticate with any scheme:\n%s" % "\n".join(failures)
                )

        self._auth_resolved = True
        self.auth = self._session.auth

    def _response_handler(self, response):
        """Handle response objects"""

        # raise exceptions if occurred
        response.raise_for_status()

        # Response objects will automatically return unicode encoded
        # when accessing .text property
        return response

    def _request(self, req):

        r = self._session.prepare_request(req)
        # requests.Session.send() does not honor env settings by design
        # see https://github.com/requests/requests/issues/2807
        _settings = self._session.merge_environment_settings(
            r.url, {}, None, self._session.verify, None
        )
        _settings["timeout"] = self.timeout

        """
        This is an ugly hack because calling consoleText on build without
        any builds, in some versions of Jenkins will result in an infinite
        redirect. Just preventing redirects on this URL is more efficient
        than checking for a build first.
        """

        if r.url.endswith("consoleText"):
            _settings["allow_redirects"] = False

        """
        End of ugly hack to prevent infinite redirect.
        """

        return self._session.send(r, **_settings)

    def jenkins_open(self, req, add_crumb=True, resolve_auth=True):
        """Return the HTTP response body from a ``requests.Request``.

        :returns: ``str``
        """
        return self.jenkins_request(req, add_crumb, resolve_auth).text

    def jenkins_request(self, req, add_crumb=True, resolve_auth=True):
        """Utility routine for opening an HTTP request to a Jenkins server.

        :param req: A ``requests.Request`` to submit.
        :param add_crumb: If True, try to add a crumb header to this ``req``
                          before submitting. Defaults to ``True``.
        :param resolve_auth: If True, maybe add authentication. Defaults to
                             ``True``.
        :returns: A ``requests.Response`` object.
        """

        try:
            if resolve_auth:
                self._maybe_add_auth()
            if add_crumb:
                self.maybe_add_crumb(req)

            return self._response_handler(self._request(req))

        except req_exc.HTTPError as e:
            # Jenkins's funky authentication means its nigh impossible to
            # distinguish errors.
            if e.response.status_code in [401, 403, 500]:
                msg = "Error in request. " + "Possibly authentication failed [%s]: %s" % (
                    e.response.status_code,
                    e.response.reason,
                )
                if e.response.text:
                    msg += "\n" + e.response.text
                raise JenkinsException(msg)
            elif e.response.status_code == 404:
                raise NotFoundException("Requested item could not be found")
            else:
                raise
        except req_exc.Timeout as e:
            raise TimeoutException("Error in request: %s" % (e))
        except URLError as e:
            # python 2.6 compatibility to ensure same exception raised
            # since URLError wraps a socket timeout on python 2.6.
            if str(e.reason) == "timed out":
                raise TimeoutException("Error in request: %s" % (e.reason))
            raise JenkinsException("Error in request: %s" % (e.reason))

    def get_info(self, item="", query=None):
        """Get information on this Master or item on Master.

        This information includes job list and view information and can be
        used to retreive information on items such as job folders.

        :param item: item to get information about on this Master
        :param query: xpath to extract information about on this Master
        :returns: dictionary of information about Master or item, ``dict``

        Example::

            >>> info = server.get_info()
            >>> jobs = info['jobs']
            >>> print(jobs[0])
            {u'url': u'http://your_url_here/job/my_job/', u'color': u'blue',
            u'name': u'my_job'}

        """

        url = "/".join((item, INFO)).lstrip("/")
        url = quote(url)
        if query:
            url += query
        try:
            return json.loads(self.jenkins_open(requests.Request("GET", self._build_url(url))))
        except (req_exc.HTTPError, BadStatusLine):
            raise BadHTTPException("Error communicating with server[%s]" % self.server)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for server[%s]" % self.server)

    def get_all_jobs(self, folder_depth=None, folder_depth_per_request=10):
        """Get list of all jobs recursively to the given folder depth.

        Each job is a dictionary with 'name', 'url', 'color' and 'fullname'
        keys.

        :param folder_depth: Number of levels to search, ``int``. By default
            None, which will search all levels. 0 limits to toplevel.
        :param folder_depth_per_request: Number of levels to fetch at once,
            ``int``. By default 10, which is usually enough to fetch all jobs
            using a single request and still easily fits into an HTTP request.
        :returns: list of jobs, ``[ { str: str} ]``

        .. note::

            On instances with many folders it would not be efficient to fetch
            each folder separately, hence `folder_depth_per_request` levels
            are fetched at once using the ``tree`` query parameter::

                ?tree=jobs[url,color,name,jobs[...,jobs[...,jobs[...,jobs]]]]

            If there are more folder levels than the query asks for, Jenkins
            returns empty [#]_ objects at the deepest level::

                {"name": "folder", "url": "...", "jobs": [{}, {}, ...]}

            This makes it possible to detect when additional requests are
            needed.

            .. [#] Actually recent Jenkins includes a ``_class`` field
                everywhere, but it's missing the requested fields.
        """
        jobs_query = "jobs"
        for _ in range(folder_depth_per_request):
            jobs_query = JOBS_QUERY_TREE % jobs_query
        jobs_query = JOBS_QUERY % jobs_query

        jobs_list = []
        jobs = [(0, [], self.get_info(query=jobs_query)["jobs"])]
        for lvl, root, lvl_jobs in jobs:
            if not isinstance(lvl_jobs, list):
                lvl_jobs = [lvl_jobs]
            for job in lvl_jobs:
                path = root + [job["name"]]
                # insert fullname info if it doesn't exist to
                # allow callers to easily reference unambiguously
                if "fullname" not in job:
                    job["fullname"] = "/".join(path)
                jobs_list.append(job)
                if "jobs" in job and isinstance(job["jobs"], list):  # folder
                    if folder_depth is None or lvl < folder_depth:
                        children = job["jobs"]
                        # once folder_depth_per_request is reached, Jenkins
                        # returns empty objects
                        if any("url" not in child for child in job["jobs"]):
                            url_path = "".join(["/job/" + p for p in path])
                            children = self.get_info(url_path, query=jobs_query)["jobs"]
                        jobs.append((lvl + 1, path, children))
        return jobs_list

    def get_nodes(self, depth=0):
        """Get a list of nodes connected to the Master

        Each node is a dict with keys 'name' and 'offline'

        :returns: List of nodes, ``[ { str: str, str: bool} ]``
        """
        try:
            nodes_data = json.loads(
                self.jenkins_open(requests.Request("GET", self._build_url(NODE_LIST, locals())))
            )

            raw_nodes = self.jenkins_open(
                requests.Request("GET", self._build_url(NODE_RAW, locals()))
            )

            soup = BeautifulSoup(raw_nodes, "html.parser")

            return_data = []

            for node in nodes_data["computer"]:
                """
                Janky OS detection because for some reason hudson.node_monitors.ArchitectureMonitor isn't available via API if you aren't an admin
                even though you can see this info as any authenticated user via the /computer url.

                For now, we assume that all nodes are shown and no ajax paging occurs like on other pages (/users).  This appears to be the case. 
                If ajax paging did occur, it would actually make this less jank because we could use that feature to get the info in a nice JSON 
                format.
                """

                architecture = None

                try:
                    architecture = (
                        soup.find_all("tr", id="node_" + node["displayName"])[0]
                        .find_all("td")[2]
                        .string
                    )
                except Exception:
                    pass

                return_data.append(
                    {
                        "name": node["displayName"],
                        "offline": node["offline"],
                        "architecture": architecture,
                    }
                )

            return return_data

        except (req_exc.HTTPError, BadStatusLine):
            raise BadHTTPException("Error communicating with server[%s]" % self.server)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for server[%s]" % self.server)

    def get_node_info(self, name, depth=0):
        """Get node information dictionary

        :param name: Node name, ``str``
        :param depth: JSON depth, ``int``
        :returns: Dictionary of node info, ``dict``
        """
        try:
            response = self.jenkins_open(
                requests.Request("GET", self._build_url(NODE_INFO, locals()))
            )
            if response:
                return json.loads(response)
            else:
                raise JenkinsException("node[%s] does not exist" % name)
        except (req_exc.HTTPError, NotFoundException):
            raise JenkinsException("node[%s] does not exist" % name)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for node[%s]" % name)

    def _get_job_folder(self, name):
        """Return the name and folder (see cloudbees plugin).

        This is a method to support cloudbees folder plugin.
        Url request should take into account folder path when the job name specify it
        (ex.: 'folder/job')

        :param name: Job name, ``str``
        :returns: Tuple [ 'folder path for Request', 'Name of job without folder path' ]
        """

        a_path = name.split("/")
        short_name = a_path[-1]
        folder_url = ("job/" + "/job/".join(a_path[:-1]) + "/") if len(a_path) > 1 else ""

        return folder_url, short_name

    def basic_access_check(self):
        with self._thread_lock:
            if self._cache_result is None:
                try:
                    self._cache_result = self.jenkins_open(requests.Request("GET", self.server))

                    if "jenkins" not in self._cache_result.lower():
                        self._cache_status = 500
                    else:
                        self._cache_status = 200
                except JenkinsException as ex:
                    if "[401]" in str(ex).split("\n")[0]:
                        self._cache_status = 401
                    else:
                        self._cache_status = 500
                except (req_exc.SSLError, req_exc.ConnectionError):
                    self._cache_status = 500

                except Exception:
                    self._cache_status = 500

        return self._cache_status

    def can_read_jenkins(self):
        result = self.basic_access_check()

        if result == 200 and self._cache_result and self._cache_result != "":
            return True

        return False

    def is_admin(self):
        result = self.basic_access_check()

        if result == 200 and self._cache_result and self._cache_result != "":
            if 'href="/manage"' in self._cache_result:
                return True

        return False

    def can_create_job(self):
        result = self.basic_access_check()

        if result == 200 and self._cache_result and self._cache_result != "":
            if 'href="/view/all/newJob"' in self._cache_result:
                return True

        return False

    def can_access_scriptler(self):
        result = self.basic_access_check()

        if result == 200 and self._cache_result and self._cache_result != "":
            if 'href="/scriptler"' in self._cache_result:
                return True

        return False

    def can_access_script_console(self):
        if not self.is_admin():
            return False

        try:
            self.jenkins_open(requests.Request("GET", self._build_url("/script")))

            return True
        except Exception:
            return False

    def get_build_console_output(self, folder_url, number):
        """Get build console text.

        :param name: Job name, ``str``
        :param number: Build number, ``int``
        :returns: Build console output,  ``str``
        """
        try:
            response = self.jenkins_open(
                requests.Request("GET", self._build_url(BUILD_CONSOLE_OUTPUT, locals()))
            )
            if response:
                return response
            else:
                raise JenkinsException("job[%s] number[%d] does not exist" % (folder_url, number))
        except (req_exc.HTTPError, NotFoundException):
            raise JenkinsException("job[%s] number[%s] does not exist" % (folder_url, number))

    def get_build_info(self, name, number, depth=0):
        """Get build information dictionary.
        :param name: Job name, ``str``
        :param name: Build number, ``int``
        :param depth: JSON depth, ``int``
        :returns: dictionary of build information, ``dict``
        Example::
            >>> next_build_number = server.get_job_info('build_name')['nextBuildNumber']
            >>> output = server.build_job('build_name')
            >>> from time import sleep; sleep(10)
            >>> build_info = server.get_build_info('build_name', next_build_number)
            >>> print(build_info)
            {u'building': False, u'changeSet': {u'items': [{u'date': u'2011-12-19T18:01:52.540557Z', u'msg': u'test', u'revision': 66, u'user': u'unknown', u'paths': [{u'editType': u'edit', u'file': u'/branches/demo/index.html'}]}], u'kind': u'svn', u'revisions': [{u'module': u'http://eaas-svn01.i3.level3.com/eaas', u'revision': 66}]}, u'builtOn': u'', u'description': None, u'artifacts': [{u'relativePath': u'dist/eaas-87-2011-12-19_18-01-57.war', u'displayPath': u'eaas-87-2011-12-19_18-01-57.war', u'fileName': u'eaas-87-2011-12-19_18-01-57.war'}, {u'relativePath': u'dist/eaas-87-2011-12-19_18-01-57.war.zip', u'displayPath': u'eaas-87-2011-12-19_18-01-57.war.zip', u'fileName': u'eaas-87-2011-12-19_18-01-57.war.zip'}], u'timestamp': 1324317717000, u'number': 87, u'actions': [{u'parameters': [{u'name': u'SERVICE_NAME', u'value': u'eaas'}, {u'name': u'PROJECT_NAME', u'value': u'demo'}]}, {u'causes': [{u'userName': u'anonymous', u'shortDescription': u'Started by user anonymous'}]}, {}, {}, {}], u'id': u'2011-12-19_18-01-57', u'keepLog': False, u'url': u'http://eaas-jenkins01.i3.level3.com:9080/job/build_war/87/', u'culprits': [{u'absoluteUrl': u'http://eaas-jenkins01.i3.level3.com:9080/user/unknown', u'fullName': u'unknown'}], u'result': u'SUCCESS', u'duration': 8826, u'fullDisplayName': u'build_war #87'}
        """
        folder_url, short_name = self._get_job_folder(name)
        try:
            response = self.jenkins_open(
                requests.Request("GET", self._build_url(BUILD_INFO, locals()))
            )
            if response:
                return json.loads(response)
            else:
                raise JenkinsException("job[%s] number[%s] does not exist" % (name, number))
        except req_exc.HTTPError:
            raise JenkinsException("job[%s] number[%s] does not exist" % (name, number))
        except ValueError:
            raise JenkinsException(
                "Could not parse JSON info for job[%s] number[%s]" % (name, number)
            )

    def delete_build(self, name, number):
        """Delete a Jenkins build.

        :param name: Name of Jenkins job, ``str``
        :param number: Jenkins build number for the job, ``int``
        """
        folder_url, short_name = self._get_job_folder(name)
        self.jenkins_open(requests.Request("POST", self._build_url(DELETE_BUILD, locals())))

    def delete_all_job_builds(self, name):
        """Attempt to delete all Jenkins builds for job

        :param name: Name of Jenkins job, ``str``
        """

        job_info = self.get_job_info(name)

        errors = False

        for build in job_info["builds"]:
            try:
                self.delete_build(name, build["number"])
            except JenkinsException:
                errors = True

        if errors:
            raise JenkinsException("One or more builds was not successfully deleted")

    def execute_script(self, script, wait=True, node=None):
        if not wait:
            Process(target=self.execute_script, args=(script, True), kwargs={"node": node}).start()
        else:
            try:
                if node:
                    node = "computer/{0}/".format(node)
                else:
                    node = ""

                return self.jenkins_open(
                    requests.Request(
                        "POST", self._build_url(SCRIPT_URL, locals()), data={"script": script}
                    )
                )
            except (req_exc.HTTPError, NotFoundException):
                raise JenkinsException("Something went wrong")

    def get_whoAmI(self):
        try:
            data = json.loads(
                self.jenkins_open(requests.Request("GET", self._build_url(WHOAMI_URL)))
            )
            del data["_class"]
            return data

        except (req_exc.HTTPError, NotFoundException):
            raise JenkinsException("Something went wrong")

    def job_exists(self, name):
        """Check whether a job exists

        :param name: Name of Jenkins job, ``str``
        :returns: ``True`` if Jenkins job exists
        """
        folder_url, short_name = self._get_job_folder(name)
        if self.get_job_name(name) == short_name:
            return True

    def get_job_name(self, name):
        """Return the name of a job using the API.

        That is roughly an identity method which can be used to quickly verify
        a job exists or is accessible without causing too much stress on the
        server side.

        :param name: Job name, ``str``
        :returns: Name of job or None
        """
        folder_url, short_name = self._get_job_folder(name)
        try:
            response = self.jenkins_open(
                requests.Request("GET", self._build_url(JOB_NAME, locals()))
            )
            actual = json.loads(response)["name"]
        except NotFoundException:
            return None
        except json.JSONDecodeError:
            raise JenkinsException(
                "Unexpected Response from Server. Are you sure this is a Jenkins Server?"
            )
        else:

            if actual != short_name:
                raise JenkinsException(
                    "Jenkins returned an unexpected job name %s " "(expected: %s)" % (actual, name)
                )
            return actual

    def get_job_info(self, name, depth=0, fetch_all_builds=False):
        """Get job information dictionary.

        :param name: Job name, ``str``
        :param depth: JSON depth, ``int``
        :param fetch_all_builds: If true, all builds will be retrieved
                                 from Jenkins. Otherwise, Jenkins will
                                 only return the most recent 100
                                 builds. This comes at the expense of
                                 an additional API call which may
                                 return significant amounts of
                                 data. ``bool``
        :returns: dictionary of job information
        """
        folder_url, short_name = self._get_job_folder(name)
        try:
            response = self.jenkins_open(
                requests.Request("GET", self._build_url(JOB_INFO, locals()))
            )
            if response:
                if fetch_all_builds:
                    return self._add_missing_builds(json.loads(response))
                else:
                    return json.loads(response)
            else:
                raise JenkinsException("job[%s] does not exist" % name)
        except (req_exc.HTTPError, NotFoundException):
            raise JenkinsException("job[%s] does not exist" % name)
        except ValueError:
            raise JenkinsException("Could not parse JSON info for job[%s]" % name)

    def create_job(self, name, config_xml):
        """Create a new Jenkins job
        :param name: Name of Jenkins job, ``str``
        :param config_xml: config file text, ``str``
        """
        folder_url, short_name = self._get_job_folder(name)
        if self.job_exists(name):
            raise JenkinsException("job[%s] already exists" % (name))

        try:
            result = self.jenkins_open(
                requests.Request(
                    "POST",
                    self._build_url(CREATE_JOB, locals()),
                    DEFAULT_HEADERS,
                    data=config_xml.encode("utf-8"),
                )
            )
        except NotFoundException:
            raise JenkinsException(
                "Cannot create job[%s] because folder " "for the job does not exist" % (name)
            )

        return True

    def stop_build(self, name, number):
        """Stop a running Jenkins build.
        :param name: Name of Jenkins job, ``str``
        :param number: Jenkins build number for the job, ``str``
        """
        folder_url, short_name = self._get_job_folder(name)
        return self.jenkins_open(requests.Request("POST", self._build_url(STOP_BUILD, locals())))

    def reconfig_job(self, name, config_xml):
        """Change configuration of existing Jenkins job.

        To create a new job, see :meth:`Jenkins.create_job`.

        :param name: Name of Jenkins job, ``str``
        :param config_xml: New XML configuration, ``str``
        """
        folder_url, short_name = self._get_job_folder(name)
        reconfig_url = self._build_url(CONFIG_JOB, locals())
        self.jenkins_open(
            requests.Request(
                "POST", reconfig_url, data=config_xml.encode("utf-8"), headers=DEFAULT_HEADERS
            )
        )

    def delete_job(self, name):
        """Delete Jenkins job permanently.

        :param name: Name of Jenkins job, ``str``
        """
        folder_url, short_name = self._get_job_folder(name)
        self.jenkins_open(requests.Request("POST", self._build_url(DELETE_JOB, locals())))

        if self.job_exists(name):
            raise JenkinsException("delete[%s] failed" % (name))

    def build_job_url(self, name, parameters=None, token=None):
        """Get URL to trigger build job.
        Authenticated setups may require configuring a token on the server
        side.
        :param parameters: parameters for job, or None., ``dict``
        :param token: (optional) token for building job, ``str``
        :returns: URL for building job
        """
        folder_url, short_name = self._get_job_folder(name)
        if parameters:
            if token:
                parameters["token"] = token
            return self._build_url(BUILD_WITH_PARAMS_JOB, locals()) + "?" + urlencode(parameters)
        elif token:
            return self._build_url(BUILD_JOB, locals()) + "?" + urlencode({"token": token})
        else:
            return self._build_url(BUILD_JOB, locals())

    def build_job(self, name, parameters=None, token=None):
        """Trigger build job.
        :param name: name of job
        :param parameters: parameters for job, or ``None``, ``dict``
        :param token: Jenkins API token
        """
        return self.jenkins_open(
            requests.Request("POST", self.build_job_url(name, parameters, token))
        )

    def disable_job(self, name):
        """Disable Jenkins job.

        To re-enable, call :meth:`Jenkins.enable_job`.

        :param name: Name of Jenkins job, ``str``
        """
        folder_url, short_name = self._get_job_folder(name)
        self.jenkins_open(requests.Request("POST", self._build_url(DISABLE_JOB, locals())))

    def list_credentials(self, name):
        """List accessible credentials on a Jenkins job
        :param name: Name of Jenkins job, ``str``
        """
        folder_url, short_name = self._get_job_folder(name)
        if not self.job_exists(name):
            raise JenkinsException("job[%s] does not exist" % (name))

        credentials = []

        credential_provider = "hudson.plugins.git.UserRemoteConfig"

        try:
            result = self.jenkins_open(
                requests.Request(
                    "POST",
                    self._build_url(GET_CREDENTIAL_LIST, locals()),
                    DEFAULT_HEADERS,
                    data="url=&credentialsId=",
                )
            )

        except NotFoundException:
            raise JenkinsException(
                "Cannot list credentials because job[%s] because does not exist" % (name)
            )

        try:
            for item in json.loads(result)["values"]:
                if "name" in item and "value" in item:
                    cred_type = None

                    if "/******" in item["name"]:
                        item["name"] = item["name"].replace("/******", "")
                        cred_type = "PASSWORD"
                    elif re.search(r" \(SSH Key\)$", item["name"]):
                        item["name"] = item["name"][:-10]
                        cred_type = "SSHKEY"

                    credentials.append(
                        {
                            "description": item["name"],
                            "id": item["value"],
                            "type": cred_type,
                            "provider": credential_provider,
                        }
                    )
                else:
                    raise Exception("Not Valid Credential")
        except Exception as ex:
            raise ex

        credential_provider = "org.jenkinsci.plugins.credentialsbinding.impl.StringBinding"

        try:
            result = self.jenkins_open(
                requests.Request(
                    "POST",
                    self._build_url(GET_CREDENTIAL_LIST, locals()),
                    DEFAULT_HEADERS,
                    data="url=&credentialsId=",
                )
            )

        except NotFoundException:
            raise JenkinsException(
                "Cannot list credentials because job[%s] because does not exist" % (name)
            )

        try:
            for item in json.loads(result)["values"]:
                if "name" in item and "value" in item:
                    cred_type = None

                    credentials.append(
                        {
                            "description": item["name"],
                            "id": item["value"],
                            "type": "SECRETTEXT",
                            "provider": credential_provider,
                        }
                    )
                else:
                    raise Exception("Not Valid Credential")
        except Exception as ex:
            raise ex

        credential_provider = "org.jenkinsci.plugins.credentialsbinding.impl.FileBinding"

        try:
            result = self.jenkins_open(
                requests.Request(
                    "POST",
                    self._build_url(GET_CREDENTIAL_LIST, locals()),
                    DEFAULT_HEADERS,
                    data="url=&credentialsId=",
                )
            )

        except NotFoundException:
            raise JenkinsException(
                "Cannot list credentials because job[%s] because does not exist" % (name)
            )

        try:
            for item in json.loads(result)["values"]:
                if "name" in item and "value" in item:
                    cred_type = None

                    credentials.append(
                        {
                            "description": item["name"],
                            "id": item["value"],
                            "type": "SECRETFILE",
                            "provider": credential_provider,
                        }
                    )
                else:
                    raise Exception("Not Valid Credential")
        except Exception as ex:
            raise ex

        return credentials

    def get_cookie_crumb(self):
        """Get Authenticated Jenkins Cookie For Testing Purposes"""

        cookies = self._session.cookies.get_dict()

        if len(cookies) == 0:
            self.get_whoAmI()

        cookies = self._session.cookies.get_dict()

        return_data = {"Cookie": None, "Crumb": None}

        for key in cookies:
            if key.startswith("JSESSIONID"):
                return_data["Cookie"] = "{0}={1}".format(key, cookies[key])
                break

        if self.crumb:
            return_data["Crumb"] = {self.crumb["crumbRequestField"]: self.crumb["crumb"]}

        return return_data

    def list_api_tokens(self, query_username=None):
        """List API Tokens

        :param name: Name of user to query tokens for, ``str``
        """

        tokens = []

        if query_username:
            if not self.can_access_script_console():
                raise JenkinsException('You must be able to access the "/script" console.')

            loader = quik.FileLoader(os.path.join("data", "groovy"))
            script_template = loader.load_template("list_api_tokens_for_user_template.groovy")

            result = self.execute_script(
                script_template.render(
                    {"command": query_username.replace("\\", "\\\\").replace('"', '\\"')}
                )
            ).strip()

            raw_tokens = re.split(r"\n\n", result, flags=re.M)

            for raw_token in raw_tokens:
                try:
                    lines = raw_token.split("\n")

                    token = {
                        "name": ": ".join(re.split(": ", lines[0])[1:]),
                        "creation_date": ": ".join(re.split(": ", lines[1])[1:]),
                        "uuid": ": ".join(re.split(": ", lines[2])[1:]),
                    }

                    tokens.append(token)
                except Exception:
                    pass
        else:
            if not self.username or len(self.username) == 0:
                user_details = self.get_whoAmI()

                if "name" in user_details:
                    self.username = user_details["name"]
                else:
                    raise JenkinsException(
                        "Could not get username, are you sure your credentials are valid?"
                    )

            user = self.username

            raw_tokens = self.jenkins_open(
                requests.Request("GET", self._build_url(GET_API_TOKEN_LIST, locals()))
            )

            soup = BeautifulSoup(raw_tokens, "html.parser")

            tokens_html = soup.find_all("div", {"name": "tokenStore"})

            for token_html in tokens_html:
                try:
                    token = {
                        "name": token_html.find("input", {"name": "tokenName"})["value"],
                        "creation_date": token_html.find("span", {"class": "token-creation"})[
                            "title"
                        ],
                        "uuid": token_html.find("input", {"name": "tokenUuid"})["value"],
                    }

                    tokens.append(token)
                except Exception:
                    pass

        return tokens

    def create_api_token(self, token_name=None, selected_username=None):
        """Creates API Token

        :param name: Name of API Token, ``str``
        :param name: Name of User to Add Token To, ``str``
        """

        if selected_username:
            if not self.can_access_script_console():
                raise JenkinsException('You must be able to access the "/script" console.')

            loader = quik.FileLoader(os.path.join("data", "groovy"))
            script_template = loader.load_template("create_api_token_for_user_template.groovy")

            if not token_name:
                token_name = ""

            result = self.execute_script(
                script_template.render(
                    {
                        "user": selected_username.replace("\\", "\\\\").replace('"', '\\"'),
                        "token": token_name.replace("\\", "\\\\").replace('"', '\\"'),
                    }
                )
            ).strip()

            if len(result) == 0:
                raise JenkinsException(
                    'Token Creation Failed.  Perhaps you don\'t have "/script" access?'
                )

            return result
        else:
            if not self.username or len(self.username) == 0:
                user_details = self.get_whoAmI()

                if "name" in user_details:
                    self.username = user_details["name"]
                else:
                    raise JenkinsException(
                        "Could not get username, are you sure your credentials are valid?"
                    )

            user = self.username

            result = self.jenkins_open(
                requests.Request(
                    "POST",
                    self._build_url(CREATE_API_TOKEN, locals()),
                    data={"newTokenName": token_name if token_name else ""},
                )
            )

            try:
                return json.loads(result)["data"]["tokenValue"]
            except Exception:
                raise JenkinsException(
                    "Server did not respond with a valid token. Something went wrong."
                )

    def delete_api_token(self, token_identifier, selected_username=None):
        """Deletes API Token

        :param name: Name of API Token or Token UUID, ``str``
        :param name: Name of User to Delete Token From, ``str``
        """

        if selected_username:
            # Permission checking and errors will be raised by list_api_tokens
            tokens = self.list_api_tokens(selected_username)

            filtered_tokens = [
                x for x in tokens if x["name"] == token_identifier or x["uuid"] == token_identifier
            ]

            if len(filtered_tokens) == 0:
                raise JenkinsException("No matching token found.")
            elif len(filtered_tokens) > 1:
                raise JenkinsException(
                    "Token Identifier matchs multiple tokens, pass UUID instead."
                )

            loader = quik.FileLoader(os.path.join("data", "groovy"))
            script_template = loader.load_template("delete_api_token_for_user_template.groovy")

            result = self.execute_script(
                script_template.render(
                    {
                        "user": selected_username.replace("\\", "\\\\").replace('"', '\\"'),
                        "token": filtered_tokens[0]["uuid"]
                        .replace("\\", "\\\\")
                        .replace('"', '\\"'),
                    }
                )
            ).strip()

            if result != "Success":
                raise JenkinsException(
                    'An error occurred. Perhaps you don\'t have "/script" access?'
                )
        else:
            tokens = self.list_api_tokens()

            # self.username will exist (if it didn't already) thanks to list_api_tokens
            user = self.username

            filtered_tokens = [
                x for x in tokens if x["name"] == token_identifier or x["uuid"] == token_identifier
            ]

            if len(filtered_tokens) == 0:
                raise JenkinsException("No matching token found.")
            elif len(filtered_tokens) > 1:
                raise JenkinsException(
                    "Token Identifier matchs multiple tokens, pass UUID instead."
                )

            result = self.jenkins_open(
                requests.Request(
                    "POST",
                    self._build_url(DELETE_API_TOKEN, locals()),
                    data={"tokenUuid": filtered_tokens[0]["uuid"]},
                )
            )
