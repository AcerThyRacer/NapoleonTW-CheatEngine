"""
Interactive CLI for Napoleon Total War Cheat Engine.
Provides a full-featured command-line interface for all cheat engine operations.
"""

import cmd
import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger('napoleon.cli')


class InteractiveCLI(cmd.Cmd):
    """
    Interactive command-line interface for Napoleon Total War Cheat Engine.
    Supports memory scanning, file editing, trainer, and configuration.
    """
    
    intro = """
╔══════════════════════════════════════════════════════════════╗
║           👑 Napoleon Total War Cheat Engine CLI            ║
║                    Cross-Platform v2.0                       ║
╠══════════════════════════════════════════════════════════════╣
║  Type 'help' for commands, 'quit' to exit                   ║
╚══════════════════════════════════════════════════════════════╝
"""
    prompt = '👑 napoleon> '
    
    def __init__(self):
        super().__init__()
        self._process_manager = None
        self._scanner = None
        self._cheat_manager = None
        self._esf_editor = None
        self._script_editor = None
        self._config_editor = None
        self._pack_parser = None
        self._freezer = None
        self._hotkey_manager = None
        self._attached = False
    
    # ── Process Commands ────────────────────────────────────────
    
    def do_attach(self, arg):
        """Attach to Napoleon Total War process. Usage: attach [pid]"""
        try:
            from src.memory import ProcessManager, MemoryScanner, CheatManager
            from src.memory.advanced import MemoryFreezer
            
            self._process_manager = ProcessManager()
            self._scanner = MemoryScanner(self._process_manager)
            
            if arg.strip():
                pid = int(arg.strip())
                success = self._scanner.attach()
                if not success:
                    self._process_manager.attach(pid)
                    success = self._scanner.editor is not None
            else:
                success = self._scanner.attach()
            
            if success:
                self._cheat_manager = CheatManager(self._scanner)
                self._freezer = MemoryFreezer(self._scanner.editor)
                self._attached = True
                print(f"✓ Attached to: {self._process_manager.process_name} (PID: {self._process_manager.pid})")
            else:
                print("✗ Could not find Napoleon Total War. Is the game running?")
                
        except Exception as e:
            print(f"✗ Attach failed: {e}")
    
    def do_detach(self, arg):
        """Detach from the game process."""
        if self._scanner:
            self._scanner.detach()
        if self._freezer:
            self._freezer.unfreeze_all()
            self._freezer.stop()
        self._attached = False
        print("✓ Detached")
    
    def do_status(self, arg):
        """Show current status."""
        print("\n── Status ─────────────────────────────")
        print(f"  Attached: {'Yes' if self._attached else 'No'}")
        if self._attached and self._process_manager:
            info = self._process_manager.get_process_info()
            if info:
                print(f"  Process:  {info.get('name', 'N/A')} (PID: {info.get('pid', 'N/A')})")
                mem = info.get('memory_info', {})
                if mem:
                    rss_mb = mem.get('rss', 0) / (1024 * 1024)
                    print(f"  Memory:   {rss_mb:.1f} MB")
        
        if self._cheat_manager:
            active = self._cheat_manager.get_active_cheats()
            print(f"  Active cheats: {len(active)}")
            for ct in active:
                print(f"    • {ct.value}")
        
        if self._freezer:
            stats = self._freezer.get_stats()
            print(f"  Frozen addresses: {stats['total_frozen']} ({stats['active_frozen']} active)")
        
        if self._scanner and self._scanner.results:
            print(f"  Scan results: {len(self._scanner.results)}")
        print()
    
    def do_processes(self, arg):
        """List Napoleon Total War processes."""
        from src.memory import ProcessManager
        procs = ProcessManager.list_game_processes()
        if procs:
            print("\n  Found processes:")
            for p in procs:
                print(f"    PID {p['pid']}: {p['name']}")
            print()
        else:
            print("  No Napoleon Total War processes found.")
    
    # ── Memory Scanner Commands ─────────────────────────────────
    
    def do_scan(self, arg):
        """Scan for exact value. Usage: scan <value> [type]
        Types: int8, int16, int32 (default), int64, float, double"""
        if not self._check_attached():
            return
        
        parts = arg.strip().split()
        if not parts:
            print("Usage: scan <value> [int32|float|double|...]")
            return
        
        value_str = parts[0]
        type_str = parts[1] if len(parts) > 1 else 'int32'
        
        from src.memory.scanner import ValueType
        type_map = {
            'int8': ValueType.INT_8, 'int16': ValueType.INT_16,
            'int32': ValueType.INT_32, 'int64': ValueType.INT_64,
            'float': ValueType.FLOAT, 'double': ValueType.DOUBLE,
        }
        
        vtype = type_map.get(type_str, ValueType.INT_32)
        
        try:
            if type_str in ('float', 'double'):
                value = float(value_str)
            else:
                value = int(value_str)
            
            count = self._scanner.scan_exact_value(value, vtype)
            print(f"✓ Found {count} results")
        except Exception as e:
            print(f"✗ Scan failed: {e}")
    
    def do_scan_next(self, arg):
        """Filter previous results. Usage: scan_next <increased|decreased|changed|unchanged|exact VALUE>"""
        if not self._check_attached():
            return
        
        parts = arg.strip().split()
        if not parts:
            print("Usage: scan_next <increased|decreased|changed|unchanged|exact VALUE>")
            return
        
        scan_type = parts[0].lower()
        
        try:
            if scan_type == 'increased':
                count = self._scanner.scan_increased_value()
            elif scan_type == 'decreased':
                count = self._scanner.scan_decreased_value()
            elif scan_type == 'exact' and len(parts) > 1:
                from src.memory.scanner import ValueType
                count = self._scanner.scan_exact_value(int(parts[1]), ValueType.INT_32, from_scratch=False)
            else:
                print("Unknown scan type. Use: increased, decreased, exact <value>")
                return
            
            print(f"✓ Filtered to {count} results")
        except Exception as e:
            print(f"✗ Filter failed: {e}")
    
    def do_results(self, arg):
        """Show scan results. Usage: results [count]"""
        if not self._scanner or not self._scanner.results:
            print("  No scan results.")
            return
        
        if arg.strip():
            try:
                limit = int(arg.strip())
            except ValueError:
                print("Usage: results [positive count]")
                return
            if limit <= 0:
                print("Usage: results [positive count]")
                return
        else:
            limit = 20
        results = self._scanner.results[:limit]
        
        print(f"\n  Scan Results ({len(self._scanner.results)} total, showing {len(results)}):")
        for i, r in enumerate(results):
            print(f"    {i+1:3d}. 0x{r.address:08X} = {r.value} ({r.value_type.value})")
        
        remaining = len(self._scanner.results) - len(results)
        if remaining > 0:
            print(f"    ... and {remaining} more")
        print()
    
    def do_write(self, arg):
        """Write value to address. Usage: write <address> <value> [type]"""
        if not self._check_attached():
            return
        
        parts = arg.strip().split()
        if len(parts) < 2:
            print("Usage: write <address> <value> [int32|float|...]")
            return
        
        try:
            address = int(parts[0], 16) if parts[0].startswith('0x') else int(parts[0])
            value = float(parts[1]) if '.' in parts[1] else int(parts[1])
            
            from src.memory.scanner import ValueType
            type_str = parts[2] if len(parts) > 2 else 'int32'
            type_map = {
                'int32': ValueType.INT_32, 'float': ValueType.FLOAT,
                'double': ValueType.DOUBLE, 'int16': ValueType.INT_16,
            }
            vtype = type_map.get(type_str, ValueType.INT_32)
            
            success = self._scanner.write_value(address, value, vtype)
            if success:
                print(f"✓ Wrote {value} to 0x{address:08X}")
            else:
                print(f"✗ Write failed")
        except Exception as e:
            print(f"✗ Write error: {e}")
    
    def do_clear(self, arg):
        """Clear scan results."""
        if self._scanner:
            self._scanner.clear_results()
            print("✓ Results cleared")
    
    # ── Freeze Commands ─────────────────────────────────────────
    
    def do_freeze(self, arg):
        """Freeze address to value. Usage: freeze <address> <value> [type] [interval_ms]"""
        if not self._check_attached() or not self._freezer:
            return
        
        parts = arg.strip().split()
        if len(parts) < 2:
            print("Usage: freeze <address> <value> [int32|float] [interval_ms]")
            return
        
        try:
            address = int(parts[0], 16) if parts[0].startswith('0x') else int(parts[0])
            value = float(parts[1]) if '.' in parts[1] else int(parts[1])
            vtype = parts[2] if len(parts) > 2 else 'int32'
            interval = int(parts[3]) if len(parts) > 3 else 50
            
            self._freezer.freeze(address, value, vtype, interval)
            print(f"✓ Frozen 0x{address:08X} = {value} ({vtype}, {interval}ms)")
        except Exception as e:
            print(f"✗ Freeze failed: {e}")
    
    def do_unfreeze(self, arg):
        """Unfreeze an address. Usage: unfreeze <address|all>"""
        if not self._freezer:
            return
        
        if arg.strip().lower() == 'all':
            count = self._freezer.unfreeze_all()
            print(f"✓ Unfroze {count} addresses")
        else:
            try:
                address = int(arg.strip(), 16) if arg.strip().startswith('0x') else int(arg.strip())
                self._freezer.unfreeze(address)
                print(f"✓ Unfrozen 0x{address:08X}")
            except Exception as e:
                print(f"✗ Unfreeze failed: {e}")
    
    def do_frozen(self, arg):
        """List frozen addresses."""
        if not self._freezer:
            print("  No freezer active.")
            return
        
        entries = self._freezer.get_frozen_list()
        if not entries:
            print("  No frozen addresses.")
            return
        
        print("\n  Frozen Addresses:")
        for e in entries:
            status = "✓" if e['enabled'] else "✗"
            print(f"    {status} {e['address']} = {e['value']} ({e['type']}) [{e['writes']} writes]")
        print()
    
    # ── Cheat Commands ──────────────────────────────────────────
    
    def do_cheats(self, arg):
        """List all available cheats."""
        if not self._cheat_manager:
            print("  Not attached. Use 'attach' first.")
            return
        
        cheats = self._cheat_manager.get_all_cheats()
        
        print("\n  ── Campaign Cheats ──")
        for c in cheats:
            if c['mode'] == 'campaign':
                status = "✓ ACTIVE" if c['active'] else "  inactive"
                print(f"    {status}  {c['name']:25s} - {c['description']}")
        
        print("\n  ── Battle Cheats ──")
        for c in cheats:
            if c['mode'] == 'battle':
                status = "✓ ACTIVE" if c['active'] else "  inactive"
                print(f"    {status}  {c['name']:25s} - {c['description']}")
        print()
    
    def do_activate(self, arg):
        """Activate a cheat. Usage: activate <cheat_name> [address]"""
        if not self._check_attached() or not self._cheat_manager:
            return
        
        parts = arg.strip().split()
        if not parts:
            print("Usage: activate <infinite_gold|god_mode|...> [address]")
            return
        
        from src.memory.cheats import CheatType
        try:
            ct = CheatType(parts[0])
            address = int(parts[1], 16) if len(parts) > 1 else None
            success = self._cheat_manager.activate_cheat(ct, address)
            print(f"{'✓' if success else '✗'} {ct.value}: {'activated' if success else 'failed'}")
        except ValueError:
            print(f"Unknown cheat: {parts[0]}. Use 'cheats' to see options.")
    
    def do_deactivate(self, arg):
        """Deactivate a cheat. Usage: deactivate <cheat_name|all>"""
        if not self._cheat_manager:
            return
        
        if arg.strip().lower() == 'all':
            self._cheat_manager.deactivate_all_cheats()
            print("✓ All cheats deactivated")
        else:
            from src.memory.cheats import CheatType
            try:
                ct = CheatType(arg.strip())
                self._cheat_manager.deactivate_cheat(ct)
                print(f"✓ {ct.value} deactivated")
            except ValueError:
                print(f"Unknown cheat: {arg.strip()}")
    
    # ── File Editing Commands ───────────────────────────────────
    
    def do_esf_load(self, arg):
        """Load an ESF save file. Usage: esf_load <path>"""
        if not arg.strip():
            print("Usage: esf_load <path_to_esf_file>")
            return
        
        from src.files import ESFEditor
        self._esf_editor = ESFEditor()
        if self._esf_editor.load_file(arg.strip()):
            print("✓ ESF file loaded")
            if self._esf_editor.root:
                print(f"  Root children: {len(self._esf_editor.root.children)}")
        else:
            print("✗ Failed to load ESF file")
    
    def do_esf_find(self, arg):
        """Find nodes in loaded ESF. Usage: esf_find <node_name>"""
        if not self._esf_editor or not self._esf_editor.root:
            print("  No ESF file loaded. Use 'esf_load' first.")
            return
        
        results = self._esf_editor.root.find_all_by_name(arg.strip())
        print(f"\n  Found {len(results)} nodes named '{arg.strip()}':")
        for node in results[:20]:
            print(f"    {node}")
        if len(results) > 20:
            print(f"    ... and {len(results) - 20} more")
        print()
    
    def do_esf_set(self, arg):
        """Set a node value. Usage: esf_set <node_name> <value>"""
        if not self._esf_editor or not self._esf_editor.root:
            print("  No ESF file loaded.")
            return
        
        parts = arg.strip().split(None, 1)
        if len(parts) < 2:
            print("Usage: esf_set <node_name> <value>")
            return
        
        nodes = self._esf_editor.root.find_all_by_name(parts[0])
        if not nodes:
            print(f"  No nodes named '{parts[0]}' found.")
            return
        
        count = 0
        for node in nodes:
            if node.set_value(parts[1]):
                count += 1
        print(f"✓ Updated {count}/{len(nodes)} nodes")
    
    def do_esf_save(self, arg):
        """Save the ESF file. Usage: esf_save [output_path]"""
        if not self._esf_editor:
            print("  No ESF file loaded.")
            return
        
        path = arg.strip() if arg.strip() else None
        if self._esf_editor.save_file(path):
            print("✓ ESF file saved")
        else:
            print("✗ Save failed")
    
    def do_script_load(self, arg):
        """Load a Lua script. Usage: script_load <path>"""
        from src.files import ScriptEditor
        self._script_editor = ScriptEditor()
        if self._script_editor.load_file(arg.strip()):
            print(f"✓ Script loaded ({len(self._script_editor.content)} bytes)")
        else:
            print("✗ Failed to load script")
    
    def do_pack_load(self, arg):
        """Load a .pack file. Usage: pack_load <path>"""
        from src.pack import PackParser
        self._pack_parser = PackParser()
        if self._pack_parser.load_file(arg.strip()):
            print(f"✓ Pack loaded ({len(self._pack_parser.files)} files)")
        else:
            print("✗ Failed to load pack")
    
    def do_pack_list(self, arg):
        """List files in loaded pack. Usage: pack_list [pattern]"""
        if not self._pack_parser:
            print("  No pack loaded. Use 'pack_load' first.")
            return
        
        pattern = arg.strip() if arg.strip() else None
        files = self._pack_parser.list_files(pattern)
        
        print(f"\n  Files ({len(files)}):")
        for f in files[:50]:
            info = self._pack_parser.get_file_info(f)
            size = info.size if info else 0
            print(f"    {f} ({size:,} bytes)")
        if len(files) > 50:
            print(f"    ... and {len(files) - 50} more")
        print()
    
    def do_pack_extract(self, arg):
        """Extract from pack. Usage: pack_extract <file_path> [output_dir]"""
        if not self._pack_parser:
            print("  No pack loaded.")
            return
        
        parts = arg.strip().split(None, 1)
        if not parts:
            print("Usage: pack_extract <file_path|all> [output_dir]")
            return
        
        if parts[0] == 'all':
            out_dir = parts[1] if len(parts) > 1 else './extracted'
            self._pack_parser.extract_all(out_dir)
        else:
            data = self._pack_parser.extract_file(parts[0])
            if data:
                out_path = parts[1] if len(parts) > 1 else Path(parts[0]).name
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, 'wb') as f:
                    f.write(data)
                print(f"✓ Extracted to {out_path} ({len(data):,} bytes)")
            else:
                print("✗ File not found in pack")
    
    # ── Configuration Commands ──────────────────────────────────
    
    def do_config_load(self, arg):
        """Load preferences.script. Usage: config_load [path]"""
        from src.files import ConfigEditor
        self._config_editor = ConfigEditor()
        if self._config_editor.load_file(arg.strip() if arg.strip() else None):
            vals = self._config_editor.get_all_values()
            print(f"✓ Config loaded ({len(vals)} values)")
        else:
            print("✗ Failed to load config")
    
    def do_config_set(self, arg):
        """Set config value. Usage: config_set <key> <value>"""
        if not self._config_editor:
            print("  No config loaded.")
            return
        
        parts = arg.strip().split(None, 1)
        if len(parts) < 2:
            print("Usage: config_set <key> <value>")
            return
        
        self._config_editor.set_value(parts[0], self._config_editor._parse_value(parts[1]))
    
    def do_config_show(self, arg):
        """Show all config values."""
        if not self._config_editor:
            print("  No config loaded.")
            return
        
        vals = self._config_editor.get_all_values()
        print(f"\n  Configuration ({len(vals)} values):")
        for k, v in sorted(vals.items()):
            print(f"    {k:35s} = {v}")
        print()
    
    def do_config_save(self, arg):
        """Save config. Usage: config_save [path]"""
        if not self._config_editor:
            return
        self._config_editor.save_file(arg.strip() if arg.strip() else None)
    
    def do_config_preset(self, arg):
        """Apply preset. Usage: config_preset <cheats|performance|ultra>"""
        if not self._config_editor:
            print("  No config loaded.")
            return
        self._config_editor.apply_preset(arg.strip())
    
    # ── Trainer Commands ────────────────────────────────────────
    
    def do_trainer_start(self, arg):
        """Start hotkey trainer."""
        if not self._check_attached():
            return
        
        from src.trainer import HotkeyManager
        from src.trainer.hotkeys import CheatHotkeys
        
        self._hotkey_manager = HotkeyManager()
        cheat_hotkeys = CheatHotkeys(self._hotkey_manager)
        cheat_hotkeys.setup_default_cheat_hotkeys(self._cheat_manager)
        self._hotkey_manager.start()
        
        print("✓ Trainer started. Hotkeys active:")
        print("  Campaign (Shift+key): F2=Gold, F3=Movement, F4=Build, F5=Research")
        print("  Battle (Ctrl+key):    F1=God, F2=Ammo, F3=Morale, F4=Stamina, F5=Kill, F6=Speed")
    
    def do_trainer_stop(self, arg):
        """Stop hotkey trainer."""
        if self._hotkey_manager:
            self._hotkey_manager.stop()
            print("✓ Trainer stopped")
    
    # ── Path Detection Commands ─────────────────────────────────
    
    def do_paths(self, arg):
        """Show detected game paths."""
        from src.utils.platform import (
            get_platform, get_steam_path, get_napoleon_install_path,
            get_save_game_directory, get_scripts_directory, get_game_data_path,
            is_proton, check_memory_access_permissions, detect_display_server,
            get_hotkey_compatibility_warning
        )
        permissions = check_memory_access_permissions()
        hotkey_warning = get_hotkey_compatibility_warning()

        print(f"\n  Platform:     {get_platform()}")
        print(f"  Proton:       {is_proton()}")
        print(f"  Display:      {detect_display_server()}")
        print(f"  Steam:        {get_steam_path() or 'Not found'}")
        print(f"  Game Install: {get_napoleon_install_path() or 'Not found'}")
        print(f"  Save Games:   {get_save_game_directory() or 'Not found'}")
        print(f"  Scripts:      {get_scripts_directory() or 'Not found'}")
        print(f"  Game Data:    {get_game_data_path() or 'Not found'}")
        if get_platform() == 'linux':
            print(f"  Mem Read:     {permissions['can_read']}")
            print(f"  Mem Write:    {permissions['can_write']}")
            print(f"  ptrace_scope: {permissions['ptrace_scope'] if permissions['ptrace_scope'] is not None else 'unknown'}")
            for recommendation in permissions['recommendations']:
                print(f"  Note:         {recommendation}")
            if hotkey_warning:
                print(f"  Warning:      {hotkey_warning}")
        print()
    
    # ── Utility Commands ────────────────────────────────────────
    
    def do_help(self, arg):
        """Show help for commands."""
        if arg:
            super().do_help(arg)
            return
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║                     Available Commands                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ── Process ──                                               ║
║  attach [pid]          Attach to game process                ║
║  detach                Detach from process                   ║
║  status                Show current status                   ║
║  processes             List game processes                   ║
║                                                              ║
║  ── Memory Scanner ──                                        ║
║  scan <val> [type]     Scan for exact value                  ║
║  scan_next <filter>    Filter results (increased/decreased)  ║
║  results [count]       Show scan results                     ║
║  write <addr> <val>    Write value to address                ║
║  clear                 Clear scan results                    ║
║                                                              ║
║  ── Memory Freeze ──                                         ║
║  freeze <addr> <val>   Freeze address to value               ║
║  unfreeze <addr|all>   Unfreeze address(es)                  ║
║  frozen                List frozen addresses                 ║
║                                                              ║
║  ── Cheats ──                                                ║
║  cheats                List available cheats                 ║
║  activate <name>       Activate a cheat                      ║
║  deactivate <name|all> Deactivate cheat(s)                   ║
║                                                              ║
║  ── File Editing ──                                          ║
║  esf_load <path>       Load ESF save file                    ║
║  esf_find <name>       Find nodes by name                    ║
║  esf_set <name> <val>  Set node value                        ║
║  esf_save [path]       Save ESF file                         ║
║  script_load <path>    Load Lua script                       ║
║  pack_load <path>      Load .pack file                       ║
║  pack_list [pattern]   List pack contents                    ║
║  pack_extract <path>   Extract from pack                     ║
║                                                              ║
║  ── Configuration ──                                         ║
║  config_load [path]    Load preferences.script               ║
║  config_set <k> <v>    Set config value                      ║
║  config_show           Show all config values                ║
║  config_save [path]    Save config                           ║
║  config_preset <name>  Apply preset (cheats/performance)     ║
║                                                              ║
║  ── Trainer ──                                               ║
║  trainer_start         Start hotkey trainer                  ║
║  trainer_stop          Stop hotkey trainer                   ║
║                                                              ║
║  ── Other ──                                                 ║
║  paths                 Show detected game paths              ║
║  quit/exit             Exit the CLI                          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    def do_quit(self, arg):
        """Exit the CLI."""
        self._cleanup()
        print("\n👋 Au revoir!")
        return True
    
    def do_exit(self, arg):
        """Exit the CLI."""
        return self.do_quit(arg)
    
    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()
        return self.do_quit(arg)
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"  Unknown command: {line}. Type 'help' for available commands.")
    
    def emptyline(self):
        """Do nothing on empty line."""
        pass
    
    def _check_attached(self) -> bool:
        """Check if attached to process."""
        if not self._attached:
            print("  Not attached. Use 'attach' first.")
            return False
        return True
    
    def _cleanup(self):
        """Clean up resources."""
        if self._hotkey_manager:
            self._hotkey_manager.stop()
        if self._freezer:
            self._freezer.unfreeze_all()
            self._freezer.stop()
        if self._scanner:
            try:
                self._scanner.detach()
            except Exception:
                pass


def run_cli(service=None):
    """Launch the interactive CLI."""
    if service is not None:
        service.logger.debug("Launching interactive CLI")

    cli = InteractiveCLI()
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Au revoir!")
        cli._cleanup()


def main(service=None):
    """Launch the interactive CLI using the shared engine service."""
    from src.engine_service import EngineService

    active_service = service or EngineService()
    if service is None:
        return active_service.run(run_cli)
    return run_cli(active_service)
