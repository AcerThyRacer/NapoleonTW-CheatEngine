import re

with open("src/gui/memory_tab.py", "r") as f:
    content = f.read()

# Fix syntax error properly
import ast

def fix_string(match):
    lines = match.group(0).split('\n')
    fixed_lines = []
    for line in lines:
        if line.endswith('"') and not line.endswith('\\"'):
            fixed_lines.append(line)
        elif line.strip():
            fixed_lines.append(line + '\\n"')

    return '\n'.join(fixed_lines)

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

                    msg += "\\nWould you like to save these commands to a script to run separately?"

                    if PYQT_AVAILABLE:
                        reply = QMessageBox.question(
                            self, "Permission Denied", msg,
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            script_path = os.path.join(os.getcwd(), "fix_permissions.sh")
                            with open(script_path, "w") as script_file:
                                script_file.write("#!/bin/bash\\n")
                                if 'setcap' in cmds:
                                    script_file.write(f"{cmds['setcap']}\\n")
                                else:
                                    script_file.write(f"{cmds.get('sudo', cmds.get('pkexec', ''))}\\n")
                            os.chmod(script_path, 0o755)
                            self._show_info(f"Saved commands to {script_path}")
                    else:
                        print(msg)

            self.process_label.setText(f"Status: Attached to {self.process_manager.process_name}")
            self.attach_btn.setEnabled(False)
            self.detach_btn.setEnabled(True)
            self._update_scan_buttons_state(True)
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("Attached to process")
        else:
            self._show_error("Failed to attach to process. Is the game running?")"""

content = re.sub(
    r'    def _attach_to_process\(self\) -> None:.*?(?=    def _detach_from_process)',
    new_attach + '\n\n',
    content,
    flags=re.DOTALL
)

with open("src/gui/memory_tab.py", "w") as f:
    f.write(content)

with open("src/gui/trainer_tab.py", "r") as f:
    content = f.read()

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

                    msg += "\\nWould you like to save these commands to a script to run separately?"

                    reply = QMessageBox.question(
                        self, "Permission Denied", msg,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        script_path = os.path.join(os.getcwd(), "fix_permissions.sh")
                        with open(script_path, "w") as script_file:
                            script_file.write("#!/bin/bash\\n")
                            if 'setcap' in cmds:
                                script_file.write(f"{cmds['setcap']}\\n")
                            else:
                                script_file.write(f"{cmds.get('sudo', cmds.get('pkexec', ''))}\\n")
                        os.chmod(script_path, 0o755)
                        QMessageBox.information(self, "Success", f"Saved commands to {script_path}")

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
