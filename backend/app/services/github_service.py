import os
from collections import Counter

from github import Github

from app.utils.constants import (
    ALLOWED_UPLOAD_EXTENSIONS,
    GITHUB_MAX_FILES,
    GITHUB_MAX_FILE_BYTES,
    GITHUB_MAX_TOTAL_BYTES,
)


class GitHubRateLimitError(Exception):
    pass


class GitHubService:
    def __init__(self, token=None):
        self.client = Github(login_or_token=token) if token else Github()

    MANIFEST_FILENAMES = {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        "cargo.toml",
        "cargo.lock",
        "go.mod",
        "go.sum",
        "pom.xml",
        "composer.json",
        "gemfile",
        "gemfile.lock",
    }

    def check_rate_limit(self):
        rate = self.client.get_rate_limit().core
        if rate.remaining <= 0:
            raise GitHubRateLimitError("GitHub API rate limit exhausted")

    @staticmethod
    def _normalize_repo_url(github_url):
        parts = [segment for segment in (github_url or "").rstrip("/").split("/") if segment]
        owner = parts[-2]
        repo = parts[-1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo

    @classmethod
    def _is_manifest_file(cls, name):
        return (name or "").strip().lower() in cls.MANIFEST_FILENAMES

    @classmethod
    def _is_supported_file(cls, name):
        lowered = (name or "").strip().lower()
        extension = os.path.splitext(lowered)[1]
        return extension in ALLOWED_UPLOAD_EXTENSIONS or cls._is_manifest_file(lowered)

    @staticmethod
    def _matches_selection(path, selected_paths):
        if not selected_paths:
            return True
        normalized_path = (path or "").strip("/")
        for selected in selected_paths:
            current = str(selected or "").strip().strip("/")
            if not current:
                continue
            if normalized_path == current or normalized_path.startswith(f"{current}/"):
                return True
        return False

    @staticmethod
    def _build_tree(entries):
        nodes = {}
        roots = []

        def ensure_node(path, name, entry_type):
            if path not in nodes:
                nodes[path] = {
                    "path": path,
                    "name": name,
                    "type": entry_type,
                    "children": [],
                }
            return nodes[path]

        for entry in sorted(entries, key=lambda item: (item["path"].count("/"), item["path"])):
            node = ensure_node(entry["path"], entry["name"], entry["type"])
            for key, value in entry.items():
                if key != "children":
                    node[key] = value

            if "/" not in entry["path"]:
                roots.append(node)
                continue

            parent_path = entry["path"].rsplit("/", 1)[0]
            parent_name = parent_path.split("/")[-1]
            parent = ensure_node(parent_path, parent_name, "dir")
            if node not in parent["children"]:
                parent["children"].append(node)

        def sort_children(node):
            node["children"] = sorted(
                node.get("children", []),
                key=lambda child: (child["type"] != "dir", child["name"].lower()),
            )
            for child in node["children"]:
                sort_children(child)

        roots = sorted(roots, key=lambda child: (child["type"] != "dir", child["name"].lower()))
        for root in roots:
            sort_children(root)
        return roots

    def _collect_repository_entries(self, repo_obj):
        entries = []
        queue = list(repo_obj.get_contents(""))

        while queue:
            entry = queue.pop(0)
            if entry.type == "dir":
                entries.append(
                    {
                        "path": entry.path,
                        "name": entry.name,
                        "type": "dir",
                        "size": None,
                        "is_supported": True,
                        "is_manifest": False,
                    }
                )
                queue.extend(repo_obj.get_contents(entry.path))
                continue

            if entry.type != "file":
                continue

            entries.append(
                {
                    "path": entry.path,
                    "name": entry.name,
                    "type": "file",
                    "size": entry.size,
                    "is_supported": self._is_supported_file(entry.name),
                    "is_manifest": self._is_manifest_file(entry.name),
                }
            )

        return entries

    def preview_repository(self, github_url):
        self.check_rate_limit()
        owner, repo = self._normalize_repo_url(github_url)

        repo_obj = self.client.get_repo(f"{owner}/{repo}")
        entries = self._collect_repository_entries(repo_obj)
        supported_files = [item for item in entries if item["type"] == "file" and item["is_supported"]]
        language_counts = Counter(
            os.path.splitext(item["name"].lower())[1] or item["name"].lower()
            for item in supported_files
        )
        return {
            "repo": f"{owner}/{repo}",
            "tree": self._build_tree(entries),
            "entries": entries,
            "summary": {
                "total_entries": len(entries),
                "supported_file_count": len(supported_files),
                "manifest_count": len([item for item in supported_files if item["is_manifest"]]),
                "top_extensions": [
                    {"extension": extension, "count": count}
                    for extension, count in language_counts.most_common(6)
                ],
            },
        }

    def fetch_repository_snapshot(self, github_url, selected_paths=None):
        self.check_rate_limit()
        owner, repo = self._normalize_repo_url(github_url)
        repo_obj = self.client.get_repo(f"{owner}/{repo}")
        selected_paths = [str(item or "").strip().strip("/") for item in (selected_paths or []) if str(item or "").strip()]

        files_collected = []
        total_bytes = 0
        for entry in self._collect_repository_entries(repo_obj):
            if entry["type"] != "file" or not entry["is_supported"]:
                continue
            if not self._matches_selection(entry["path"], selected_paths):
                continue
            if entry.get("size") and entry["size"] > GITHUB_MAX_FILE_BYTES:
                continue

            repo_entry = repo_obj.get_contents(entry["path"])
            blob = repo_entry.decoded_content or b""
            file_size = len(blob)
            if file_size > GITHUB_MAX_FILE_BYTES:
                continue
            if total_bytes + file_size > GITHUB_MAX_TOTAL_BYTES:
                break
            if len(files_collected) >= GITHUB_MAX_FILES:
                break

            content = blob.decode("utf-8", errors="ignore")
            files_collected.append(
                {
                    "path": entry["path"],
                    "content": content,
                    "size": file_size,
                    "is_manifest": entry["is_manifest"],
                }
            )
            total_bytes += file_size

        if not files_collected:
            if selected_paths:
                raise ValueError("No supported source files found in the selected files or folders")
            raise ValueError("No supported source files found in repository")

        combined_chunks = [f"\n# File: {item['path']}\n{item['content']}" for item in files_collected]

        dominant_extensions = Counter(
            os.path.splitext(item["path"].lower())[1] or os.path.basename(item["path"].lower())
            for item in files_collected
        )
        scanned_paths = [item["path"] for item in files_collected]
        manifest_paths = [item["path"] for item in files_collected if item["is_manifest"]]

        return {
            "repo": f"{owner}/{repo}",
            "content": "\n".join(combined_chunks),
            "file_count": len(files_collected),
            "total_bytes": total_bytes,
            "selected_paths": selected_paths,
            "scanned_paths": scanned_paths,
            "manifest_paths": manifest_paths,
            "dominant_extensions": [
                {"extension": extension, "count": count}
                for extension, count in dominant_extensions.most_common(6)
            ],
        }


def is_github_rate_limit_response(error):
    status_code = getattr(error, "status", None) or getattr(error, "status_code", None)
    if status_code in {403, 429}:
        return True
    message = str(error).lower()
    return "rate limit" in message or "api rate limit exceeded" in message
