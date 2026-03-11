"""
Trainer tab for the GUI.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QCheckBox, QGroupBox, QGridLayout, QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.memory import ProcessManager, MemoryScanner, CheatManager, CheatType
import os
from src.utils.platform import check_memory_access_permissions, get_linux_permission_commands, get_platform
from src.trainer import HotkeyManager, TrainerCheats


class TrainerTab(QWidget):
    """
    Trainer tab widget for hotkey-activated cheats.
    """
    
    def __init__(self):
        """Initialize trainer tab."""
        super().__init__()
        
        self.process_manager = ProcessManager()
        self.scanner = MemoryScanner(self.process_manager)
        self.cheat_manager = CheatManager(self.scanner)
        self.hotkey_manager = HotkeyManager()
        self.trainer_cheats = TrainerCheats(self.cheat_manager)
        
        self.cheat_checkboxes = {}
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_cheat_status)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Process attachment
        process_group = self._create_process_group()
        layout.addWidget(process_group)
        
        # Campaign cheats
        campaign_group = self._create_campaign_cheats_group()
        layout.addWidget(campaign_group)
        
        # Battle cheats
        battle_group = self._create_battle_cheats_group()
        layout.addWidget(battle_group)
        
        # Hotkey info
        hotkey_group = self._create_hotkey_info_group()
        layout.addWidget(hotkey_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.activate_all_btn = QPushButton("Activate All Cheats")
        self.activate_all_btn.clicked.connect(self._activate_all_cheats)
        control_layout.addWidget(self.activate_all_btn)
        
        self.deactivate_all_btn = QPushButton("Deactivate All Cheats")
        self.deactivate_all_btn.clicked.connect(self._deactivate_all_cheats)
        control_layout.addWidget(self.deactivate_all_btn)

        self.repair_hooks_btn = QPushButton("Repair All Hooks")
        self.repair_hooks_btn.clicked.connect(self._repair_all_hooks)
        self.repair_hooks_btn.setEnabled(False)
        control_layout.addWidget(self.repair_hooks_btn)
        
        layout.addLayout(control_layout)
        
        # Status label
        self.status_label = QLabel("Trainer inactive")
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(self.status_label)

        # Hook status label
        self.hook_status_label = QLabel("")
        self.hook_status_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(self.hook_status_label)
        
        self.setLayout(layout)
        
        # Start status update timer
        self.update_timer.start(1000)  # Update every second
    
    def _create_process_group(self) -> QGroupBox:
        """Create process attachment group."""
        group = QGroupBox("Game Process")
        layout = QHBoxLayout()
        
        self.trainer_status_label = QLabel("Status: Not attached")
        layout.addWidget(self.trainer_status_label)
        
        self.trainer_attach_btn = QPushButton("Attach to Game")
        self.trainer_attach_btn.clicked.connect(self._attach_trainer)
        layout.addWidget(self.trainer_attach_btn)
        
        self.trainer_detach_btn = QPushButton("Detach")
        self.trainer_detach_btn.clicked.connect(self._detach_trainer)
        self.trainer_detach_btn.setEnabled(False)
        self.trainer_detach_btn.setToolTip("Attach to a game process first to detach")
        layout.addWidget(self.trainer_detach_btn)
        
        self.start_hotkeys_btn = QPushButton("Start Hotkeys")
        self.start_hotkeys_btn.clicked.connect(self._start_hotkeys)
        self.start_hotkeys_btn.setEnabled(False)
        self.start_hotkeys_btn.setToolTip("Attach to a game process first to use hotkeys")
        layout.addWidget(self.start_hotkeys_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_campaign_cheats_group(self) -> QGroupBox:
        """Create campaign cheats group."""
        group = QGroupBox("Campaign Cheats")
        layout = QGridLayout()
        
        campaign_cheats = [
            ("Infinite Gold", CheatType.INFINITE_GOLD, "F2 (with Shift)"),
            ("Unlimited Movement", CheatType.UNLIMITED_MOVEMENT, "F3 (with Shift)"),
            ("Instant Construction", CheatType.INSTANT_CONSTRUCTION, "F4 (with Shift)"),
            ("Fast Research", CheatType.FAST_RESEARCH, "F5 (with Shift)"),
        ]
        
        for i, (name, cheat_type, hotkey) in enumerate(campaign_cheats):
            checkbox = QCheckBox(name)
            checkbox.setToolTip(f"Hotkey: {hotkey}")
            checkbox.stateChanged.connect(
                lambda state, ct=cheat_type: self._on_cheat_toggled(ct, state)
            )
            
            layout.addWidget(checkbox, i // 2, i % 2)
            self.cheat_checkboxes[cheat_type] = checkbox
        
        group.setLayout(layout)
        return group
    
    def _create_battle_cheats_group(self) -> QGroupBox:
        """Create battle cheats group."""
        group = QGroupBox("Battle Cheats")
        layout = QGridLayout()
        
        battle_cheats = [
            ("God Mode", CheatType.GOD_MODE, "F1 (with Ctrl)"),
            ("Unlimited Ammo", CheatType.UNLIMITED_AMMO, "F2 (with Ctrl)"),
            ("High Morale", CheatType.HIGH_MORALE, "F3 (with Ctrl)"),
            ("Infinite Stamina", CheatType.INFINITE_STAMINA, "F4 (with Ctrl)"),
            ("One-Hit Kill", CheatType.ONE_HIT_KILL, "F5 (with Ctrl)"),
            ("Super Speed", CheatType.SUPER_SPEED, "F6 (with Ctrl)"),
        ]
        
        for i, (name, cheat_type, hotkey) in enumerate(battle_cheats):
            checkbox = QCheckBox(name)
            checkbox.setToolTip(f"Hotkey: {hotkey}")
            checkbox.stateChanged.connect(
                lambda state, ct=cheat_type: self._on_cheat_toggled(ct, state)
            )
            
            layout.addWidget(checkbox, i // 3, i % 3)
            self.cheat_checkboxes[cheat_type] = checkbox
        
        group.setLayout(layout)
        return group
    
    def _create_hotkey_info_group(self) -> QGroupBox:
        """Create hotkey information group."""
        group = QGroupBox("Hotkey Reference")
        layout = QVBoxLayout()
        
        info_text = """
        <b>Campaign Cheats (hold Shift + key):</b><br>
        Shift+F2 - Infinite Gold<br>
        Shift+F3 - Unlimited Movement<br>
        Shift+F4 - Instant Construction<br>
        Shift+F5 - Fast Research<br><br>
        
        <b>Battle Cheats (hold Ctrl + key):</b><br>
        Ctrl+F1 - God Mode<br>
        Ctrl+F2 - Unlimited Ammo<br>
        Ctrl+F3 - High Morale<br>
        Ctrl+F4 - Infinite Stamina<br>
        Ctrl+F5 - One-Hit Kill<br>
        Ctrl+F6 - Super Speed
        """
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        group.setLayout(layout)
        return group
    
    def _attach_trainer(self) -> None:
        """Attach trainer to game process."""
        if self.scanner.attach():
            # Check permissions on Linux
            if get_platform() == 'linux':
                perms = check_memory_access_permissions()
                if not perms.get('can_write', False):
                    cmds = get_linux_permission_commands(self.process_manager.process_name)
                    msg = "Attached successfully, but memory write access is denied.\n\n"
                    msg += "This is common on Linux due to ptrace restrictions.\n\n"
                    msg += "To fix this, you can run the application with elevated privileges:\n"
                    if 'sudo' in cmds:
                        msg += f"  {cmds['sudo']}\n"
                    if 'pkexec' in cmds:
                        msg += f"  {cmds['pkexec']}\n"
                    if 'setcap' in cmds:
                        msg += f"Or grant capabilities:\n  {cmds['setcap']}\n"

                    msg += "\nWould you like to save these commands to a script to run separately?"

                    reply = QMessageBox.question(
                        self, "Permission Denied", msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        import os
                        script_path = os.path.join(os.getcwd(), "fix_permissions.sh")
                        with open(script_path, "w") as script_file:
                            script_file.write("#!/bin/bash\n")
                            if 'setcap' in cmds:
                                script_file.write(f"{cmds['setcap']}\n")
                            else:
                                script_file.write(f"{cmds.get('sudo', cmds.get('pkexec', ''))}\n")
                        os.chmod(script_path, 0o755)
                        QMessageBox.information(self, "Success", f"Saved commands to {script_path}")

            self.trainer_status_label.setText(f"Status: Attached to {self.process_manager.process_name}")
            self.trainer_attach_btn.setEnabled(False)
            self.trainer_attach_btn.setToolTip("Already attached to a process")
            self.trainer_detach_btn.setEnabled(True)
            self.trainer_detach_btn.setToolTip("")
            self.start_hotkeys_btn.setEnabled(True)
            self.start_hotkeys_btn.setToolTip("")
            self.repair_hooks_btn.setEnabled(True)
            self.status_label.setText("Trainer ready - attach successful")
            self.status_label.setStyleSheet("color: #00ff00;")
        else:
            QMessageBox.warning(self, "Error", "Failed to attach to game process. Is it running?")

    def _detach_trainer(self) -> None:
        """Detach trainer from game."""
        self._deactivate_all_cheats()
        self.hotkey_manager.stop()
        
        self.scanner.detach()
        self.trainer_status_label.setText("Status: Not attached")
        self.trainer_attach_btn.setEnabled(True)
        self.trainer_attach_btn.setToolTip("")
        self.trainer_detach_btn.setEnabled(False)
        self.trainer_detach_btn.setToolTip("Attach to a game process first to detach")
        self.start_hotkeys_btn.setEnabled(False)
        self.start_hotkeys_btn.setToolTip("Attach to a game process first to use hotkeys")
        self.repair_hooks_btn.setEnabled(False)
        self.status_label.setText("Trainer detached")
        self.status_label.setStyleSheet("color: #888888;")
        self.hook_status_label.setText("")
    
    def _start_hotkeys(self) -> None:
        """Start hotkey listener."""
        if self.hotkey_manager.start():
            self.trainer_cheats.setup_default_cheat_hotkeys(self.cheat_manager)
            self.status_label.setText("Hotkeys active")
            self.status_label.setStyleSheet("color: #00ff00;")
            QMessageBox.information(
                self,
                "Hotkeys Active",
                "Hotkey listener started. Use the hotkeys in-game to activate cheats."
            )
    
    def _on_cheat_toggled(self, cheat_type: CheatType, state) -> None:
        """Handle cheat checkbox toggle."""
        is_active = state == Qt.CheckState.Checked.value if hasattr(Qt, 'CheckState') else state == 2
        
        if is_active:
            # Activate cheat
            success = self.cheat_manager.activate_cheat(cheat_type)
            if success:
                cheat_def = self.cheat_manager._get_cheat_definition(cheat_type)
                if cheat_def and cheat_def.name in self.cheat_manager.memory_scanner.ml_predictor.models:
                     self.status_label.setText(f"Activated (ML Assisted): {cheat_type.value}")
                else:
                     self.status_label.setText(f"Activated: {cheat_type.value}")
            else:
                # Need address - show message
                QMessageBox.warning(
                    self,
                    "Address Required",
                    f"This cheat requires a memory address.\n\n"
                    f"Use the Memory Scanner to find the address first, "
                    f"then click 'Learn Selected Address' to teach the ML model "
                    f"or right-click to 'Set for this Cheat'."
                )
                self.cheat_checkboxes[cheat_type].setChecked(False)
        else:
            # Deactivate cheat
            self.cheat_manager.deactivate_cheat(cheat_type)
            self.status_label.setText(f"Deactivated: {cheat_type.value}")
    
    def _activate_all_cheats(self) -> None:
        """Activate all cheats."""
        self.trainer_cheats.activate_all_campaign_cheats()
        self.trainer_cheats.activate_all_battle_cheats()
        
        # Update checkboxes
        for cheat_type in self.cheat_checkboxes.keys():
            if self.cheat_manager.is_cheat_active(cheat_type):
                self.cheat_checkboxes[cheat_type].setChecked(True)
        
        self.status_label.setText("All cheats activated")
        self.status_label.setStyleSheet("color: #00ff00;")
    
    def _deactivate_all_cheats(self) -> None:
        """Deactivate all cheats."""
        self.trainer_cheats.deactivate_all_cheats()
        
        # Update checkboxes
        for checkbox in self.cheat_checkboxes.values():
            checkbox.setChecked(False)
        
        self.status_label.setText("All cheats deactivated")
        self.status_label.setStyleSheet("color: #ff4444;")
    
    def _repair_all_hooks(self) -> None:
        """Manually trigger hook validation and repair."""
        if not self.scanner.is_attached():
            return

        status = self.cheat_manager.validate_hooks(repair=True)
        restored = sum(1 for s in status.values() if s == 'restored')
        corrupted = sum(1 for s in status.values() if s == 'corrupted')

        if restored > 0 or corrupted > 0:
            msg = f"Hook repair complete.\nRestored: {restored}\nFailed to restore: {corrupted}"
            if corrupted > 0:
                QMessageBox.warning(self, "Hook Repair", msg)
            else:
                QMessageBox.information(self, "Hook Repair", msg)
        else:
            QMessageBox.information(self, "Hook Repair", "All hooks are intact. No repair needed.")
    
    def _update_cheat_status(self) -> None:
        """Update cheat status display."""
        was_attached = getattr(self, '_was_attached', False)
        is_attached = self.scanner.is_attached()

        self._was_attached = is_attached

        if was_attached and not is_attached:
            # Game crashed or was closed
            self._handle_process_crash()
            return

        active_cheats = self.trainer_cheats.get_active_cheats()
        
        if active_cheats:
            self.status_label.setText(f"Active cheats: {len(active_cheats)}")
            self.status_label.setStyleSheet("color: #00ff00;")
        else:
            if is_attached:
                self.status_label.setText("Trainer active - no cheats enabled")
                self.status_label.setStyleSheet("color: #ffaa00;")
            else:
                self.status_label.setText("Trainer inactive")
                self.status_label.setStyleSheet("color: #888888;")
                self.hook_status_label.setText("")

        # Update hook status
        if is_attached:
            hook_status = self.cheat_manager.validate_hooks(repair=False)
            corrupted = sum(1 for s in hook_status.values() if s == 'corrupted')
            total = len(hook_status)

            if total == 0:
                self.hook_status_label.setText("No active hooks")
                self.hook_status_label.setStyleSheet("color: #888888;")
            elif corrupted > 0:
                self.hook_status_label.setText(f"Warning: {corrupted}/{total} hooks corrupted! Click 'Repair All Hooks'")
                self.hook_status_label.setStyleSheet("color: #ff4444;")
            else:
                self.hook_status_label.setText(f"All hooks active ({total})")
                self.hook_status_label.setStyleSheet("color: #00ff00;")

    def _handle_process_crash(self) -> None:
        """Handle game process unexpected detachment."""
        active_count = len(self.cheat_manager.active_cheats)
        if active_count > 0:
            self.cheat_manager.save_active_cheats_state()

            # Show one-click restore prompt
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Process Lost")
            msg.setText(f"Game process has terminated unexpectedly.\n{active_count} cheats were active.")

            restore_btn = msg.addButton("Re-attach and Restore", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg.addButton("Dismiss", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            if msg.clickedButton() == restore_btn:
                self._reattach_and_restore()
            else:
                self._detach_trainer()
        else:
            self._detach_trainer()

    def _reattach_and_restore(self) -> None:
        """Attempt to re-attach to game and restore cheats."""
        if self.scanner.attach():
            self.trainer_status_label.setText(f"Status: Attached to {self.process_manager.process_name}")
            self.trainer_attach_btn.setEnabled(False)
            self.trainer_detach_btn.setEnabled(True)
            self.start_hotkeys_btn.setEnabled(True)

            restored = self.cheat_manager.restore_saved_cheats()
            self.status_label.setText(f"Trainer ready - {restored} cheats restored")
            self.status_label.setStyleSheet("color: #00ff00;")

            # Update checkboxes
            self._sync_checkboxes_with_manager()
        else:
            QMessageBox.warning(self, "Error", "Failed to attach to game process. Is it running?")
            self._detach_trainer()

    def _sync_checkboxes_with_manager(self) -> None:
        """Update checkboxes to match current cheat state."""
        for cheat_type, checkbox in self.cheat_checkboxes.items():
            is_active = self.cheat_manager.is_cheat_active(cheat_type)
            checkbox.blockSignals(True)
            checkbox.setChecked(is_active)
            checkbox.blockSignals(False)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.update_timer.stop()
        self.hotkey_manager.stop()
        if hasattr(self.cheat_manager, 'stop_validation_thread'):
            self.cheat_manager.stop_validation_thread()
        self.scanner.detach()


class CheatStatusWidget(QWidget):
    """Widget showing individual cheat status."""
    
    def __init__(self, name: str, hotkey: str, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout()
        
        self.checkbox = QCheckBox(name)
        layout.addWidget(self.checkbox)
        
        hotkey_label = QLabel(f"({hotkey})")
        hotkey_label.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(hotkey_label)
        
        self.setLayout(layout)
