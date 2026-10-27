"""Single source of truth for the version number and branding.

Every place that needs the version (About page, window title, PDF reports,
PyInstaller exe metadata, Inno Setup installer, Git tag) reads it from HERE.
Bump the version in this file only.
"""
__version__ = "1.0.0"

APP_NAME = "PlateTrack"
PUBLISHER = "Fikrado Security"
COPYRIGHT = "Copyright (c) Fikrado Security"
