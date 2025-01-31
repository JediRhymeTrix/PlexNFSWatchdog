<a name="readme-top"></a>

<!-- Presentation Block -->
<br />

<div align="center">

  <a href="https://github.com/LightDestory/PlexNFSWatchdog">
    <img src="https://raw.githubusercontent.com/LightDestory/PlexNFSWatchdog/master/.github/assets/images/presentation_image.png" alt="Preview" width="90%">
  </a>

  <h2 align="center">Plex NFS Watchdog</h2>
  
  <p align="center">
      A utility to trigger Plex partial-scans on NFS configurations, on which inotify is not supported
  </p>
  
  <br />
  <br />
</div>

<!-- ToC -->

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#book-about-the-project">📖 About The Project</a>
    </li>
    <li>
      <a href="#gear-getting-started">⚙️ Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#usage">Usage</a></li>
        <li><a href="#notes">Notes</a></li>
      </ul>
    </li>
    <li><a href="#dizzy-contributing">💫 Contributing</a></li>
    <li><a href="#handshake-support">🤝 Support</a></li>
    <li><a href="#warning-license">⚠️ License</a></li>
    <li><a href="#hammer_and_wrench-built-with">🛠️ Built With</a></li>
  </ol>
</details>

<!-- About Block -->

## :book: About The Project

Inotify is a Linux kernel subsystem that allows monitoring changes to files and directories in real-time. It is commonly used by applications to watch for changes in files or directories and respond accordingly.

Plex makes use of inotify to perform partial scans when a file is added or removed from a directory. This allows Plex to update its library without having to perform a full scan.

Running Plex Media Server with the library located on Network File System (NFS) mounted directories will not trigger such partial scans because inotify doesn't work on NFS. When a file is changed on an NFS mount, it doesn't trigger an inotify event on the client side.

**Plex NFS Watchdog** is a utility that can be installed on the machine where inotify *does* work. It monitors directories for changes (via inotify or equivalent mechanisms) and triggers partial scans on the Plex Media Server (which might be installed elsewhere) by calling Plex’s API whenever a change is detected.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- Setup Block -->

## :gear: Getting Started

To use **Plex NFS Watchdog**, ensure that on all machines involved, the Plex library sections use the *same folder name*. The full path can differ (for instance, one might be `/media/Movies`, another might be `R:\Movies`), but the last folder name should match.  
This is important because the utility uses that folder name to map the changed directory to the correct Plex library section.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Prerequisites

Obtain the Plex Authentication Token for your Plex Media Server instance. See [this Plex article](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) for instructions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Installation

You can install this tool as a Python package or run it directly from source:

1. **Install with pip**  

   ```bash
   pip install plex-nfs-watchdog
   ```

   Then run it with:

   ```bash
   plex-nfs-watchdog
   ```

2. **Clone & run from source**  

   ```bash
   git clone https://github.com/LightDestory/PlexNFSWatchdog
   cd PlexNFSWatchdog
   pip install -r requirements.txt
   python ./src/plex_nfs_watchdog/plex_nfs_watchdog.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Usage

**Plex NFS Watchdog** supports both manual one-time scans and daemon mode. It can monitor specific folders *or* all library folders (if `--paths` is omitted). In all cases, the utility sends folder-level scan requests to Plex—no single-file scans are done.

| Argument                                           | Role                                                                                                                                   |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| **--scan \| -s**                                    | Manually triggers a partial-scan on the given paths                                                                                    |
| **--daemon \| -d**                                  | Starts a watchdog daemon to automatically trigger a partial scan on the given paths <br> **Requires:** *--interval* and *--listeners* |
| **--paths \| -p** *\[PATHS...\]* (Optional)         | A list of folder paths. If omitted, **all** library section paths will be monitored or scanned.                                        |
| **--host \| -H** *HOST*                             | The host of the Plex server<br>**Default:** *<http://localhost:32400>*                                                                   |
| **--token \| -t** *TOKEN*                           | The token of the Plex server                                                                                                           |
| **--interval \| -i** *INTERVAL* \[OPTIONAL\]        | The interval in seconds to wait between partial-scans                                                                                  |
| **--listeners \| -l** *\[LISTENERS...\]* (Optional) | The event types to watch: `move`, `modify`, `create`, `delete`, etc.                                                                   |
| **--dry-run**                                       | Skip sending actual scan requests to Plex, useful for testing                                                                          |

**Manual scan example** (only scanning specific paths):

```bash
plex-nfs-watchdog --scan --paths /path/to/Movies /path/to/TVShows \
  --host http://localhost:32400 --token YOUR_TOKEN
```

**Daemon scan example** (monitor all library sections):

```bash
plex-nfs-watchdog --daemon \
  --host http://localhost:32400 --token YOUR_TOKEN \
  --interval 150 --listeners move modify create delete
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Notes

- After the first successful run, **a cache file** with your Plex host and token is created in your home directory. Subsequent runs use it, so you don’t have to re-enter your host/token.  
- The utility always does **folder-based scans**; if a file changes, it triggers a scan on that file’s **parent directory**.  
- If no paths are passed, we automatically **monitor all** folder paths from each Plex library section (according to the server configuration).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- Contribute Block -->

## :dizzy: Contributing

If you are interested in contributing, please refer to [Contributing Guidelines](.github/CONTRIBUTING.md) for more information and check open issues. Feel free to ask any questions or propose ideas. Thank you for considering a contribution!

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- Support Block -->

## :handshake: Support

If you find value in this project, please consider making a donation to help keep it maintained and free for everyone.

<p align="center">
<a href='https://ko-fi.com/M4M6KC01A' target='_blank'><img src='https://raw.githubusercontent.com/LightDestory/RepositoryTemplate/master/.github/assets/images/support.png' alt='Buy Me a Hot Chocolate at ko-fi.com' width="45%" /></a>
</p>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- License Block -->

## :warning: License

The content of this repository is distributed under the **GNU GPL-3.0 License**. See the [`LICENSE`](LICENSE) file for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- Built With Block -->

## :hammer_and_wrench: Built With

- [Python](https://www.python.org/)
- [Watchdog](https://pypi.org/project/watchdog/)
- [PlexAPI](https://pypi.org/project/PlexAPI/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
