import argparse
import logging
import time
import colorlog
import sys
import os
from pathlib import Path
from watchdog.observers import Observer

# Adjust this if needed
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from modules.watchdog.plex_watchdog_event import PlexWatchdog
from modules.config import shared
from modules.plex.plex_agent import plex_agent_singleton

SCRIPT_START_TIME = time.time()

colorlog.basicConfig(
    format='{log_color}{levelname}:\t{message}',
    level=logging.INFO,
    style='{',
    stream=None,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'white',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red'
    }
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("watchdog").setLevel(logging.WARNING)


def get_args_from_cli() -> None:
    """
    Parses the command line arguments and stores them in shared.user_input.

    If --paths is not passed, we'll watch all library paths from Plex.
    """
    parser = argparse.ArgumentParser(
        prog="PlexNFSWatchdog",
        description="A utility to trigger Plex partial-scans on NFS configurations, on which inotify is not supported",
    )
    action_type = parser.add_mutually_exclusive_group(required=True)
    action_type.add_argument(
        "--scan", "-s", action='store_true',
        help="Manually triggers a partial-scan on the given folder paths"
    )
    action_type.add_argument(
        "--daemon", "-d", action='store_true',
        help="Starts a watchdog daemon to automatically trigger partial-scans on the given folder paths"
    )

    # Make paths optional via nargs='*'
    parser.add_argument(
        "--paths", "-p", action="store", nargs='*', required=False, default=None,
        help="A list of folder paths. If omitted, all Plex library folders are monitored."
    )
    parser.add_argument(
        "--host", "-H", action="store", help="The host of the Plex server",
        type=str, default="http://localhost:32400", required=False
    )
    parser.add_argument(
        "--token", "-t", action="store", help="The Plex server token",
        type=str, default=None, required=False
    )
    parser.add_argument(
        "--dry-run", action='store_true',
        help="Dry run mode, does not send any request for partial-scans"
    )
    parser.add_argument(
        "--interval", "-i", help="Interval in seconds between partial-scans",
        action="store", type=int, required=False, default=None
    )
    parser.add_argument(
        "--version", "-v", help="Prints the version of the application",
        action='version', version=f"%(prog)s {shared.VERSION}"
    )
    parser.add_argument(
        "--listeners", "-l", action="store", nargs='+', required=False,
        help="List of events to watch", type=str,
        choices=shared.listeners_type, default=None
    )

    shared.user_input = parser.parse_args()

    # Validate daemon-related args
    if shared.user_input.daemon and (shared.user_input.interval is None or shared.user_input.interval <= 0):
        parser.error("--interval is required when using --daemon. It must be a positive integer.")
    if shared.user_input.daemon and shared.user_input.listeners is None:
        parser.error("--listeners is required when using --daemon. Must be a valid event type.")

    # If user provided --paths, validate them; else None
    if shared.user_input.paths:
        validated_paths = set()
        for raw in shared.user_input.paths:
            p = Path(raw)
            if not p.exists() or not p.is_dir():
                parser.error(f"{p.resolve()} does not exist or is not a folder!")
            validated_paths.add(p)
        shared.user_input.paths = validated_paths
    else:
        shared.user_input.paths = None

    # Ensure we have a Plex token or a cached config
    if shared.user_input.token is None and not plex_agent_singleton.is_cache_loaded():
        parser.error("Plex host and token are missing!")


def main() -> None:
    # If we already have a cached Plex config, load it
    if shared.cache_path.exists():
        plex_agent_singleton.load_config_cache()

    # Parse CLI arguments
    get_args_from_cli()

    # Let the agent know script start time if needed
    plex_agent_singleton.set_script_start_time(SCRIPT_START_TIME)

    # Connect to Plex
    plex_agent_singleton.connect()

    # If no paths were specified, default to all library folder paths
    if shared.user_input.paths is None:
        library_paths = plex_agent_singleton.get_all_library_paths()
        if not library_paths:
            logging.error("No library paths found in Plex. Exiting.")
            sys.exit(-1)
        shared.user_input.paths = library_paths
        logging.info("No --paths specified. Monitoring all Plex library folders by default.")

    # If user just wants a manual scan
    if shared.user_input.scan:
        plex_agent_singleton.manual_scan(shared.user_input.paths)
        return

    # Otherwise, daemon mode
    event_handler = PlexWatchdog()
    observer = Observer()
    observers = []

    # Filter out paths that don't match any library subpath (if needed)
    valid_paths = []
    for given_path in shared.user_input.paths:
        full_path = given_path.resolve()
        matches = plex_agent_singleton.find_sections_and_subpaths(given_path)
        if not matches:
            logging.warning(f"{full_path} does not correspond to any known Plex library folder, skipping...")
            continue
        valid_paths.append(full_path)

    for full_path in valid_paths:
        logging.info(f"Scheduling watcher for {full_path}")
        observer.schedule(event_handler, str(full_path), recursive=True)
    observers.append(observer)

    if not observers or not valid_paths:
        logging.error("No valid paths to watch, exiting...")
        sys.exit(-1)

    try:
        logging.info("Registering watchers...")
        observer.start()
        stop_plex_watchdog_service = plex_agent_singleton.start_service()
        logging.info("Ready to operate...")

        while True:
            time.sleep(2)

    except KeyboardInterrupt:
        logging.warning("Detected a keyboard interrupt, stopping PlexNFSWatchdog...")
        for obs in observers:
            obs.unschedule_all()
            obs.stop()
            obs.join()
        if 'stop_plex_watchdog_service' in locals():
            stop_plex_watchdog_service()

    except OSError as os_err:
        logging.error(f"OS error: {os_err}")


if __name__ == '__main__':
    main()
