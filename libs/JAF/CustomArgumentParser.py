import argparse
import re
import sys


class ArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        """
        Since we handle some positional arguments at the end of our arguments and some at the beginning we need 
        to do some hackery to make argparse play nicely with optional positional arguments at the end of our 
        arguments list. This solution is fragile, but sufficient for our needs. What we do, is check to see if 
        parse_known_args returns any "unknown args". If so, we shuffle arguments so that all the unknown args appear 
        at the front (after the command arg that should always be first). Then we try again. If we still get an 
        error, we throw the error just like argparse would, otherwise everything is golden.
        """

        args, argv = self.parse_known_args(args, namespace)

        new_argv = []

        if argv:
            new_argv = [x for x in sys.argv[1:] if x not in argv]

            for i in range(len(argv)):
                new_argv.insert(i + 1, argv[i])

            args, argv = self.parse_known_args(new_argv, namespace)

            if argv:
                msg = "unrecognized arguments: %s"
                self.error(msg % " ".join(argv))

        return args


class Formatter(argparse.HelpFormatter):
    """Argparse Formatter to override usage creation.
        Created to force argparse to respect positional order
        Also move [-h] option to more expected location"""

    # use defined argument order to display usage
    def _format_usage(self, usage, actions, groups, prefix):
        """Generates usage string, mostly stolen from argparse source"""

        if prefix is None:
            prefix = "usage: "

        # if usage is specified, use that
        if usage is not None:
            usage = usage % {"prog": self._prog}

        # if no optionals or positionals are available, usage is just prog
        elif usage is None and not actions:
            usage = "%(prog)s" % {"prog": self._prog}
        elif usage is None:
            prog = "%(prog)s" % {"prog": self._prog}

            # split optionals from positionals
            args = []

            for action in actions[1:]:
                args.append(action)

            args.insert(1, actions[0])  # Move [-h] to after subcommand

            # build full usage string
            action_usage = self._format_actions_usage(args, groups)

            usage = " ".join([s for s in [prog, action_usage] if s])

            # wrap the usage parts if it's too long
            text_width = self._width - self._current_indent
            if len(prefix) + len(usage) > text_width:

                # break usage into wrappable parts
                part_regexp = r"\(.*?\)+(?=\s|$)|" r"\[.*?\]+(?=\s|$)|" r"\S+"

                args_usage = self._format_actions_usage(args, groups)
                args_parts = re.findall(part_regexp, args_usage)

                # helper for wrapping lines
                def get_lines(parts, indent, prefix=None):
                    lines = []
                    line = []
                    if prefix is not None:
                        line_len = len(prefix) - 1
                    else:
                        line_len = len(indent) - 1
                    for part in parts:
                        if line_len + 1 + len(part) > text_width and line:
                            lines.append(indent + " ".join(line))
                            line = []
                            line_len = len(indent) - 1
                        line.append(part)
                        line_len += len(part) + 1
                    if line:
                        lines.append(indent + " ".join(line))
                    if prefix is not None:
                        lines[0] = lines[0][len(indent) :]
                    return lines

                # if prog is short, follow it with optionals or positionals
                if len(prefix) + len(prog) <= 0.75 * text_width:
                    indent = " " * (len(prefix) + len(prog) + 1)
                    if args_parts:
                        lines = get_lines([prog] + args_parts, indent, prefix)
                    else:
                        lines = [prog]

                # if prog is long, put it on its own line
                else:
                    indent = " " * len(prefix)
                    lines = get_lines(args_parts, indent)
                    if len(lines) > 1:
                        lines = []
                        lines.extend(get_lines(args_parts, indent))
                    lines = [prog] + lines

                # join lines into usage
                usage = "\n".join(lines) + "\n"

        return "%s%s\n\n" % (prefix, usage)
