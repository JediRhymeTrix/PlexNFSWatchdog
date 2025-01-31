import json
import logging
import pprint

from plexapi.server import PlexServer
from pathlib import Path
from threading import Event, Thread

from ..config import shared


class PlexAgent:
    __plex_config: dict[str, str] = {}
    __server: PlexServer = None
    __save_cache: bool = False

    # Each key = Plex library section title, value = list of (folder_name, remote_path).
    # For example:
    #   {
    #     "Movies": [("Movies", "/mnt/media/Movies"), ("Extra", "/mnt/media/MoreMovies")],
    #     "TV Shows": [("TV", "D:/TV Shows")]
    #   }
    __internal_paths: dict[str, list[tuple[str, str]]] = {}
    __notify_queue: list[tuple[str, str]] = []
    __supported_ext: list[str] = [
        "3g2", "3gp", "amv", "asf", "ass", "avi", "drc", "f4a", "f4b", "f4p", "f4v", "flac", "flv",
        "gif", "gifv", "idx", "m2ts", "m2v", "m4p", "m4v", "m4v", "mkv", "mng", "mov", "mp2", "mp3",
        "mp4", "mpe", "mpeg", "mpg", "mpv", "mxf", "nsv", "ogg", "ogv", "qt", "rm", "rmvb", "roq",
        "smi", "srt", "ssa", "sub", "svi", "ts", "vob", "vtt", "wmv", "yuv", "webm"
    ]

    script_start_time: float = 0.0

    def set_script_start_time(self, t: float):
        self.script_start_time = t

    def is_cache_loaded(self) -> bool:
        """
        Checks if the Plex configuration is set.
        :return: True if the Plex configuration is set, False otherwise.
        """
        return bool(self.__plex_config)

    def load_config_cache(self) -> None:
        """
        Loads the Plex configuration from the cache.
        """
        try:
            logging.info(f"Found Plex configuration from cache: {shared.cache_path}")
            with open(shared.cache_path, "r") as cache_file:
                self.__plex_config = json.load(cache_file)
        except OSError as e:
            logging.error(f"Could not load Plex configuration from cache: {e}")
            exit(-1)

    def __save_config_cache(self) -> None:
        """
        Saves the Plex configuration to the cache.
        """
        try:
            logging.info(f"Saving Plex configuration to cache: {shared.cache_path}")
            if not shared.cache_path.parent.exists():
                shared.cache_path.parent.mkdir(parents=True)
            with open(shared.cache_path, "w") as cache_file:
                json.dump(self.__plex_config, cache_file)
        except OSError as e:
            logging.error(f"Could not save Plex configuration to cache: {e}")
            exit(-1)

    def __eval_config(self) -> None:
        """
        Ensures that host and token are available either from CLI or cache.
        """
        if shared.user_input.token and not self.__plex_config:
            self.__plex_config["host"] = shared.user_input.host
            self.__plex_config["token"] = shared.user_input.token
            self.__save_cache = True
        elif shared.user_input.token and self.__plex_config:
            if (self.__plex_config["host"] != shared.user_input.host or
                    self.__plex_config["token"] != shared.user_input.token):
                logging.warning("Plex host and/or token differ from the cached ones!")
                while True:
                    answer: str = input("Do you want to overwrite the cached configuration? [y/N]: ").lower()
                    if answer == 'y':
                        self.__plex_config["host"] = shared.user_input.host
                        self.__plex_config["token"] = shared.user_input.token
                        self.__save_cache = True
                        break
                    elif answer == 'n':
                        break

    def connect(self) -> None:
        """
        Connects to the Plex server using the stored or user-provided host/token.
        """
        self.__eval_config()
        try:
            self.__server = PlexServer(self.__plex_config["host"], self.__plex_config["token"])
            logging.info("Connected to Plex server")
            logging.info(f"Plex version: {self.__server.version}")
            self.__inspect_library()

            # Count how many total folder mappings (all sections)
            num_detected_paths = sum(len(paths) for paths in self.__internal_paths.values())
            if num_detected_paths == 0:
                logging.error("No Plex library sections or paths detected. Check your configuration.")
                exit(-1)

            logging.info(
                f"Found {num_detected_paths} folder mappings across sections:\n"
                f"{pprint.pformat(self.__internal_paths)}"
            )

            if self.__save_cache:
                self.__save_config_cache()
        except Exception as e:
            logging.error(f"Unable to connect to Plex server:\n{e}")
            exit(-1)

    def __inspect_library(self) -> None:
        """
        Gathers Plex library sections, storing them in a dict as:
            {
                section.title: [(folder_name, remote_path), ...]
            }
        This code is platform-neutral, but the remote_path might be formatted for your OS (e.g., "D:/TV Shows" or "/mnt/media").
        """
        for section in self.__server.library.sections():
            if section.title not in self.__internal_paths:
                self.__internal_paths[section.title] = []
            for remote_path in section.locations:
                folder_name = Path(remote_path).name
                # The final component is used for matching user paths.
                self.__internal_paths[section.title].append((folder_name, remote_path))

    def get_all_library_paths(self) -> set[Path]:
        """
        Returns a set of all library folder paths from every known Plex section.
        This is a public, read-only accessor, so code elsewhere doesn't have to
        touch __internal_paths directly.
        """
        all_paths = set()
        for folder_list in self.__internal_paths.values():
            for (_, remote_path) in folder_list:
                all_paths.add(Path(remote_path))
        return all_paths

    def find_sections_and_subpaths(self, item: Path) -> list[tuple[str, Path]]:
        """
        Return ALL (section_title, subpath) combos if the user-supplied path includes a folder_name
        that matches one of Plex's known library paths.

        This approach avoids .resolve(), so we don't rely on OS to transform paths into UNC or
        drive-letter forms automatically. We simply look for a matching folder_name among item.parts.

        Example:
          If the user path is \\Network\\shared\\Movies\\Comedy\\File.mkv
          and Plex has "X:/Movies" with folder_name="Movies",
          then 'Movies' is in item.parts. The subpath is Comedy\\File.mkv.
          We combine that with X:/Movies, yielding X:/Movies/Comedy/File.mkv as the final path to Plex.
        """
        item_parts = list(item.parts)
        matches = []

        for section_title, folder_list in self.__internal_paths.items():
            for (folder_name, remote_path) in folder_list:
                if folder_name in item_parts:
                    # find the index of that folder_name
                    idx = item_parts.index(folder_name)
                    # the subpath is everything after that folder
                    sub_path_parts = item_parts[idx + 1:]
                    if sub_path_parts:
                        subpath = Path(*sub_path_parts)
                    else:
                        # exactly the folder itself
                        subpath = Path(".")
                    matches.append((section_title, subpath))

        return matches

    def __get_scannable_path(self, section_title: str, subpath: Path) -> Path:
        """
        Build the path that Plex expects to see by taking the first remote_path for that section
        and combining it with subpath.

        On Windows, that might look like "D:/TV Shows" + subpath = "D:/TV Shows/Episode..."
        On Linux/macOS, it could be "/mnt/media/TV" + subpath = "/mnt/media/TV/Episode..."
        """
        if section_title not in self.__internal_paths:
            return subpath

        _, first_remote_path = self.__internal_paths[section_title][0]
        return Path(first_remote_path) / subpath

    def _scan(self, section_title: str, subpath: Path) -> None:
        """
        Request Plex to scan the computed path in the specified library section.
        """
        plex_section = self.__server.library.section(section_title)
        if plex_section.refreshing:
            if shared.user_input.daemon:
                logging.warning(f"Section '{section_title}' is currently refreshing; re-scheduling scan.")
                self.__notify_queue.append((section_title, str(subpath)))
            else:
                logging.warning(f"Section '{section_title}' is currently refreshing; skipping scan.")
            return

        scannable_path = self.__get_scannable_path(section_title, subpath)
        logging.info(f"Requesting Plex to scan path '{scannable_path}' in section '{section_title}'")

        if shared.user_input.dry_run:
            logging.info("Skipping Plex scan (dry-run mode)")
        else:
            plex_section.update(str(scannable_path))
            
    def _scan_once(self, section_title: str, subpath: Path) -> bool:
        """
        Attempts a single partial scan. Returns True if success,
        False if the section is refreshing (and we should retry later).
        """
        plex_section = self.__server.library.section(section_title)
        if plex_section.refreshing:
            logging.warning(f"Section '{section_title}' is currently refreshing; re-scheduling scan.")
            return False  # We'll reschedule in start_service() loop

        scannable_path = self.__get_scannable_path(section_title, subpath)
        logging.info(f"Requesting Plex to scan path '{scannable_path}' in section '{section_title}'")
        if shared.user_input.dry_run:
            logging.info("Skipping Plex scan (dry-run mode)")
        else:
            plex_section.update(str(scannable_path))
        return True

    def manual_scan(self, paths: set[Path]) -> None:
        """
        For manual (user-initiated) scans.
        For each path, find which Plex section(s) it might belong to, then request a scan.
        """
        for given_path in paths:
            logging.info(f"Analyzing '{given_path}' for manual scan.")
            all_matches = self.find_sections_and_subpaths(given_path)
            if not all_matches:
                logging.error(f"Could not map '{given_path}' to any known Plex section.")
                continue

            for (section_title, subpath) in all_matches:
                self._scan(section_title, subpath)

    def parse_event(self, event) -> None:
        """
        Filesystem event handler.
        Figures out which library sections might be impacted, then schedules scans accordingly.
        """
        event_type = event.event_type

        if event_type != 'moved':
            event_path = Path(event.src_path)
        else:
            event_path = Path(event.dest_path)

        # Check if the path still exists (might have been removed)
        if not event_path.exists():
            logging.debug(f"Path {event_path} no longer exists; ignoring event.")
            return

        # Gather the file/folder's last modified time
        mtime = event_path.stat().st_mtime
        if mtime < self.script_start_time:
            # This means the file/folder was last modified before script started
            logging.debug(f"Ignoring event on {event_path}, modified before script start.")
            return

        # If it's a file, get the parent folder
        if not event.is_directory:
            event_path = event_path.parent

        all_matches = self.find_sections_and_subpaths(event_path)
        if not all_matches:
            logging.error(f"Could not find a matching Plex section for '{event_path}'")
            return

        for (section_title, subpath) in all_matches:
            section_scan = (section_title, str(subpath))
            if section_scan not in self.__notify_queue:
                logging.info(
                    f"Queueing scan (event: {event_type}) => {section_title}: '{subpath}'"
                )
                self.__notify_queue.append(section_scan)

    def start_service(self) -> ():
        """
        Spawns a background thread that periodically checks the notify queue and processes scans.
        Returns a callable to stop the thread.
        """
        stopped = Event()

        def loop():
            while not stopped.wait(shared.user_input.interval):
                # We'll iterate a snapshot of the current queue
                current_queue_size = len(self.__notify_queue)
                for _ in range(current_queue_size):
                    section_title, subpath_str = self.__notify_queue.pop(0)
                    success = self._scan_once(section_title, Path(subpath_str))
                    if not success:
                        # Section refreshing => re-queue this item, but continue to next item
                        self.__notify_queue.append((section_title, str(subpath_str)))
                    # If success, we do nothing more for that item
                # Then we wait the next interval

        Thread(target=loop).start()
        return stopped.set


plex_agent_singleton = PlexAgent()
