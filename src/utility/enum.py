from enum import Enum


class MimeType(str, Enum):
    JSON = 'application/json'
    TEXT = 'text/plain'
    FOLDER = 'application/vnd.google-apps.folder'
    MINDMUP = 'application/vnd.mindmup'
    OCTET = 'application/octet-stream'
    GOOGLE_DOCS = 'application/vnd.google-apps.document'
    GOOGLE_SHEETS = 'application/vnd.google-apps.spreadsheet'
    GOOGLE_SLIDES = 'application/vnd.google-apps.presentation'
    GOOGLE_DRAWINGS = 'application/vnd.google-apps.drawing'


class FileStatus(str, Enum):
    ACTIVE = 'active'
    TRASHED = 'trashed'
    DELETED = 'deleted'


# Google Apps MIME type that cannot be directly downloaded
GOOGLE_APPS_MIME_TYPE = [
    'application/vnd.google-apps.document',
    'application/vnd.google-apps.spreadsheet',
    'application/vnd.google-apps.presentation',
    'application/vnd.google-apps.form',
    'application/vnd.google-apps.drawing',
    'application/vnd.google-apps.script',
    'application/vnd.google-apps.folder'
]
