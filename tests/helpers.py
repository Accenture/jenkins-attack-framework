import multiprocessing
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO

from libs.JAF.BaseCommandLineParser import BaseCommandLineParser

from .configuration import (
    server,
    user_admin,
    user_bad,
    user_noaccess,
    user_normal,
    user_read_job_access,
    user_read_no_job_access,
)


class RemoteFeedbackTester:
    def __init__(self, port, timeout):
        self.port = port
        self.timeout = timeout

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def get_script(self, job_type):
        if job_type == "python":
            return "python -c \"import socket; sock = socket.create_connection(('{}', 12345)); sock.sendall(b'Test'); sock.close()\"".format(
                self.get_ip()
            )
        elif job_type == "groovy":
            return "def s = new Socket('{}', 12345); s.close()".format(self.get_ip())

    def got_connect_back(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.bind(("0.0.0.0", self.port))
            sock.listen(1)
            connection, client_address = sock.accept()
            connection.close()

            return True
        except socket.timeout:
            return False


class HijackOutput:
    def __enter__(self):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        sys.stdout = StringIO()
        sys.stderr = StringIO()
        return self

    def read(self):
        if sys.stdout is not sys.stderr:
            return sys.stdout.getvalue() + sys.stderr.getvalue()
        else:
            return sys.stdout.getvalue()

    def __exit__(self, type, value, traceback):
        sys.stderr = self.old_stderr
        sys.stdout = self.old_stdout


class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        return f"<html><body><h1>{message}</h1></body></html>".encode("utf8")

    def do_GET(self):
        self._set_headers()
        self.wfile.write(self._html("hi!"))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        self._set_headers()
        self.wfile.write(self._html("POST!"))

    def log_message(*args):
        # suppress output
        pass


class DummyWebServer:
    def start_webserver(self):
        self._server = multiprocessing.Process(target=self._start_webserver)
        self._server.start()

    def stop_webserver(self):
        self._server.terminate()

    def _start_webserver(self):
        with HTTPServer(("127.0.0.1", 59322), Server) as httpd:
            httpd.serve_forever()

    def __enter__(self):
        self.start_webserver()
        return self

    def __exit__(self, type, value, traceback):
        self.stop_webserver()


class TestFramework:
    def basic_test_harness(self, cmdline_args, output_regexs=[], expected_exit_code=0):
        sys.argv = cmdline_args

        try:
            classes = [BaseCommandLineParser]

            if self.TestParserClass:
                classes.append(self.TestParserClass)

            with HijackOutput() as f:
                command_line_parser = type("CommandLineParser", tuple(classes), {})()
                args = command_line_parser.parse()

                if not self.TestClass:
                    result = f.read()
                    for output_regex in output_regexs:
                        self.assertRegex(result, output_regex)

            if self.TestClass:
                with HijackOutput() as f:
                    self.TestClass(args)

                    result = f.read()
                    for output_regex in output_regexs:
                        self.assertRegex(result, output_regex)

        except SystemExit as ex:
            self.assertEqual(ex.code, expected_exit_code)
