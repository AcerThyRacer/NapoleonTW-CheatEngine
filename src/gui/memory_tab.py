"""
Memory Scanner tab for the GUI.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
        QGroupBox, QSpinBox, QDoubleSpinBox, QCheckBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.memory import ProcessManager, MemoryScanner, ValueType, ScanType


class MemoryScannerTab(QWidget):
    """
    Memory scanner tab widget.
    """
    
    def __init__(self):
        """Initialize memory scanner tab."""
        super().__init__()
        
        self.process_manager = ProcessManager()
        self.scanner = MemoryScanner(self.process_manager)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Process control group
        process_group = self._create_process_group()
        layout.addWidget(process_group)
        
        # Scan controls group
        scan_group = self._create_scan_group()
        layout.addWidget(scan_group)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Address", "Value", "Type"])
        self.results_table.horizontalHeader().stretchLastSection(True)
        layout.addWidget(QLabel("Scan Results:"))
        layout.addWidget(self.results_table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.add_selected_btn = QPushButton("Add Selected to Cheat List")
        self.add_selected_btn.clicked.connect(self._add_selected_to_cheats)
        action_layout.addWidget(self.add_selected_btn)
        
        self.clear_results_btn = QPushButton("Clear Results")
        self.clear_results_btn.clicked.connect(self._clear_results)
        action_layout.addWidget(self.clear_results_btn)
        
        layout.addLayout(action_layout)
        
        self.setLayout(layout)
    
    def _create_process_group(self) -> QGroupBox:
        """Create process control group."""
        group = QGroupBox("Process Control")
        layout = QHBoxLayout()
        
        self.process_label = QLabel("Status: Not attached")
        layout.addWidget(self.process_label)
        
        self.attach_btn = QPushButton("Attach to Process")
        self.attach_btn.clicked.connect(self._attach_to_process)
        layout.addWidget(self.attach_btn)
        
        self.detach_btn = QPushButton("Detach")
        self.detach_btn.clicked.connect(self._detach_from_process)
        self.detach_btn.setEnabled(False)
        layout.addWidget(self.detach_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_process)
        layout.addWidget(self.refresh_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_scan_group(self) -> QGroupBox:
        """Create scan controls group."""
        group = QGroupBox("Scan Controls")
        layout = QVBoxLayout()
        
        # Scan type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Scan Type:"))
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems([
            "Exact Value",
            "Increased Value",
            "Decreased Value",
            "Unknown Initial Value"
        ])
        type_layout.addWidget(self.scan_type_combo)
        layout.addLayout(type_layout)
        
        # Value type
        value_type_layout = QHBoxLayout()
        value_type_layout.addWidget(QLabel("Value Type:"))
        self.value_type_combo = QComboBox()
        self.value_type_combo.addItems([
            "4 Bytes",
            "2 Bytes",
            "1 Byte",
            "Float",
            "Double",
            "String"
        ])
        value_type_layout.addWidget(self.value_type_combo)
        layout.addLayout(value_type_layout)
        
        # Value input
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Value to Scan:"))
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter value...")
        value_layout.addWidget(self.value_input)
        layout.addLayout(value_layout)
        
        # Scan buttons
        button_layout = QHBoxLayout()
        
        self.new_scan_btn = QPushButton("New Scan")
        self.new_scan_btn.clicked.connect(self._new_scan)
        button_layout.addWidget(self.new_scan_btn)
        
        self.next_scan_btn = QPushButton("Next Scan")
        self.next_scan_btn.clicked.connect(self._next_scan)
        button_layout.addWidget(self.next_scan_btn)
        
        self.undo_scan_btn = QPushButton("Undo Scan")
        self.undo_scan_btn.clicked.connect(self._undo_scan)
        button_layout.addWidget(self.undo_scan_btn)
        
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
    
    def _attach_to_process(self) -> None:
        """Attach to Napoleon process."""
        if self.scanner.attach():
            self.process_label.setText(f"Status: Attached to {self.process_manager.process_name}")
            self.attach_btn.setEnabled(False)
            self.detach_btn.setEnabled(True)
            self.statusBar().showMessage("Attached to process") if hasattr(self, 'statusBar') else None
        else:
            self._show_error("Failed to attach to process. Is the game running?")
    
    def _detach_from_process(self) -> None:
        """Detach from process."""
        self.scanner.detach()
        self.process_label.setText("Status: Not attached")
        self.attach_btn.setEnabled(True)
        self.detach_btn.setEnabled(False)
        self._clear_results()
    
    def _refresh_process(self) -> None:
        """Refresh process status."""
        if self.scanner.is_attached():
            self.process_label.setText(f"Status: Attached to {self.process_manager.process_name}")
        else:
            self.process_label.setText("Status: Not attached")
    
    def _new_scan(self) -> None:
        """Start a new scan."""
        if not self.scanner.is_attached():
            self._show_error("Not attached to process")
            return
        
        value_str = self.value_input.text()
        value_type_str = self.value_type_combo.currentText()
        scan_type_str = self.scan_type_combo.currentText()
        
        # Convert value type
        value_type = ValueType(value_type_str)
        
        # Convert value
        try:
            if value_type == ValueType.FLOAT or value_type == ValueType.DOUBLE:
                value = float(value_str)
            elif value_type == ValueType.STRING:
                value = value_str
            else:
                value = int(value_str)
        except ValueError:
            self._show_error(f"Invalid value for type {value_type_str}")
            return
        
        # Perform scan
        from_scratch = scan_type_str == "Exact Value" or scan_type_str == "Unknown Initial Value"
        
        if scan_type_str == "Exact Value":
            count = self.scanner.scan_exact_value(value, value_type, from_scratch=True)
        elif scan_type_str == "Increased Value":
            count = self.scanner.scan_increased_value(value_type)
        elif scan_type_str == "Decreased Value":
            count = self.scanner.scan_decreased_value(value_type)
        else:
            self._show_error("Scan type not implemented yet")
            return
        
        self._update_results_table()
        self.statusBar().showMessage(f"Found {count} results") if hasattr(self, 'statusBar') else None
    
    def _next_scan(self) -> None:
        """Perform next scan (filter previous results)."""
        self._new_scan()
    
    def _undo_scan(self) -> None:
        """Undo last scan."""
        self.scanner.clear_results()
        self._update_results_table()
    
    def _update_results_table(self) -> None:
        """Update results table with scan results."""
        results = self.scanner.get_results()
        
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            addr_item = QTableWidgetItem(f"0x{result.address:08X}")
            value_item = QTableWidgetItem(str(result.value))
            type_item = QTableWidgetItem(result.value_type.value)
            
            self.results_table.setItem(i, 0, addr_item)
            self.results_table.setItem(i, 1, value_item)
            self.results_table.setItem(i, 2, type_item)
    
    def _clear_results(self) -> None:
        """Clear scan results."""
        self.scanner.clear_results()
        self.results_table.setRowCount(0)
    
    def _add_selected_to_cheats(self) -> None:
        """Add selected results to cheat list."""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            self._show_error("No rows selected")
            return
        
        # This would integrate with the cheat manager
        self._show_info(f"Would add {len(selected_rows)} addresses to cheat list")
    
    def _show_error(self, message: str) -> None:
        """Show error message."""
        print(f"ERROR: {message}")
    
    def _show_info(self, message: str) -> None:
        """Show info message."""
        print(f"INFO: {message}")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.scanner.detach()


class ScanWorker(QThread):
    """Background worker for memory scanning."""
    
    scan_complete = pyqtSignal(int)  # Number of results
    error = pyqtSignal(str)
    
    def __init__(self, scanner, value, value_type, scan_type):
        super().__init__()
        self.scanner = scanner
        self.value = value
        self.value_type = value_type
        self.scan_type = scan_type
    
    def run(self):
        try:
            if self.scan_type == ScanType.EXACT_VALUE:
                count = self.scanner.scan_exact_value(self.value, self.value_type)
            elif self.scan_type == ScanType.INCREASED_VALUE:
                count = self.scanner.scan_increased_value(self.value_type)
            elif self.scan_type == ScanType.DECREASED_VALUE:
                count = self.scanner.scan_decreased_value(self.value_type)
            else:
                self.error.emit("Unknown scan type")
                return
            
            self.scan_complete.emit(count)
        except Exception as e:
            self.error.emit(str(e))
