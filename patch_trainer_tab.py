import re

with open("src/gui/trainer_tab.py", "r") as f:
    content = f.read()

# Add import for check_memory_access_permissions and get_linux_permission_commands
import_re = r'(from src\.memory import ProcessManager, MemoryScanner, CheatManager, CheatType)'
content = re.sub(
    import_re,
    r'\1\nfrom src.utils.platform import check_memory_access_permissions, get_linux_permission_commands, get_platform',
    content
)

# Modify _attach_trainer to check permissions
new_attach = """    def _attach_trainer(self) -> None:
        \"\"\"Attach trainer to game process.\"\"\"
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

                    QMessageBox.warning(self, "Imperial Command Warning", msg)

            self.trainer_status_label.setText(f"Status: Attached to {self.process_manager.process_name}")
            self.trainer_attach_btn.setEnabled(False)
            self.trainer_detach_btn.setEnabled(True)
            self.start_hotkeys_btn.setEnabled(True)
            self.status_label.setText("Trainer ready - attach successful")
            self.status_label.setStyleSheet("color: #00ff00;")
        else:
            QMessageBox.warning(self, "Error", "Failed to attach to game process. Is it running?")"""

content = re.sub(
    r'    def _attach_trainer\(self\) -> None:.*?(?=    def _detach_trainer)',
    new_attach + '\n\n',
    content,
    flags=re.DOTALL
)

with open("src/gui/trainer_tab.py", "w") as f:
    f.write(content)
