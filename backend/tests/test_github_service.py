from app.services.github_service import GitHubService


class _FakeRate:
    remaining = 100


class _FakeRateLimit:
    core = _FakeRate()


class _FakeEntry:
    def __init__(self, path, entry_type, content="", size=None):
        self.path = path
        self.type = entry_type
        self.name = path.split("/")[-1]
        self.decoded_content = content.encode("utf-8")
        self.size = size if size is not None else len(self.decoded_content)


class _FakeRepo:
    def __init__(self):
        self.root = [
            _FakeEntry("src", "dir"),
            _FakeEntry("README.md", "file", "# docs only"),
        ]
        self.src = [
            _FakeEntry("src/app.py", "file", "print('ok')"),
            _FakeEntry("src/ignore.txt", "file", "ignore"),
            _FakeEntry("src/main.js", "file", "console.log('ok')"),
        ]

    def get_contents(self, path):
        if path == "":
            return self.root
        if path == "src":
            return self.src
        return []


class _FakeClient:
    def get_rate_limit(self):
        return _FakeRateLimit()

    def get_repo(self, repo_name):
        assert repo_name == "octocat/Hello-World"
        return _FakeRepo()


def test_fetch_repository_snapshot_scans_source_files_not_readme_only():
    service = GitHubService()
    service.client = _FakeClient()

    snapshot = service.fetch_repository_snapshot("https://github.com/octocat/Hello-World")

    assert snapshot["repo"] == "octocat/Hello-World"
    assert snapshot["file_count"] == 2
    assert "# File: src/app.py" in snapshot["content"]
    assert "# File: src/main.js" in snapshot["content"]
    assert "README.md" not in snapshot["content"]
