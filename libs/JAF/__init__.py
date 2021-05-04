import glob
import importlib
import os
import sys

from .BaseCommandLineParser import BaseCommandLineParser


def JAF():
    """
    Primary JAF Function
    This function handles the dynamic plugin loading.
    Commandline Parsers are loaded as mixins to the BaseCommandLindParser class.
    Once parsing occurs, the correct Plugin Class is called that inherits from BasePlugin.
    """

    plugins = [BaseCommandLineParser]

    for plugin in glob.glob(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugin_*.py")
    ):
        plugin = (os.path.split(plugin)[1])[7:-3]

        try:
            module = importlib.import_module("libs.JAF.plugin_" + plugin)
            parser_class = getattr(module, plugin + "Parser")
            plugins.append(parser_class)
        except AttributeError as ex:
            sys.stderr.write("An error occurred loading plugin {0}:\n\t{1}\n".format(plugin, ex))
            exit(-1)

    command_line_parser = type("CommandLineParser", tuple(plugins), {})()
    args = command_line_parser.parse()

    try:
        module = importlib.import_module("libs.JAF.plugin_" + args.subcommand)
    except ModuleNotFoundError as ex:
        sys.stderr.write(
            "An error occurred loading plugin {0}:\n\t{1}\n".format(args.subcommand, ex)
        )
        exit(-1)

    return getattr(module, args.subcommand)(args)
