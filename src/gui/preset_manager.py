"""
Cheat Preset Manager for Napoleon Total War Cheat Engine.

Provides save, load, import, export, and sharing of complete cheat
configurations (presets).  Presets are stored as versioned JSON files with
full compatibility checks.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QScrollArea, QGridLayout, QGroupBox, QLineEdit,
        QTextEdit, QListWidget, QListWidgetItem, QMessageBox,
        QFileDialog, QInputDialog, QSplitter, QComboBox,
        QSizePolicy, QApplication, QMenu, QAbstractItemView,
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QSize
    from PyQt6.QtGui import QFont, QColor, QIcon, QCursor, QAction
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.memory import CheatManager, CheatType

logger = logging.getLogger('napoleon.gui.preset_manager')


# ---------------------------------------------------------------------------
# Current preset format version
# ---------------------------------------------------------------------------

PRESET_FORMAT_VERSION = "2.0"
COMPATIBLE_VERSIONS = {"1.0", "1.1", "2.0"}
APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Preset data model
# ---------------------------------------------------------------------------

class CheatPreset:
    """
    Represents a complete cheat configuration snapshot.

    Attributes:
        name:            Human-readable name.
        description:     Optional description / notes.
        version:         Preset format version (for compatibility checks).
        app_version:     Application version that created the preset.
        created:         ISO-8601 creation timestamp.
        modified:        ISO-8601 last-modified timestamp.
        author:          Optional author tag.
        tags:            User-assigned tags for organisation.
        cheats:          Mapping of cheat-type value → per-cheat state dict.
    """

    def __init__(
        self,
        name: str = "Untitled",
        description: str = "",
        author: str = "",
        tags: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.version = PRESET_FORMAT_VERSION
        self.app_version = APP_VERSION
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.created = now
        self.modified = now
        self.author = author
        self.tags: List[str] = tags or []
        self.cheats: Dict[str, Dict[str, Any]] = {}

    # ---- serialisation ----

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset_format_version": self.version,
            "app_version": self.app_version,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "created": self.created,
            "modified": self.modified,
            "cheats": self.cheats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheatPreset":
        preset = cls.__new__(cls)
        preset.version = data.get("preset_format_version", "1.0")
        preset.app_version = data.get("app_version", "unknown")
        preset.name = data.get("name", "Imported Preset")
        preset.description = data.get("description", "")
        preset.author = data.get("author", "")
        preset.tags = data.get("tags", [])
        preset.created = data.get("created", "")
        preset.modified = data.get("modified", "")
        preset.cheats = data.get("cheats", {})
        return preset

    # ---- JSON I/O ----

    def save_to_file(self, path: Path) -> None:
        self.modified = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: Path) -> "CheatPreset":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Preset storage / repository
# ---------------------------------------------------------------------------

class PresetRepository:
    """
    Manages a directory of preset JSON files.

    Default location: ``~/.napoleon_cheat/presets/``
    """

    def __init__(self, directory: Optional[Path] = None):
        self.directory = directory or (Path.home() / ".napoleon_cheat" / "presets")
        self.directory.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> List[CheatPreset]:
        presets: List[CheatPreset] = []
        for p in sorted(self.directory.glob("*.json")):
            try:
                presets.append(CheatPreset.load_from_file(p))
            except Exception as exc:
                logger.warning("Skipping invalid preset %s: %s", p, exc)
        return presets

    def save_preset(self, preset: CheatPreset) -> Path:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in preset.name)
        path = self.directory / f"{safe_name}.json"
        preset.save_to_file(path)
        return path

    def delete_preset(self, name: str) -> bool:
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path = self.directory / f"{safe_name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def import_preset(self, source_path: Path) -> CheatPreset:
        preset = CheatPreset.load_from_file(source_path)
        self.save_preset(preset)
        return preset

    def export_preset(self, preset: CheatPreset, dest_path: Path) -> None:
        preset.save_to_file(dest_path)


# ---------------------------------------------------------------------------
# Version compatibility helpers
# ---------------------------------------------------------------------------

def check_version_compatibility(preset: CheatPreset) -> Dict[str, Any]:
    """
    Check whether *preset* is compatible with the running application.

    Returns a dict with keys:
      - ``compatible`` (bool)
      - ``warnings`` (list[str])
      - ``preset_version`` (str)
      - ``app_version`` (str)
    """
    result: Dict[str, Any] = {
        "compatible": True,
        "warnings": [],
        "preset_version": preset.version,
        "app_version": APP_VERSION,
    }

    if preset.version not in COMPATIBLE_VERSIONS:
        result["compatible"] = False
        result["warnings"].append(
            f"Preset format version {preset.version!r} is not supported. "
            f"Compatible versions: {', '.join(sorted(COMPATIBLE_VERSIONS))}."
        )

    # Warn if unknown cheat types found
    known_types = {ct.value for ct in CheatType}
    unknown = [k for k in preset.cheats if k not in known_types]
    if unknown:
        result["warnings"].append(
            f"Preset contains unknown cheat types: {', '.join(unknown)}. "
            "They will be skipped on load."
        )

    return result


# ---------------------------------------------------------------------------
# Capture / apply helpers
# ---------------------------------------------------------------------------

def capture_preset_from_manager(
    cheat_manager: CheatManager,
    name: str = "Untitled",
    description: str = "",
    author: str = "",
    tags: Optional[List[str]] = None,
) -> CheatPreset:
    """
    Snapshot the current state of *cheat_manager* into a :class:`CheatPreset`.
    """
    preset = CheatPreset(name=name, description=description, author=author, tags=tags)

    for cheat_def in cheat_manager.cheat_definitions:
        ct = cheat_def.cheat_type
        is_active = cheat_manager.is_cheat_active(ct)
        entry: Dict[str, Any] = {
            "name": cheat_def.name,
            "active": is_active,
            "mode": cheat_def.mode,
            "value_type": cheat_def.value_type.value,
            "cheat_value": cheat_def.cheat_value,
        }
        # Include the resolved address if available
        addr = cheat_manager._resolved_addresses.get(ct)
        if addr is not None:
            entry["resolved_address"] = f"0x{addr:08X}"
        preset.cheats[ct.value] = entry

    return preset


def apply_preset_to_manager(
    cheat_manager: CheatManager,
    preset: CheatPreset,
) -> Dict[str, Any]:
    """
    Apply *preset* to *cheat_manager*.

    Returns a summary dict: ``{'activated': [...], 'skipped': [...], 'errors': [...]}``.
    """
    result: Dict[str, List[str]] = {"activated": [], "skipped": [], "errors": []}

    compat = check_version_compatibility(preset)
    if not compat["compatible"]:
        result["errors"].extend(compat["warnings"])
        return result

    # Deactivate everything first
    cheat_manager.deactivate_all_cheats()

    known_types = {ct.value: ct for ct in CheatType}

    for cheat_key, cheat_state in preset.cheats.items():
        ct = known_types.get(cheat_key)
        if ct is None:
            result["skipped"].append(cheat_key)
            continue

        if not cheat_state.get("active", False):
            continue

        try:
            success = cheat_manager.activate_cheat(ct)
            if success:
                result["activated"].append(cheat_state.get("name", cheat_key))
            else:
                result["errors"].append(f"Could not activate {cheat_state.get('name', cheat_key)}")
        except Exception as exc:
            result["errors"].append(f"{cheat_state.get('name', cheat_key)}: {exc}")

    return result


# ---------------------------------------------------------------------------
# Qt preset-manager tab / widget
# ---------------------------------------------------------------------------

if PYQT_AVAILABLE:

    class _PresetListItem(QListWidgetItem):
        """List item wrapping a :class:`CheatPreset`."""

        def __init__(self, preset: CheatPreset):
            super().__init__(f"{'🟢' if any(c.get('active') for c in preset.cheats.values()) else '⚪'} {preset.name}")
            self.preset = preset
            self.setToolTip(f"{preset.description or 'No description'}\n"
                            f"Author: {preset.author or 'unknown'}\n"
                            f"Created: {preset.created}\n"
                            f"Tags: {', '.join(preset.tags) if preset.tags else '—'}")

    class PresetManagerTab(QWidget):
        """
        Full preset-manager tab for the main GUI.

        Features:
          - List of saved presets with search / filter.
          - Save current cheat state as a new preset.
          - Load / apply a preset to the cheat manager.
          - Import / export presets as JSON files.
          - Delete and duplicate presets.
          - Version compatibility display.
        """

        preset_applied = pyqtSignal(str)   # emitted with preset name

        def __init__(
            self,
            cheat_manager: Optional[CheatManager] = None,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)

            self.cheat_manager = cheat_manager
            self.repo = PresetRepository()
            self._current_preset: Optional[CheatPreset] = None

            self._build_ui()
            self._refresh_list()

        # --------------------------------------------------------------
        # UI construction
        # --------------------------------------------------------------

        def _build_ui(self) -> None:
            root = QVBoxLayout(self)

            # Top controls
            top = QHBoxLayout()

            self._search_input = QLineEdit()
            self._search_input.setPlaceholderText("🔍 Search presets…")
            self._search_input.textChanged.connect(self._filter_list)
            self._search_input.setStyleSheet(
                "QLineEdit { background: #2d2d2d; color: #ccc; border: 1px solid #555; "
                "border-radius: 4px; padding: 4px 8px; }"
            )
            top.addWidget(self._search_input)

            self._tag_filter = QComboBox()
            self._tag_filter.addItem("All Tags")
            self._tag_filter.setStyleSheet(
                "QComboBox { background: #2d2d2d; color: #ccc; border: 1px solid #555; "
                "border-radius: 4px; padding: 4px 8px; }"
            )
            self._tag_filter.currentTextChanged.connect(lambda _: self._filter_list())
            top.addWidget(self._tag_filter)

            root.addLayout(top)

            # Splitter: list + detail
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Left – preset list
            left = QWidget()
            left_layout = QVBoxLayout(left)
            left_layout.setContentsMargins(0, 0, 0, 0)

            self._preset_list = QListWidget()
            self._preset_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self._preset_list.currentItemChanged.connect(self._on_selection_changed)
            self._preset_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self._preset_list.customContextMenuRequested.connect(self._show_context_menu)
            self._preset_list.setStyleSheet(
                "QListWidget { background: #252525; color: #ccc; border: 1px solid #3c3c3c; "
                "border-radius: 4px; } "
                "QListWidget::item { padding: 6px; } "
                "QListWidget::item:selected { background: #0e639c; color: #fff; }"
            )
            left_layout.addWidget(self._preset_list)

            # List action buttons
            btn_row = QHBoxLayout()

            self._btn_save = QPushButton("💾 Save Current")
            self._btn_save.clicked.connect(self._save_current)
            self._btn_save.setToolTip("Snapshot all current cheat states as a new preset")
            btn_row.addWidget(self._btn_save)

            self._btn_import = QPushButton("📥 Import")
            self._btn_import.clicked.connect(self._import_preset)
            self._btn_import.setToolTip("Import a preset JSON file")
            btn_row.addWidget(self._btn_import)

            self._btn_refresh = QPushButton("🔄 Refresh")
            self._btn_refresh.clicked.connect(self._refresh_list)
            btn_row.addWidget(self._btn_refresh)

            left_layout.addLayout(btn_row)
            splitter.addWidget(left)

            # Right – detail panel
            right = QWidget()
            right_layout = QVBoxLayout(right)
            right_layout.setContentsMargins(0, 0, 0, 0)

            # Info group
            info_group = QGroupBox("Preset Details")
            info_layout = QGridLayout(info_group)
            info_layout.setSpacing(6)

            info_layout.addWidget(QLabel("Name:"), 0, 0)
            self._detail_name = QLabel("—")
            self._detail_name.setStyleSheet("font-weight: bold; color: #fff;")
            info_layout.addWidget(self._detail_name, 0, 1)

            info_layout.addWidget(QLabel("Author:"), 1, 0)
            self._detail_author = QLabel("—")
            info_layout.addWidget(self._detail_author, 1, 1)

            info_layout.addWidget(QLabel("Created:"), 2, 0)
            self._detail_created = QLabel("—")
            info_layout.addWidget(self._detail_created, 2, 1)

            info_layout.addWidget(QLabel("Modified:"), 3, 0)
            self._detail_modified = QLabel("—")
            info_layout.addWidget(self._detail_modified, 3, 1)

            info_layout.addWidget(QLabel("Version:"), 4, 0)
            self._detail_version = QLabel("—")
            info_layout.addWidget(self._detail_version, 4, 1)

            info_layout.addWidget(QLabel("Tags:"), 5, 0)
            self._detail_tags = QLabel("—")
            info_layout.addWidget(self._detail_tags, 5, 1)

            self._compat_label = QLabel("")
            self._compat_label.setWordWrap(True)
            info_layout.addWidget(self._compat_label, 6, 0, 1, 2)

            right_layout.addWidget(info_group)

            # Description
            desc_group = QGroupBox("Description")
            desc_layout = QVBoxLayout(desc_group)
            self._detail_desc = QTextEdit()
            self._detail_desc.setReadOnly(True)
            self._detail_desc.setStyleSheet(
                "QTextEdit { background: #2d2d2d; color: #ccc; border: 1px solid #3c3c3c; "
                "border-radius: 4px; }"
            )
            self._detail_desc.setMaximumHeight(80)
            desc_layout.addWidget(self._detail_desc)
            right_layout.addWidget(desc_group)

            # Cheat summary
            cheats_group = QGroupBox("Cheats in Preset")
            cheats_layout = QVBoxLayout(cheats_group)
            self._cheat_summary = QTextEdit()
            self._cheat_summary.setReadOnly(True)
            self._cheat_summary.setStyleSheet(
                "QTextEdit { background: #2d2d2d; color: #ccc; border: 1px solid #3c3c3c; "
                "border-radius: 4px; font-family: monospace; }"
            )
            cheats_layout.addWidget(self._cheat_summary)
            right_layout.addWidget(cheats_group)

            # Detail action buttons
            detail_btns = QHBoxLayout()

            self._btn_load = QPushButton("▶ Load Preset")
            self._btn_load.clicked.connect(self._load_selected)
            self._btn_load.setEnabled(False)
            self._btn_load.setToolTip("Apply this preset to the cheat manager")
            detail_btns.addWidget(self._btn_load)

            self._btn_export = QPushButton("📤 Export")
            self._btn_export.clicked.connect(self._export_selected)
            self._btn_export.setEnabled(False)
            detail_btns.addWidget(self._btn_export)

            self._btn_duplicate = QPushButton("📋 Duplicate")
            self._btn_duplicate.clicked.connect(self._duplicate_selected)
            self._btn_duplicate.setEnabled(False)
            detail_btns.addWidget(self._btn_duplicate)

            self._btn_delete = QPushButton("🗑️ Delete")
            self._btn_delete.clicked.connect(self._delete_selected)
            self._btn_delete.setEnabled(False)
            self._btn_delete.setStyleSheet(
                "QPushButton { background-color: #8b0000; }"
                "QPushButton:hover { background-color: #a00000; }"
            )
            detail_btns.addWidget(self._btn_delete)

            right_layout.addLayout(detail_btns)
            splitter.addWidget(right)

            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 3)
            root.addWidget(splitter)

        # --------------------------------------------------------------
        # List management
        # --------------------------------------------------------------

        def _refresh_list(self) -> None:
            self._preset_list.clear()
            presets = self.repo.list_presets()
            all_tags: set[str] = set()
            for preset in presets:
                item = _PresetListItem(preset)
                self._preset_list.addItem(item)
                all_tags.update(preset.tags)

            # Refresh tag filter
            current_tag = self._tag_filter.currentText()
            self._tag_filter.blockSignals(True)
            self._tag_filter.clear()
            self._tag_filter.addItem("All Tags")
            for tag in sorted(all_tags):
                self._tag_filter.addItem(tag)
            idx = self._tag_filter.findText(current_tag)
            if idx >= 0:
                self._tag_filter.setCurrentIndex(idx)
            self._tag_filter.blockSignals(False)

        def _filter_list(self) -> None:
            search_text = self._search_input.text().lower()
            selected_tag = self._tag_filter.currentText()

            for i in range(self._preset_list.count()):
                item = self._preset_list.item(i)
                if not isinstance(item, _PresetListItem):
                    continue
                preset = item.preset

                name_match = search_text in preset.name.lower() if search_text else True
                desc_match = search_text in preset.description.lower() if search_text else True
                tag_match = (
                    selected_tag == "All Tags"
                    or selected_tag in preset.tags
                )

                item.setHidden(not ((name_match or desc_match) and tag_match))

        # --------------------------------------------------------------
        # Selection handling
        # --------------------------------------------------------------

        def _on_selection_changed(self, current: Optional[QListWidgetItem], _prev) -> None:
            if current is None or not isinstance(current, _PresetListItem):
                self._clear_details()
                return

            preset = current.preset
            self._current_preset = preset

            self._detail_name.setText(preset.name)
            self._detail_author.setText(preset.author or "—")
            self._detail_created.setText(preset.created or "—")
            self._detail_modified.setText(preset.modified or "—")
            self._detail_version.setText(f"Format v{preset.version}  |  App v{preset.app_version}")
            self._detail_tags.setText(", ".join(preset.tags) if preset.tags else "—")
            self._detail_desc.setPlainText(preset.description or "(no description)")

            # Compatibility check
            compat = check_version_compatibility(preset)
            if compat["compatible"] and not compat["warnings"]:
                self._compat_label.setText("✅ Compatible")
                self._compat_label.setStyleSheet("color: #00cc55; font-weight: bold;")
            elif compat["compatible"]:
                self._compat_label.setText("⚠️ " + " ".join(compat["warnings"]))
                self._compat_label.setStyleSheet("color: #ffaa00;")
            else:
                self._compat_label.setText("❌ " + " ".join(compat["warnings"]))
                self._compat_label.setStyleSheet("color: #ff4444; font-weight: bold;")

            # Cheats summary
            lines: List[str] = []
            for key, state in preset.cheats.items():
                status = "ON " if state.get("active") else "OFF"
                name = state.get("name", key)
                mode = state.get("mode", "?")
                lines.append(f"[{status}] {name:<28s}  ({mode})")
            self._cheat_summary.setPlainText("\n".join(lines) if lines else "(empty)")

            # Enable buttons
            self._btn_load.setEnabled(True)
            self._btn_export.setEnabled(True)
            self._btn_duplicate.setEnabled(True)
            self._btn_delete.setEnabled(True)

        def _clear_details(self) -> None:
            self._current_preset = None
            self._detail_name.setText("—")
            self._detail_author.setText("—")
            self._detail_created.setText("—")
            self._detail_modified.setText("—")
            self._detail_version.setText("—")
            self._detail_tags.setText("—")
            self._compat_label.setText("")
            self._detail_desc.setPlainText("")
            self._cheat_summary.setPlainText("")
            self._btn_load.setEnabled(False)
            self._btn_export.setEnabled(False)
            self._btn_duplicate.setEnabled(False)
            self._btn_delete.setEnabled(False)

        # --------------------------------------------------------------
        # Actions
        # --------------------------------------------------------------

        def _save_current(self) -> None:
            """Save the current cheat-manager state as a new preset."""
            name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
            if not ok or not name.strip():
                return

            desc, _ = QInputDialog.getText(self, "Save Preset", "Description (optional):")
            author, _ = QInputDialog.getText(self, "Save Preset", "Author (optional):")
            tags_str, _ = QInputDialog.getText(self, "Save Preset", "Tags (comma-separated, optional):")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

            if self.cheat_manager is None:
                QMessageBox.warning(self, "Error", "No cheat manager available.")
                return

            preset = capture_preset_from_manager(
                self.cheat_manager,
                name=name.strip(),
                description=desc.strip(),
                author=author.strip(),
                tags=tags,
            )
            path = self.repo.save_preset(preset)
            self._refresh_list()
            QMessageBox.information(self, "Saved", f"Preset '{preset.name}' saved to\n{path}")

        def _load_selected(self) -> None:
            """Apply the selected preset."""
            if self._current_preset is None or self.cheat_manager is None:
                return

            compat = check_version_compatibility(self._current_preset)
            if not compat["compatible"]:
                QMessageBox.critical(
                    self, "Incompatible Preset",
                    "\n".join(compat["warnings"]),
                )
                return

            if compat["warnings"]:
                reply = QMessageBox.question(
                    self, "Compatibility Warnings",
                    "\n".join(compat["warnings"]) + "\n\nContinue loading?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            result = apply_preset_to_manager(self.cheat_manager, self._current_preset)
            summary_parts: List[str] = []
            if result["activated"]:
                summary_parts.append(f"Activated: {', '.join(result['activated'])}")
            if result["skipped"]:
                summary_parts.append(f"Skipped: {', '.join(result['skipped'])}")
            if result["errors"]:
                summary_parts.append(f"Errors: {', '.join(result['errors'])}")

            QMessageBox.information(
                self, "Preset Loaded",
                f"Preset '{self._current_preset.name}' applied.\n\n" + "\n".join(summary_parts),
            )
            self.preset_applied.emit(self._current_preset.name)

        def _import_preset(self) -> None:
            """Import a preset from an external JSON file."""
            path, _ = QFileDialog.getOpenFileName(
                self, "Import Preset", "", "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return
            try:
                preset = self.repo.import_preset(Path(path))
                self._refresh_list()
                QMessageBox.information(self, "Imported", f"Preset '{preset.name}' imported.")
            except Exception as exc:
                QMessageBox.critical(self, "Import Error", str(exc))

        def _export_selected(self) -> None:
            """Export the selected preset to an external JSON file."""
            if self._current_preset is None:
                return
            safe_name = "".join(
                c if c.isalnum() or c in " _-" else "_" for c in self._current_preset.name
            )
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Preset", f"{safe_name}.json",
                "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return
            try:
                self.repo.export_preset(self._current_preset, Path(path))
                QMessageBox.information(self, "Exported", f"Preset exported to\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

        def _duplicate_selected(self) -> None:
            """Create a copy of the selected preset with a new name."""
            if self._current_preset is None:
                return
            new_name, ok = QInputDialog.getText(
                self, "Duplicate Preset",
                "New name:",
                text=f"{self._current_preset.name} (copy)",
            )
            if not ok or not new_name.strip():
                return
            dup = CheatPreset.from_dict(self._current_preset.to_dict())
            dup.name = new_name.strip()
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            dup.created = now
            dup.modified = now
            self.repo.save_preset(dup)
            self._refresh_list()

        def _delete_selected(self) -> None:
            """Delete the selected preset after confirmation."""
            if self._current_preset is None:
                return
            reply = QMessageBox.question(
                self, "Delete Preset",
                f"Delete preset '{self._current_preset.name}'?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.repo.delete_preset(self._current_preset.name)
            self._refresh_list()
            self._clear_details()

        def _show_context_menu(self, pos) -> None:
            item = self._preset_list.itemAt(pos)
            if item is None or not isinstance(item, _PresetListItem):
                return
            menu = QMenu(self)
            menu.addAction("▶ Load").triggered.connect(self._load_selected)
            menu.addAction("📤 Export").triggered.connect(self._export_selected)
            menu.addAction("📋 Duplicate").triggered.connect(self._duplicate_selected)
            menu.addSeparator()
            menu.addAction("🗑️ Delete").triggered.connect(self._delete_selected)
            menu.exec(self._preset_list.mapToGlobal(pos))

        # --------------------------------------------------------------
        # Public API
        # --------------------------------------------------------------

        def set_cheat_manager(self, cm: CheatManager) -> None:
            self.cheat_manager = cm

        def cleanup(self) -> None:
            """Release resources."""
            pass

else:
    # Fallback when PyQt6 is not available
    class PresetManagerTab:  # type: ignore[no-redef]
        """Stub when PyQt6 is unavailable."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt6 is required for PresetManagerTab")
