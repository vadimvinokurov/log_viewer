"""PyInstaller hook for PySide6.

Ensures all required Qt plugins and modules are bundled.
Ref: docs/specs/features/application-packaging.md §5.1
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all PySide6 submodules
hiddenimports = collect_submodules('PySide6')

# Collect Qt plugins (platforms, imageformats, etc.)
datas = collect_data_files('PySide6', include_py_files=False)

# Ensure Qt platforms plugin is included (required for GUI)
hiddenimports += [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]