"""
Defines EVM tools for use in the Ethereum specification.
"""

import argparse

from .t8n import T8N, t8n_arguments

# TODO: Add verbose description
DESCRIPTION = """
This is the EVM tool for execution specs.
You can use this to run the following tools:
    1. t8n: A stateless state transition utility.
"""

parser = argparse.ArgumentParser(
    description=DESCRIPTION,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)


# Add options to the t8n tool
subparsers = parser.add_subparsers(dest="evm_tool")


def main() -> int:
    """Run the tools based on the given options."""
    t8n_arguments(subparsers)
    options = parser.parse_args()
    if options.evm_tool == "t8n":
        t8n_tool = T8N(options)
        return t8n_tool.run()
    else:
        # TODO: Add support for b11r tool
        parser.print_help()
        return 0
