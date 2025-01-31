import sys
import argparse
import subprocess

def main(args):
    # Build the base command
    command = ['plex-nfs-watchdog']

    # If daemon mode is desired, add --daemon
    if args.daemon:
        command.append('--daemon')

    # If a paths_file was passed, read it and supply --paths
    if args.paths_file is not None:
        with open(args.paths_file, 'r') as file:
            paths = [line.strip() for line in file if line.strip()]
        # Only add --paths if we have any lines
        if paths:
            command += ['--paths', *paths]

    # Add host, token, interval, listeners
    command += [
        '--host', args.host,
        '--token', args.token,
        '--interval', str(args.interval),
        '--listeners', *args.listeners
    ]

    # Run the command
    subprocess.run(command)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run plex-nfs-watchdog with configurable arguments.')

    # Use nargs='?' for a single optional positional argument
    parser.add_argument(
        'paths_file', type=str, nargs='?', default=None,
        help='Path to a file containing a list of paths (if omitted, --paths is not passed)'
    )
    parser.add_argument(
        '--daemon', action='store_true', default=True,
        help='Run as a daemon (default: True)'
    )
    parser.add_argument(
        '--host', type=str, default='http://localhost:32400',
        help='Plex server host (default: http://localhost:32400)'
    )
    parser.add_argument(
        '--token', type=str, default='',
        help='Plex server token (default: empty string)'
    )
    parser.add_argument(
        '--interval', type=int, default=150,
        help='Interval for scanning (default: 150)'
    )
    parser.add_argument(
        '--listeners', nargs='+', default=['move', 'modify', 'create', 'delete'],
        help='List of listeners (default: [move, modify, create, delete])'
    )

    args = parser.parse_args()
    main(args)
