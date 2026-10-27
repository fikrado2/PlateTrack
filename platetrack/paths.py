"""Compatibility shim: preserve the old platetrack.paths location for existing imports,
while the actual implementation lives in platetrack.core.paths.

This avoids breaking existing code that imports from platetrack.paths.
"""
print("[SHIM] Loading platetrack.paths shim")
from platetrack.core.paths import (
    app_data_dir,
    resource_path,
    base_path,
    db_dir,
    snapshots_dir,
    logs_dir,
    exports_dir,
    models_dir,
    database_file,
)
print("[SHIM] Imported core.paths successfully")
print("[SHIM] __all__ set to:", ['app_data_dir', 'resource_path', 'base_path', 'db_dir', 'snapshots_dir', 'logs_dir', 'exports_dir', 'models_dir', 'database_file'])

__all__ = [
    "app_data_dir",
    "resource_path",
    "base_path",
    "db_dir",
    "snapshots_dir",
    "logs_dir",
    "exports_dir",
    "models_dir",
    "database_file",
]
