import re

with open("src/utils/platform.py", "r") as f:
    content = f.read()

# Add get_linux_permission_commands function
new_function = """def get_linux_permission_commands(process_name: str = "napoleon.exe") -> Dict[str, str]:
    \"\"\"Get commands to fix Linux memory access permissions.\"\"\"
    if get_platform() != 'linux':
        return {}

    script_path = os.path.abspath(sys.argv[0])

    return {
        'sudo': f"sudo python3 {script_path}",
        'pkexec': f"pkexec python3 {script_path}",
        'setcap': f"sudo setcap cap_sys_ptrace=eip $(which python3)",
        'ptrace_temp': "echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope"
    }
"""

content = content + "\n\n" + new_function

with open("src/utils/platform.py", "w") as f:
    f.write(content)
