import sys
import argparse
import subprocess

def main(args):
    # Read the paths from the file
    with open(args.paths_file, 'r') as file:
        paths = [line.strip() for line in file.readlines() if line.strip()]

    # Construct the command
    command = [
        'plex-nfs-watchdog',
        '--daemon' if args.daemon else '',
        '--paths', *paths,
        '--host', args.host,
        '--token', args.token,
        '--interval', str(args.interval),
        '--listeners', *args.listeners
    ]

    # Remove empty strings from the command list
    command = [arg for arg in command if arg]

    # Run the command
    subprocess.run(command)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run plex-nfs-watchdog with configurable arguments.')
    
    parser.add_argument('paths_file', type=str, help='Path to the file containing the list of paths')
    parser.add_argument('--daemon', action='store_true', default=True, help='Run as a daemon (default: True)')
    parser.add_argument('--host', type=str, default='http://localhost:32400', help='Plex server host (default: http://localhost:32400)')
    parser.add_argument('--token', type=str, default='', help='Plex server token (default: empty string)')
    parser.add_argument('--interval', type=int, default=150, help='Interval for scanning (default: 150)')
    parser.add_argument('--listeners', nargs='+', default=['move', 'modify', 'create', 'delete'], help='List of listeners (default: [move, modify, create, delete])')

    args = parser.parse_args()
    main(args)
