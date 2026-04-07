import os

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

    def check_rate_limit(self):
        rate = self.client.get_rate_limit().core
        if rate.remaining <= 0:
            raise GitHubRateLimitError("GitHub API rate limit exhausted")

    def fetch_repository_snapshot(self, github_url):
        self.check_rate_limit()

        parts = [segment for segment in github_url.rstrip("/").split("/") if segment]
        owner = parts[-2]
        repo = parts[-1]

        repo_obj = self.client.get_repo(f"{owner}/{repo}")

        files_collected = []
        total_bytes = 0
        queue = list(repo_obj.get_contents(""))

        while queue and len(files_collected) < GITHUB_MAX_FILES:
            entry = queue.pop(0)

            if entry.type == "dir":
                queue.extend(repo_obj.get_contents(entry.path))
                continue

            if entry.type != "file":
                continue

            extension = os.path.splitext(entry.name.lower())[1]
            if extension not in ALLOWED_UPLOAD_EXTENSIONS:
                continue

            if entry.size and entry.size > GITHUB_MAX_FILE_BYTES:
                continue

            blob = entry.decoded_content or b""
            file_size = len(blob)
            if file_size > GITHUB_MAX_FILE_BYTES:
                continue
            if total_bytes + file_size > GITHUB_MAX_TOTAL_BYTES:
                break

            content = blob.decode("utf-8", errors="ignore")
            files_collected.append({"path": entry.path, "content": content})
            total_bytes += file_size

        if not files_collected:
            raise ValueError("No supported source files found in repository")

        combined_chunks = [
            f"\n# File: {item['path']}\n{item['content']}" for item in files_collected
        ]

        return {
            "repo": f"{owner}/{repo}",
            "content": "\n".join(combined_chunks),
            "file_count": len(files_collected),
            "total_bytes": total_bytes,
        }


def is_github_rate_limit_response(error):
    status_code = getattr(error, "status", None) or getattr(error, "status_code", None)
    if status_code in {403, 429}:
        return True
    message = str(error).lower()
    return "rate limit" in message or "api rate limit exceeded" in message
