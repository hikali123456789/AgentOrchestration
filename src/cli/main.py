"""CLI entry point for the agent orchestrator."""

import argparse
import sys

from src.common.config import Config
from src.common.logging import configure_logging


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def non_negative_int(value: str) -> int:
    """Argparse type for non-negative integers."""
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: '{value}'")
    if ivalue < 0:
        raise argparse.ArgumentTypeError(f"value must be non-negative, got: {ivalue}")
    return ivalue


def handle_init(args) -> int:
    """Handle the init command. Returns exit code."""
    print(f"Initializing project: {args.name}")
    return EXIT_SUCCESS


def handle_deploy(args) -> int:
    """Handle the deploy command. Returns exit code."""
    print(f"Deploying agent from manifest: {args.manifest}")
    return EXIT_SUCCESS


def handle_status(args) -> int:
    """Handle the status command. Returns exit code."""
    print("Checking agent status...")
    return EXIT_SUCCESS


def handle_logs(args) -> int:
    """Handle the logs command. Returns exit code."""
    print(f"Fetching logs for agent: {args.agent_id}")
    return EXIT_SUCCESS


COMMAND_HANDLERS = {
    "init": handle_init,
    "deploy": handle_deploy,
    "status": handle_status,
    "logs": handle_logs,
}


def cli() -> int:
    """Run the CLI. Returns exit code."""
    parser = argparse.ArgumentParser(description="Agent Orchestrator CLI")
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", help="Project name")

    deploy_parser = subparsers.add_parser("deploy", help="Deploy an agent")
    deploy_parser.add_argument("manifest", help="Path to agent manifest file")

    status_parser = subparsers.add_parser("status", help="Show agent status")
    status_parser.add_argument("--watch", "-w", action="store_true", help="Watch mode")

    logs_parser = subparsers.add_parser("logs", help="View agent logs")
    logs_parser.add_argument("agent_id", help="Agent ID")
    logs_parser.add_argument("--tail", "-t", type=non_negative_int, default=50, help="Number of lines (must be non-negative)")

    args = parser.parse_args()

    if args.verbose:
        configure_logging("DEBUG")
    else:
        configure_logging("INFO")

    handler = COMMAND_HANDLERS.get(args.command)
    if handler is None:
        parser.print_help()
        return EXIT_FAILURE

    return handler(args)


if __name__ == "__main__":
    sys.exit(cli())