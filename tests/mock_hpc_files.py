from __future__ import annotations

from threading import Lock, get_ident

from hpc_gui.wx_remote_files import RemoteEntry


class MockRemoteFilesBackend:
    def __init__(self):
        self._lock = Lock()
        self.entries = {"/": True, "/work": True, "/work/a.txt": False, "/work/b.txt": False}
        self.calls = []
        self.list_calls = 0
        self.thread_ids = []

    def _record(self, operation, *values):
        with self._lock:
            self.calls.append((operation, *values))
            self.thread_ids.append(get_ident())

    def iterdir_entries(self, path):
        with self._lock:
            self.list_calls += 1
        path = path.rstrip("/") or "/"
        prefix = path if path == "/" else path + "/"
        children = {}
        with self._lock:
            for name, is_dir in self.entries.items():
                if name.startswith(prefix) and "/" not in name[len(prefix):].strip("/"):
                    children[name] = is_dir
        return tuple(RemoteEntry(name, is_dir=is_dir) for name, is_dir in sorted(children.items()))

    def rename(self, source, destination):
        self._record("rename", source, destination)
        with self._lock:
            if source not in self.entries or destination in self.entries:
                raise FileExistsError(destination)
            self.entries[destination] = self.entries.pop(source)

    def remove(self, path, recursive=True):
        self._record("remove", path, recursive)
        with self._lock:
            targets = [name for name in self.entries if name == path or (recursive and name.startswith(path.rstrip("/") + "/"))]
            for name in targets:
                if name != "/":
                    self.entries.pop(name, None)

    def mkdir(self, path):
        self._record("mkdir", path)
        with self._lock:
            if path in self.entries:
                raise FileExistsError(path)
            self.entries[path] = True

    def copy(self, source, destination):
        self._record("copy", source, destination)
        with self._lock:
            self.entries[destination] = self.entries[source]

    def move(self, source, destination):
        self._record("move", source, destination)
        with self._lock:
            self.entries[destination] = self.entries.pop(source)

    def upload(self, source, destination):
        self._record("upload", source, destination)

    def download(self, source, destination):
        self._record("download", source, destination)

    def exists(self, path):
        with self._lock:
            return path in self.entries

    def operation(self, action, paths, destination=""):
        for path in paths:
            if action == "rename":
                self.rename(path, destination)
            elif action == "delete":
                self.remove(path, recursive=True)
            elif action == "copy":
                self.copy(path, f"{destination.rstrip('/')}/{path.rsplit('/', 1)[-1]}")
            elif action == "move":
                self.move(path, f"{destination.rstrip('/')}/{path.rsplit('/', 1)[-1]}")
            elif action == "new_folder":
                self.mkdir(destination)
            elif action in {"upload", "download"}:
                getattr(self, action)(path, destination)
            else:
                raise ValueError(action)
