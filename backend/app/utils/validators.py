import os
import re
from urllib.parse import urlparse

from app.utils.constants import ALLOWED_UPLOAD_EXTENSIONS


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(email and EMAIL_REGEX.match(email))


def is_valid_password(password):
    if not password or len(password) < 8:
        return False
    has_alpha = any(char.isalpha() for char in password)
    has_digit = any(char.isdigit() for char in password)
    return has_alpha and has_digit


def is_valid_github_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return False
    parts = [segment for segment in parsed.path.split("/") if segment]
    return len(parts) >= 2


def get_file_extension(filename):
    if not filename:
        return ""
    return os.path.splitext(filename.lower())[1]


def is_allowed_upload(filename):
    return get_file_extension(filename) in ALLOWED_UPLOAD_EXTENSIONS
