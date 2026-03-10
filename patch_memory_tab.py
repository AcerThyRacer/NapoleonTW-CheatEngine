import re

with open("src/gui/memory_tab.py", "r") as f:
    content = f.read()

# Add import for check_memory_access_permissions and get_linux_permission_commands
import_re = r'(from src\.memory import ProcessManager, MemoryScanner, ValueType, ScanType)'
content = re.sub(
    import_re,
    r'\1\nfrom src.utils.platform import check_memory_access_permissions, get_linux_permission_commands, get_platform',
    content
)

# Modify _attach_to_process to check permissions
new_attach = """    def _attach_to_process(self) -> None:
        \"\"\"Attach to Napoleon process.\"\"\"
        if self.scanner.attach():
            # Check permissions on Linux
            if get_platform() == 'linux':
                perms = check_memory_access_permissions()
                if not perms.get('can_write', False):
                    cmds = get_linux_permission_commands(self.process_manager.process_name)
                    msg = "Attached successfully, but memory write access is denied.\\n\\n"
                    msg += "This is common on Linux due to ptrace restrictions.\\n\\n"
                    msg += "To fix this, you can run the application with elevated privileges:\\n"
                    if 'sudo' in cmds:
                        msg += f"  {cmds['sudo']}\\n"
                    if 'pkexec' in cmds:
                        msg += f"  {cmds['pkexec']}\\n"
                    if 'setcap' in cmds:
                        msg += f"Or grant capabilities:\\n  {cmds['setcap']}\\n"

                    self._show_warning(msg)

            self.process_label.setText(f"Status: Attached to {self.process_manager.process_name}")
            self.attach_btn.setEnabled(False)
            self.detach_btn.setEnabled(True)
            self._update_scan_buttons_state(True)
            self.statusBar().showMessage("Attached to process") if hasattr(self, 'statusBar') else None
        else:
            self._show_error("Failed to attach to process. Is the game running?")"""

content = re.sub(
    r'    def _attach_to_process\(self\) -> None:.*?(?=    def _detach_from_process)',
    new_attach + '\n\n',
    content,
    flags=re.DOTALL
)

# Add _show_warning method
new_warning = """    def _show_warning(self, message: str) -> None:
        \"\"\"Show warning message.\"\"\"
        if PYQT_AVAILABLE:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Imperial Command Warning")
            msg.setText(message)
            msg.setStyleSheet("QMessageBox { background-color: #1a252f; color: #d4af37; border: 2px solid #d4af37; } QLabel { color: #d4af37; } QPushButton { background-color: #2c3e50; color: #d4af37; border: 1px solid #d4af37; padding: 5px; }")
            msg.exec()
        else:
            print(f"WARNING: {message}")"""

content = re.sub(
    r'    def _show_info\(self, message: str\) -> None:',
    new_warning + '\n\n    def _show_info(self, message: str) -> None:',
    content
)

with open("src/gui/memory_tab.py", "w") as f:
    f.write(content)
