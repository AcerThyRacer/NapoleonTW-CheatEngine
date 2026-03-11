"""
File Editor tab for the GUI.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QFileDialog, QTreeWidget, QTreeWidgetItem, QTextEdit,
        QGroupBox, QTabWidget, QSplitter, QMessageBox
    )
    from PyQt6.QtCore import Qt
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.files import ESFEditor, ScriptEditor, ConfigEditor
from src.utils import get_save_game_directory, get_scripts_directory


class FileEditorTab(QWidget):
    """
    File editor tab widget.
    """
    
    def __init__(self):
        """Initialize file editor tab."""
        super().__init__()
        
        self.esf_editor = ESFEditor()
        self.script_editor = ScriptEditor()
        self.config_editor = ConfigEditor()
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Create file type tabs
        self.file_tabs = QTabWidget()
        
        # Save Game Editor tab
        save_tab = self._create_save_editor_tab()
        self.file_tabs.addTab(save_tab, "Save Games (.esf)")
        
        # Script Editor tab
        script_tab = self._create_script_editor_tab()
        self.file_tabs.addTab(script_tab, "Scripts (.lua)")
        
        # Config Editor tab
        config_tab = self._create_config_editor_tab()
        self.file_tabs.addTab(config_tab, "Configuration")
        
        layout.addWidget(self.file_tabs)
        self.setLayout(layout)
    
    def _create_save_editor_tab(self) -> QWidget:
        """Create save game editor tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # File controls
        file_layout = QHBoxLayout()
        
        self.esf_open_btn = QPushButton("Open Save Game")
        self.esf_open_btn.clicked.connect(self._open_esf_file)
        file_layout.addWidget(self.esf_open_btn)
        
        self.esf_save_btn = QPushButton("Save Changes")
        self.esf_save_btn.clicked.connect(self._save_esf_file)
        self.esf_save_btn.setEnabled(False)
        self.esf_save_btn.setToolTip("Open a save game first to save changes")
        file_layout.addWidget(self.esf_save_btn)
        
        self.esf_export_xml_btn = QPushButton("Export to XML")
        self.esf_export_xml_btn.clicked.connect(self._export_esf_xml)
        file_layout.addWidget(self.esf_export_xml_btn)
        
        layout.addLayout(file_layout)
        
        # File info
        self.esf_file_label = QLabel("No file loaded")
        layout.addWidget(self.esf_file_label)
        
        # Tree view for ESF structure
        self.esf_tree = QTreeWidget()
        self.esf_tree.setHeaderLabels(["Name", "Value", "Type"])
        layout.addWidget(QLabel("Save Structure:"))
        layout.addWidget(self.esf_tree)
        
        # Edit controls
        edit_layout = QHBoxLayout()
        
        edit_layout.addWidget(QLabel("Edit Value:"))
        self.esf_value_edit = QLineEdit()
        edit_layout.addWidget(self.esf_value_edit)
        
        self.esf_apply_btn = QPushButton("Apply")
        self.esf_apply_btn.clicked.connect(self._apply_esf_edit)
        edit_layout.addWidget(self.esf_apply_btn)
        
        layout.addLayout(edit_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _create_script_editor_tab(self) -> QWidget:
        """Create script editor tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # File controls
        file_layout = QHBoxLayout()
        
        self.script_open_btn = QPushButton("Open Script")
        self.script_open_btn.clicked.connect(self._open_script_file)
        file_layout.addWidget(self.script_open_btn)
        
        self.script_save_btn = QPushButton("Save")
        self.script_save_btn.clicked.connect(self._save_script_file)
        self.script_save_btn.setEnabled(False)
        self.script_save_btn.setToolTip("Open a script first to save changes")
        file_layout.addWidget(self.script_save_btn)
        
        self.script_revert_btn = QPushButton("Revert")
        self.script_revert_btn.clicked.connect(self._revert_script)
        file_layout.addWidget(self.script_revert_btn)
        
        layout.addLayout(file_layout)
        
        # File info
        self.script_file_label = QLabel("No file loaded")
        layout.addWidget(self.script_file_label)
        
        # Quick edits
        quick_layout = QHBoxLayout()
        
        quick_layout.addWidget(QLabel("Quick Edits:"))
        
        self.treasury_btn = QPushButton("Set Treasury to 999999")
        self.treasury_btn.clicked.connect(self._set_treasury)
        quick_layout.addWidget(self.treasury_btn)
        
        self.fog_btn = QPushButton("Disable Fog of War")
        self.fog_btn.clicked.connect(self._disable_fog)
        quick_layout.addWidget(self.fog_btn)
        
        layout.addLayout(quick_layout)
        
        # Script editor
        self.script_editor_widget = QTextEdit()
        self.script_editor_widget.setPlaceholderText("Open a .lua script file to edit...")
        layout.addWidget(self.script_editor_widget)
        
        widget.setLayout(layout)
        return widget
    
    def _create_config_editor_tab(self) -> QWidget:
        """Create configuration editor tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # File controls
        file_layout = QHBoxLayout()
        
        self.config_open_btn = QPushButton("Open Configuration")
        self.config_open_btn.clicked.connect(self._open_config_file)
        file_layout.addWidget(self.config_open_btn)
        
        self.config_save_btn = QPushButton("Save")
        self.config_save_btn.clicked.connect(self._save_config_file)
        self.config_save_btn.setEnabled(False)
        self.config_save_btn.setToolTip("Open configuration first to save changes")
        file_layout.addWidget(self.config_save_btn)
        
        self.config_reset_btn = QPushButton("Reset to Defaults")
        self.config_reset_btn.clicked.connect(self._reset_config)
        file_layout.addWidget(self.config_reset_btn)
        
        layout.addLayout(file_layout)
        
        # Presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        
        self.cheats_preset_btn = QPushButton("Enable Cheats")
        self.cheats_preset_btn.clicked.connect(lambda: self._apply_config_preset("cheats"))
        preset_layout.addWidget(self.cheats_preset_btn)
        
        self.performance_preset_btn = QPushButton("Performance")
        self.performance_preset_btn.clicked.connect(lambda: self._apply_config_preset("performance"))
        preset_layout.addWidget(self.performance_preset_btn)
        
        self.ultra_preset_btn = QPushButton("Ultra Graphics")
        self.ultra_preset_btn.clicked.connect(lambda: self._apply_config_preset("ultra"))
        preset_layout.addWidget(self.ultra_preset_btn)
        
        layout.addLayout(preset_layout)
        
        # Config values
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabels(["Option", "Value", "Description"])
        layout.addWidget(QLabel("Configuration Options:"))
        layout.addWidget(self.config_tree)
        
        widget.setLayout(layout)
        return widget
    
    # ESF Editor methods
    
    def _open_esf_file(self) -> None:
        """Open ESF save file."""
        save_dir = get_save_game_directory()
        if not save_dir:
            save_dir = None
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Save Game",
            str(save_dir) if save_dir else "",
            "ESF Files (*.esf);;All Files (*)"
        )
        
        if file_path:
            if self.esf_editor.load_file(file_path):
                self.esf_file_label.setText(f"Loaded: {file_path}")
                self.esf_save_btn.setEnabled(True)
                self.esf_save_btn.setToolTip("")
                self._populate_esf_tree()
    
    def _save_esf_file(self) -> None:
        """Save ESF file."""
        if self.esf_editor.save_file():
            QMessageBox.information(self, "Success", "Save game updated successfully")
    
    def _export_esf_xml(self) -> None:
        """Export ESF to XML."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to XML",
            "",
            "XML Files (*.xml);;All Files (*)"
        )
        
        if file_path:
            xml_content = self.esf_editor.to_xml()
            with open(file_path, 'w') as f:
                f.write(xml_content)
            QMessageBox.information(self, "Success", f"Exported to {file_path}")
    
    def _populate_esf_tree(self) -> None:
        """Populate ESF tree view."""
        self.esf_tree.clear()
        
        if self.esf_editor.root:
            for child in self.esf_editor.root.children:
                item = self._create_tree_item(child)
                if item:
                    self.esf_tree.addTopLevelItem(item)
    
    def _create_tree_item(self, node) -> QTreeWidgetItem:
        """Create tree item from ESF node."""
        item = QTreeWidgetItem()
        item.setText(0, node.name)
        
        if node.value is not None:
            item.setText(1, str(node.value))
        
        item.setText(2, node.node_type.value)
        
        # Add children
        for child in node.children:
            child_item = self._create_tree_item(child)
            if child_item:
                item.addChild(child_item)
        
        return item
    
    def _apply_esf_edit(self) -> None:
        """Apply edit to selected ESF node."""
        selected = self.esf_tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "No node selected")
            return
        
        new_value = self.esf_value_edit.text()
        # Would apply edit to selected node
    
    # Script Editor methods
    
    def _open_script_file(self) -> None:
        """Open script file."""
        scripts_dir = get_scripts_directory()
        if not scripts_dir:
            scripts_dir = None
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Script",
            str(scripts_dir) if scripts_dir else "",
            "Lua Files (*.lua);;All Files (*)"
        )
        
        if file_path:
            if self.script_editor.load_file(file_path):
                self.script_file_label.setText(f"Loaded: {file_path}")
                self.script_save_btn.setEnabled(True)
                self.script_save_btn.setToolTip("")
                self.script_editor_widget.setText(self.script_editor.content)
    
    def _save_script_file(self) -> None:
        """Save script file."""
        # Update content from editor
        self.script_editor.content = self.script_editor_widget.toPlainText()
        
        if self.script_editor.save_file():
            QMessageBox.information(self, "Success", "Script saved successfully")
    
    def _revert_script(self) -> None:
        """Revert script changes."""
        if self.script_editor.revert_changes():
            self.script_editor_widget.setText(self.script_editor.content)
            # Reverting does not remove the file, so it should still be loaded.
            # In file_editor_tab.py, if we reverted, we could disable save if not modified,
            # but setting enabled to False with tooltip is consistent with the original design.
            self.script_save_btn.setEnabled(False)
            self.script_save_btn.setToolTip("No unsaved changes")
    
    def _set_treasury(self) -> None:
        """Set treasury quick edit."""
        if self.script_editor.modify_faction_treasury('france', 999999):
            self.script_editor_widget.setText(self.script_editor.content)
            self.script_save_btn.setEnabled(True)
    
    def _disable_fog(self) -> None:
        """Disable fog of war."""
        if self.script_editor.disable_fog_of_war():
            self.script_editor_widget.setText(self.script_editor.content)
            self.script_save_btn.setEnabled(True)
    
    # Config Editor methods
    
    def _open_config_file(self) -> None:
        """Open config file."""
        if self.config_editor.load_file():
            self.script_file_label.setText("Loaded: preferences.script")
            self.config_save_btn.setEnabled(True)
            self.config_save_btn.setToolTip("")
            self._populate_config_tree()
    
    def _save_config_file(self) -> None:
        """Save config file."""
        if self.config_editor.save_file():
            QMessageBox.information(self, "Success", "Configuration saved")
    
    def _reset_config(self) -> None:
        """Reset config to defaults."""
        if self.config_editor.reset_to_defaults():
            self._populate_config_tree()
    
    def _apply_config_preset(self, preset_name: str) -> None:
        """Apply configuration preset."""
        if self.config_editor.apply_preset(preset_name):
            self._populate_config_tree()
    
    def _populate_config_tree(self) -> None:
        """Populate config tree view."""
        self.config_tree.clear()
        
        values = self.config_editor.get_all_values()
        
        for key, value in values.items():
            item = QTreeWidgetItem()
            item.setText(0, key)
            item.setText(1, str(value))
            
            # Get description if available
            if key in self.config_editor.KNOWN_OPTIONS:
                opt = self.config_editor.KNOWN_OPTIONS[key]
                item.setText(2, opt.description)
            
            self.config_tree.addTopLevelItem(item)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.esf_editor.close()
        self.script_editor.close()
        self.config_editor.close()
