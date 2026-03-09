"""
Script file editor for Napoleon Total War.
Handles scripting.lua and other Lua script files.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.utils import create_backup, get_game_data_path


class ScriptEditor:
    """
    Editor for Lua script files in Napoleon Total War.
    """
    
    def __init__(self):
        """Initialize script editor."""
        self.file_path: Optional[Path] = None
        self.content: str = ""
        self.original_content: str = ""
        self.modifications: List[Dict] = []
        
    def load_file(self, file_path: str) -> bool:
        """
        Load a Lua script file.
        
        Args:
            file_path: Path to .lua file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            path = Path(file_path)
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.content = f.read()
                    self.original_content = self.content
            except FileNotFoundError:
                print(f"File not found: {file_path}")
                return False
            except PermissionError:
                print(f"Permission denied: {file_path}")
                return False
            
            self.file_path = path
            print(f"Loaded script: {path.name}")
            return True
            
        except Exception as e:
            print(f"Error loading script file: {e}")
            return False
    
    def save_file(self, output_path: Optional[str] = None) -> bool:
        """
        Save the script file.
        
        Args:
            output_path: Optional output path (default: overwrite original)
            
        Returns:
            bool: True if saved successfully
        """
        try:
            if output_path:
                path = Path(output_path)
            else:
                if not self.file_path:
                    print("No file path specified")
                    return False
                path = self.file_path
            
            # Create backup before overwriting
            if path.exists() and output_path is None:
                backup_path = create_backup(path)
                print(f"Backup created: {backup_path}")
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.content)
            
            print(f"Script saved: {path}")
            return True
            
        except Exception as e:
            print(f"Error saving script file: {e}")
            return False
    
    def revert_changes(self) -> bool:
        """
        Revert all changes to original content.
        
        Returns:
            bool: True if reverted
        """
        if not self.original_content:
            return False
        
        self.content = self.original_content
        self.modifications = []
        print("Changes reverted")
        return True
    
    def has_unsaved_changes(self) -> bool:
        """
        Check if there are unsaved changes.
        
        Returns:
            bool: True if content differs from original
        """
        return self.content != self.original_content
    
    # Campaign Script Modifications
    
    def modify_faction_treasury(
        self,
        faction_name: str,
        treasury_amount: int = 999999
    ) -> bool:
        """
        Modify faction treasury in scripting.lua.
        
        This modifies the OnFactionTurnStart function to set treasury.
        
        Args:
            faction_name: Faction identifier (e.g., 'france', 'egy_french_republic')
            treasury_amount: Amount to set
            
        Returns:
            bool: True if modification successful
        """
        # Pattern to find OnFactionTurnStart function
        pattern = r'(local function OnFactionTurnStart\(context\).+?)(\nend\n)'
        
        def replace_func(match):
            func_content = match.group(1)
            end_marker = match.group(2)
            
            # Check if faction check exists
            if faction_name in func_content:
                # Modify existing treasury assignment
                old_pattern = r'(treasury\s*=\s*)\d+'
                new_content = re.sub(old_pattern, f'\\g<1>{treasury_amount}', func_content)
                return new_content + end_marker
            else:
                # Add new faction check
                new_code = f"""
    -- Modified by Napoleon Cheat Engine
    if context.faction:name() == "{faction_name}" then
        treasury = {treasury_amount}
    end
"""
                # Insert before the end
                return func_content + new_code + end_marker
        
        new_content = re.sub(pattern, replace_func, self.content, flags=re.DOTALL)
        
        if new_content != self.content:
            self.content = new_content
            self.modifications.append({
                'type': 'treasury_mod',
                'faction': faction_name,
                'amount': treasury_amount,
            })
            print(f"Modified treasury for {faction_name} to {treasury_amount}")
            return True
        
        print("Could not find OnFactionTurnStart function")
        return False
    
    def disable_fog_of_war(self) -> bool:
        """
        Disable fog of war in campaign.
        
        Returns:
            bool: True if modification successful
        """
        # Look for fog of war settings
        patterns = [
            r'(fog_of_war\s*=\s*)true',
            r'(enable_fog\s*=\s*)true',
        ]
        
        modified = False
        for pattern in patterns:
            if re.search(pattern, self.content):
                self.content = re.sub(pattern, r'\g<1>false', self.content)
                modified = True
        
        if modified:
            self.modifications.append({'type': 'disable_fog_of_war'})
            print("Fog of war disabled")
            return True
        
        print("Fog of war setting not found")
        return False
    
    def modify_agent_action_points(self, points: int = 99) -> bool:
        """
        Modify agent action points.
        
        Args:
            points: Number of action points to set
            
        Returns:
            bool: True if successful
        """
        pattern = r'(action_points\s*=\s*)\d+'
        
        if re.search(pattern, self.content):
            self.content = re.sub(pattern, f'\\g<1>{points}', self.content)
            self.modifications.append({'type': 'agent_action_points', 'value': points})
            print(f"Agent action points set to {points}")
            return True
        
        print("Agent action points setting not found")
        return False
    
    # Battle Script Modifications
    
    def set_battle_time_limit(self, seconds: int = -1) -> bool:
        """
        Set battle time limit.
        
        Args:
            seconds: Time limit in seconds (-1 for unlimited)
            
        Returns:
            bool: True if successful
        """
        # This might be in preferences.script instead
        pattern = r'(battle_time_limit\s*=\s*)-?\d+'
        
        if re.search(pattern, self.content):
            self.content = re.sub(pattern, f'\\g<1>{seconds}', self.content)
            self.modifications.append({'type': 'battle_time_limit', 'value': seconds})
            print(f"Battle time limit set to {seconds}")
            return True
        
        return False
    
    def find_function(self, function_name: str) -> Optional[str]:
        """
        Find a function definition in the script.
        
        Args:
            function_name: Name of function to find
            
        Returns:
            Optional[str]: Function content or None if not found
        """
        pattern = rf'(local function {function_name}\([^)]*\).*?\nend\n)'
        match = re.search(pattern, self.content, re.DOTALL)
        
        if match:
            return match.group(1)
        return None
    
    def insert_code_after_function(
        self,
        function_name: str,
        code_to_insert: str
    ) -> bool:
        """
        Insert code after a specific function.
        
        Args:
            function_name: Function to insert after
            code_to_insert: Code to insert
            
        Returns:
            bool: True if successful
        """
        pattern = rf'(local function {function_name}\([^)]*\).*?\nend\n)'
        
        def replace_func(match):
            return match.group(0) + '\n' + code_to_insert + '\n'
        
        new_content = re.sub(pattern, replace_func, self.content, flags=re.DOTALL)
        
        if new_content != self.content:
            self.content = new_content
            print(f"Inserted code after {function_name}")
            return True
        
        print(f"Function {function_name} not found")
        return False
    
    def validate_syntax(self) -> Tuple[bool, str]:
        """
        Validate Lua syntax (basic check).
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        # Basic syntax checks
        errors = []
        
        # Check for balanced 'do' and 'end'
        do_count = len(re.findall(r'\bdo\b', self.content))
        end_count = len(re.findall(r'\bend\b', self.content))
        
        if do_count != end_count:
            errors.append(f"Unbalanced do/end: {do_count} do, {end_count} end")
        
        # Check for balanced 'function' and 'end'
        func_count = len(re.findall(r'\bfunction\b', self.content))
        # Note: This is approximate since 'end' is used for multiple purposes
        
        # Check for balanced parentheses (basic)
        open_parens = self.content.count('(')
        close_parens = self.content.count(')')
        
        if open_parens != close_parens:
            errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
        
        # Check for balanced braces
        open_braces = self.content.count('{')
        close_braces = self.content.count('}')
        
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        if errors:
            return False, '\n'.join(errors)
        
        return True, "Syntax appears valid"
    
    def get_modifications_summary(self) -> str:
        """
        Get summary of all modifications made.
        
        Returns:
            str: Summary string
        """
        if not self.modifications:
            return "No modifications made"
        
        lines = ["Modifications made:"]
        for mod in self.modifications:
            lines.append(f"  - {mod['type']}: {mod}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def find_campaign_scripts() -> List[Path]:
        """
        Find campaign script files.
        
        Returns:
            List[Path]: List of scripting.lua file paths
        """
        data_path = get_game_data_path()
        if not data_path:
            return []
        
        campaigns_path = data_path / 'campaigns'
        if not campaigns_path.exists():
            return []
        
        scripts = []
        for campaign_dir in campaigns_path.iterdir():
            if campaign_dir.is_dir():
                script_path = campaign_dir / 'scripting.lua'
                if script_path.exists():
                    scripts.append(script_path)
        
        return scripts
    
    def close(self) -> None:
        """Clear loaded data."""
        self.file_path = None
        self.content = ""
        self.original_content = ""
        self.modifications = []
