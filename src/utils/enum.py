from enum import Enum


class MimeType(str, Enum):
    JSON = 'application/json'
    TEXT = 'text/plain'
    FOLDER = 'application/vnd.google-apps.folder'
    MINDMUP = 'application/vnd.mindmup'


class FileStatus(str, Enum):
    ACTIVE = 'active'
    TRASHED = 'trashed'
    DELETED = 'deleted'
