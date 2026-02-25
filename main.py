'''
Copyright 2026 David Wright

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sys
import os
import shutil
import subprocess
import json
import platform
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QScrollArea,
                             QLineEdit, QDialog, QMessageBox, QTextEdit,
                             QInputDialog, QListWidget, QTabWidget, QMenu, QFileDialog, QCheckBox, QFrame, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QProcess, QUrl, QSettings
from PyQt6.QtGui import QDesktopServices, QAction

# --- Helper Classes ---

class SettingsDialog(QDialog):
    def __init__(self, current_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Settings")
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Default Environments Location:</b>"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(current_path)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        btn_save = QPushButton("Save & Restart Scan")
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Venv Storage")
        if path: self.path_input.setText(path)

    def get_path(self):
        return self.path_input.text()

class VenvScanner(QThread):
    finished = pyqtSignal(list)
    def __init__(self, search_path):
        super().__init__()
        self.search_path = search_path
    def run(self):
        found_venvs = []
        if os.path.exists(self.search_path):
            for entry in os.scandir(self.search_path):
                if entry.is_dir():
                    cfg_path = os.path.join(entry.path, "pyvenv.cfg")
                    version = "Unknown"
                    size_str = "Unknown"
                    if os.path.exists(cfg_path):
                        # 1. Get Version
                        try:
                            with open(cfg_path, 'r') as f:
                                for line in f:
                                    if line.startswith("version ="):
                                        version = line.split("=")[1].strip()
                                        break
                        except Exception: pass
                        
                        # 2. Get Size
                        total_size = 0
                        try:
                            for dirpath, dirnames, filenames in os.walk(entry.path):
                                for f in filenames:
                                    fp = os.path.join(dirpath, f)
                                    if not os.path.islink(fp):
                                        total_size += os.path.getsize(fp)
                            if total_size < 1024 * 1024:
                                size_str = f"{total_size / 1024:.1f} KB"
                            elif total_size < 1024 * 1024 * 1024:
                                size_str = f"{total_size / (1024*1024):.1f} MB"
                            else:
                                size_str = f"{total_size / (1024*1024*1024):.2f} GB"
                        except Exception: pass

                        found_venvs.append({"name": entry.name, "path": entry.path, "version": version, "size": size_str})
        self.finished.emit(found_venvs)

# --- New Venv Dialog ---

class NewVenvDialog(QDialog):
    def __init__(self, base_dir, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.setWindowTitle("Create New Environment")
        self.setFixedWidth(450)
        self.setFixedHeight(350)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Page 1: Input
        self.input_page = QWidget()
        input_lay = QVBoxLayout(self.input_page)
        input_lay.setContentsMargins(0, 0, 0, 0)
        input_lay.setSpacing(8)
        
        input_lay.addWidget(QLabel("<b>Environment Name:</b>"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. my_project_env")
        input_lay.addWidget(self.name_input)

        input_lay.addWidget(QLabel("<b>Base Python Version:</b>"))
        self.version_combo = QListWidget()
        self.version_combo.setFixedHeight(100)
        self.find_pythons()
        input_lay.addWidget(self.version_combo)

        self.btn_create = QPushButton("Create Environment")
        self.btn_create.clicked.connect(self.start_creation)
        input_lay.addWidget(self.btn_create)
        self.stack.addWidget(self.input_page)

        # Page 2: Console
        self.console_page = QWidget()
        console_lay = QVBoxLayout(self.console_page)
        console_lay.setContentsMargins(0, 0, 0, 0)
        console_lay.setSpacing(8)
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background: #1e1e1e; color: #00ff00; font-family: monospace;")
        console_lay.addWidget(self.console_output)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        console_lay.addWidget(self.btn_close)
        self.stack.addWidget(self.console_page)

    def find_pythons(self):
        paths = ["/usr/bin/python3", "/usr/local/bin/python3", sys.executable]
        if os.path.isdir("/usr/bin"):
            for entry in os.scandir("/usr/bin"):
                if entry.name.startswith("python3.") and entry.is_file() and not entry.is_symlink():
                    if entry.path not in paths: paths.append(entry.path)
        
        for p in sorted(list(set(paths))):
            self.version_combo.addItem(p)
        
        if self.version_combo.count() > 0:
            self.version_combo.setCurrentRow(0)

    def start_creation(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a name for the environment.")
            return

        path = os.path.join(self.base_dir, name.replace(" ", "_"))
        if os.path.exists(path):
            QMessageBox.warning(self, "Duplicate Name", f"The environment '{name}' already exists at {path}.")
            return

        py_exe = self.version_combo.currentItem().text() if self.version_combo.currentItem() else sys.executable
        
        # Switch to console view
        self.stack.setCurrentIndex(1)
        self.setWindowTitle(f"Creating {name}...")
        
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(lambda: self.console_output.append(self.proc.readAllStandardOutput().data().decode().strip()))
        self.proc.readyReadStandardError.connect(lambda: self.console_output.append(self.proc.readAllStandardError().data().decode().strip()))
        self.proc.finished.connect(self.on_finished)
        
        self.console_output.append(f"Command: {py_exe} -m venv {path}")
        self.proc.start(py_exe, ["-m", "venv", path])

    def on_finished(self, exit_code, exit_status):
        self.btn_close.setEnabled(True)
        self.console_output.append("\n--- Creation Finished ---")
        if self.parent():
            # Trigger refresh in main window if possible
            if hasattr(self.parent(), 'refresh'):
                self.parent().refresh()

class VenvCard(QWidget):
    def __init__(self, data, linked_projects, on_link, on_terminal, on_launch, on_manage, on_unlink, on_delete, on_clone):
        super().__init__()
        self.path = data['path']
        self.name = data['name']
        self.version = data.get('version', 'Unknown')
        self.size = data.get('size', 'Unknown')
        self.linked_project_names = [os.path.basename(p) for p in linked_projects]
        
        self.setStyleSheet("""
            VenvCard { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #e0e0e0; 
                border-radius: 12px;
            }
            VenvCard:hover {
                border: 1px solid #0078d4;
                background: #f0f7ff;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #ccc;
                background: white;
            }
            QPushButton:hover {
                background: #e5e5e5;
            }
            QPushButton#deleteBtn {
                color: #d32f2f;
                border: 1px solid #ffcdd2;
            }
            QPushButton#deleteBtn:hover {
                background: #ffebee;
            }
            QLabel#nameLabel {
                font-size: 14px;
                color: #333;
            }
            QLabel#versionLabel {
                font-size: 11px;
                color: #0078d4;
                background: #e1f0ff;
                padding: 2px 6px;
                border-radius: 4px;
            }
            .ProjectRow {
                background: #fdfdfd;
                border: 1px solid #f0f0f0;
                border-radius: 5px;
                padding: 4px 8px;
            }
            .ProjectRow:hover {
                background: #f5f5f5;
            }
            QPushButton.ActionBtn {
                padding: 2px 6px;
                font-size: 11px;
                background: #fff;
                border: 1px solid #ddd;
            }
            QPushButton.ActionBtn:hover {
                background: #eee;
            }
            QPushButton.UnlinkBtn {
                color: #d32f2f;
                border: 1px solid #ffcdd2;
            }
            QPushButton.UnlinkBtn:hover {
                background: #ffebee;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header = QHBoxLayout()
        name_lbl = QLabel(f"<b>{self.name}</b>")
        name_lbl.setObjectName("nameLabel")
        header.addWidget(name_lbl)
        header.addStretch()
        
        version_lbl = QLabel(f"Python {self.version}")
        version_lbl.setObjectName("versionLabel")
        header.addWidget(version_lbl)
        layout.addLayout(header)

        info_lay = QHBoxLayout()
        project_count = len(linked_projects)
        status_text = f"🔗 {project_count} Project(s) linked" if project_count > 0 else "❌ No projects linked"
        status_lbl = QLabel(f"<small>{status_text}</small>")
        status_lbl.setStyleSheet("color: #666;")
        
        size_lbl = QLabel(f"<small>💾 {self.size}</small>")
        size_lbl.setStyleSheet("color: #666; background: #eee; padding: 2px 5px; border-radius: 3px;")
        
        info_lay.addWidget(status_lbl)
        info_lay.addStretch()
        info_lay.addWidget(size_lbl)
        layout.addLayout(info_lay)

        # Projects Listing
        if linked_projects:
            proj_list_layout = QVBoxLayout()
            proj_list_layout.setSpacing(4)
            for p_path in linked_projects:
                p_name = os.path.basename(p_path)
                p_row = QWidget()
                p_row.setProperty("class", "ProjectRow")
                p_row_lay = QHBoxLayout(p_row)
                p_row_lay.setContentsMargins(5, 5, 5, 5)
                
                p_row_lay.addWidget(QLabel(f"📁 <b>{p_name}</b> <font color='gray'><small>({p_path})</small></font>"))
                p_row_lay.addStretch()
                
                btn_run = QPushButton("🚀 Run")
                btn_run.setProperty("class", "ActionBtn")
                btn_run.clicked.connect(lambda _, p=p_path: on_launch(self.path, p))
                
                btn_term = QPushButton("💻 Term")
                btn_term.setProperty("class", "ActionBtn")
                btn_term.clicked.connect(lambda _, p=p_path: on_terminal(self.path, p))
                
                btn_unl = QPushButton("🔗 Unlink")
                btn_unl.setProperty("class", "ActionBtn UnlinkBtn")
                btn_unl.clicked.connect(lambda _, p=p_path: on_unlink(self.path, p))
                
                p_row_lay.addWidget(btn_run)
                p_row_lay.addWidget(btn_term)
                p_row_lay.addWidget(btn_unl)
                
                proj_list_layout.addWidget(p_row)
            layout.addLayout(proj_list_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        btn_link = QPushButton("Link Folder")
        btn_link.clicked.connect(lambda: on_link(self.path))

        btn_manage = QPushButton("Packages")
        btn_manage.clicked.connect(lambda: on_manage(self.path))

        btn_clone = QPushButton("Clone")
        btn_clone.clicked.connect(lambda: on_clone(self.path))

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("deleteBtn")
        btn_del.clicked.connect(lambda: on_delete(self.path))

        btn_layout.addWidget(btn_link)
        btn_layout.addWidget(btn_manage)
        btn_layout.addWidget(btn_clone)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)

class PackageManagerDialog(QDialog):
    def __init__(self, venv_path, parent=None):
        super().__init__(parent)
        self.venv_path = venv_path
        self.setWindowTitle(f"Package Manager: {os.path.basename(venv_path)}")
        self.resize(700, 750)
        self.py_exe = os.path.join(venv_path, "bin", "python") if os.name != 'nt' else os.path.join(venv_path, "Scripts", "python.exe")
        self.init_ui()
        self.refresh_installed()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. System Site Packages Toggle
        self.system_site_cb = QCheckBox("Include System Site Packages (Global Libraries)")
        self.system_site_cb.setChecked(self.get_system_site_packages_status())
        self.system_site_cb.stateChanged.connect(self.toggle_system_site_packages)
        layout.addWidget(self.system_site_cb)

        # 2. Manual Install Section
        install_layout = QHBoxLayout()
        self.pkg_input = QLineEdit()
        self.pkg_input.setPlaceholderText("Enter package name from PyPi.org ...")
        self.btn_install = QPushButton("Install")
        self.btn_install.clicked.connect(self.install_pkg)
        install_layout.addWidget(self.pkg_input)
        install_layout.addWidget(self.btn_install)
        layout.addLayout(install_layout)

        # 3. Package Tabs
        self.tabs = QTabWidget()
        
        # Project Tab
        self.project_tab = QWidget()
        proj_lay = QVBoxLayout(self.project_tab)
        
        # Tools Row
        tools_layout = QHBoxLayout()
        self.btn_bootstrap = QPushButton("🛠 Bootstrap (pip, setuptools, wheel)")
        self.btn_bootstrap.clicked.connect(self.bootstrap_tools)
        self.btn_check_updates = QPushButton("🔍 Check for Updates")
        self.btn_check_updates.clicked.connect(self.check_updates)
        tools_layout.addWidget(self.btn_bootstrap)
        tools_layout.addWidget(self.btn_check_updates)
        proj_lay.addLayout(tools_layout)

        self.project_list = QListWidget()
        self.btn_remove = QPushButton("Remove Selected Package")
        self.btn_remove.setStyleSheet("color: white; background-color: #d32f2f;")
        self.btn_remove.clicked.connect(self.uninstall_pkg)
        
        self.btn_update = QPushButton("Update Selected Package")
        self.btn_update.setStyleSheet("color: white; background-color: #0078d4;")
        self.btn_update.clicked.connect(self.update_pkg)
        self.btn_update.setEnabled(False)

        proj_lay.addWidget(self.project_list)
        btn_action_lay = QHBoxLayout()
        btn_action_lay.addWidget(self.btn_update)
        btn_action_lay.addWidget(self.btn_remove)
        proj_lay.addLayout(btn_action_lay)

        # System Tab
        self.system_tab = QWidget()
        sys_lay = QVBoxLayout(self.system_tab)
        self.system_list = QListWidget()
        sys_lay.addWidget(QLabel("<i>Global packages are read-only.</i>"))
        sys_lay.addWidget(self.system_list)

        self.tabs.addTab(self.project_tab, "Project Packages")
        self.tabs.addTab(self.system_tab, "System Packages")
        layout.addWidget(self.tabs)

        # 4. Requirements Row
        req_lay = QHBoxLayout()
        self.btn_import = QPushButton("📄 Import Requirements.txt")
        self.btn_import.clicked.connect(self.import_reqs)
        self.btn_export = QPushButton("📤 Export Requirements.txt")
        self.btn_export.clicked.connect(self.export_reqs)
        req_lay.addWidget(self.btn_import)
        req_lay.addWidget(self.btn_export)
        layout.addLayout(req_lay)

        # --- THE RESTORED CONSOLE ---
        layout.addWidget(QLabel("<b>Pip Output / Activity Log:</b>"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(150) # Fixed height so it's always visible
        self.console.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace;")
        layout.addWidget(self.console)

        # 4. Process Logic
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.handle_stdout)
        self.proc.finished.connect(self.on_finished)

    def handle_stdout(self):
        data = self.proc.readAllStandardOutput().data().decode()
        self.console.append(data)

    def on_finished(self):
        self.btn_install.setEnabled(True)
        self.btn_remove.setEnabled(True)
        self.btn_bootstrap.setEnabled(True)
        self.btn_check_updates.setEnabled(True)
        self.refresh_installed()
        self.console.append("--- Process Finished ---")

    def run_cmd(self, args):
        self.console.clear()
        self.console.append(f"Running: {os.path.basename(self.py_exe)} {' '.join(args)}...")
        self.btn_install.setEnabled(False)
        self.btn_remove.setEnabled(False)
        self.btn_bootstrap.setEnabled(False)
        self.btn_check_updates.setEnabled(False)
        self.proc.start(self.py_exe, args)

    def bootstrap_tools(self):
        self.run_cmd(["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    def check_updates(self):
        self.console.clear()
        self.console.append("Checking for updates (local packages only)...")
        self.btn_check_updates.setEnabled(False)
        
        # Use a temporary thread to run pip list --outdated to avoid freezing UI
        class UpdateChecker(QThread):
            finished = pyqtSignal(str)
            def __init__(self, py_exe):
                super().__init__()
                self.py_exe = py_exe
            def run(self):
                try:
                    res = subprocess.run([self.py_exe, "-m", "pip", "list", "--outdated", "--local", "--format=freeze"], capture_output=True, text=True)
                    self.finished.emit(res.stdout)
                except Exception as e:
                    self.finished.emit(f"Error: {str(e)}")

        self.checker = UpdateChecker(self.py_exe)
        self.checker.finished.connect(self.handle_updates_found)
        self.checker.start()

    def handle_updates_found(self, output):
        self.btn_check_updates.setEnabled(True)
        if output.startswith("Error:"):
            self.console.append(output)
            return

        lines = output.splitlines()
        if not lines:
            self.console.append("All local packages are up to date.")
            return

        self.console.append(f"Found {len(lines)} updates:")
        for line in lines:
            self.console.append(f"  - {line}")
        
        # Highlight updateable items in the list
        outdated_names = [line.split('==')[0].lower() for line in lines]
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            name = item.text().split('==')[0].lower()
            if name in outdated_names:
                item.setForeground(Qt.GlobalColor.blue)
                item.setToolTip("Update available!")
        
        self.btn_update.setEnabled(True)

    def update_pkg(self):
        if self.project_list.currentItem():
            name = self.project_list.currentItem().text().split('==')[0]
            self.run_cmd(["-m", "pip", "install", "--upgrade", name])
            self.btn_update.setEnabled(False)

    def import_reqs(self):
        file, _ = QFileDialog.getOpenFileName(self, "Import Requirements", "", "Text Files (*.txt);;All Files (*)")
        if file:
            self.run_cmd(["-m", "pip", "install", "-r", file])

    def export_reqs(self):
        file, _ = QFileDialog.getSaveFileName(self, "Export Requirements", "requirements.txt", "Text Files (*.txt);;All Files (*)")
        if file:
            # Check if we should include system packages
            include_system = QMessageBox.question(self, "Export", "Include system site-packages in export?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
            args = [self.py_exe, "-m", "pip", "freeze"]
            if not include_system: args.append("--local")
            
            try:
                res = subprocess.run(args, capture_output=True, text=True)
                with open(file, 'w') as f:
                    f.write(res.stdout)
                self.console.append(f"Exported to {file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ... (Keep the rest of the existing methods: refresh_installed, install_pkg, etc.) ...

    def get_system_site_packages_status(self):
        cfg = os.path.join(self.venv_path, "pyvenv.cfg")
        try:
            with open(cfg, 'r') as f:
                content = f.read().lower()
                return "include-system-site-packages = true" in content
        except: return False

    def toggle_system_site_packages(self, state):
        cfg = os.path.join(self.venv_path, "pyvenv.cfg")
        val = "true" if state else "false"
        try:
            with open(cfg, 'r') as f: lines = f.readlines()
            with open(cfg, 'w') as f:
                for l in lines:
                    if l.startswith("include-system-site-packages"):
                        f.write(f"include-system-site-packages = {val}\n")
                    else:
                        f.write(l)
            self.refresh_installed()
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def refresh_installed(self):
        self.project_list.clear()
        self.system_list.clear()
        try:
            local = subprocess.run([self.py_exe, "-m", "pip", "list", "--local", "--format=freeze"], capture_output=True, text=True).stdout.splitlines()
            all_pkgs = subprocess.run([self.py_exe, "-m", "pip", "list", "--format=freeze"], capture_output=True, text=True).stdout.splitlines()
            local_names = [p.split('==')[0].lower() for p in local]
            for p in local: self.project_list.addItem(p)
            for p in all_pkgs:
                if p.split('==')[0].lower() not in local_names:
                    self.system_list.addItem(p)
        except: pass

    def install_pkg(self):
        pkg = self.pkg_input.text().strip()
        if pkg: self.run_cmd(["-m", "pip", "install", pkg])

    def uninstall_pkg(self):
        if self.project_list.currentItem():
            name = self.project_list.currentItem().text().split('==')[0]
            if QMessageBox.question(self, "Confirm", f"Uninstall {name}?") == QMessageBox.StandardButton.Yes:
                self.run_cmd(["-m", "pip", "uninstall", "-y", name])

# --- Main Application Window ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Venv Manager")
        self.resize(900, 700)
        self.settings = QSettings("MyPythonTools", "VenvManager")
        self.links_file = os.path.join(os.path.dirname(__file__), "project_links.json")
        self.project_links = self.load_links()
        self.base_dir = self.settings.value("venv_path", "")
        if self.base_dir and not os.path.exists(self.base_dir): os.makedirs(self.base_dir, exist_ok=True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QHBoxLayout()
        self.loc_info = QLabel()
        self.update_loc_info()
        
        btn_settings = QPushButton("⚙ Settings")
        btn_settings.clicked.connect(self.open_settings)
        self.btn_new = QPushButton("+ Create New Venv")
        self.btn_new.clicked.connect(self.create_venv_dialog)
        self.btn_new.setEnabled(bool(self.base_dir))
        
        header.addWidget(self.loc_info); header.addStretch(); header.addWidget(btn_settings); header.addWidget(self.btn_new)
        layout.addLayout(header)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search environments...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_cards)
        self.search_input.setStyleSheet("padding: 8px; border-radius: 8px; border: 1px solid #ccc; font-size: 14px;")
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.container = QWidget(); self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(10)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        self.refresh()

    def filter_cards(self, text):
        text = text.lower()
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, VenvCard):
                    # Match against venv name OR any linked project folder name
                    match = (text in card.name.lower() or 
                             any(text in p_name.lower() for p_name in card.linked_project_names))
                    card.setVisible(match)

    def update_loc_info(self):
        if self.base_dir:
            self.loc_info.setText(f"Storing in: {self.base_dir}")
            self.loc_info.setStyleSheet("color: #333;")
        else:
            self.loc_info.setText("⚠️ No storage path configured")
            self.loc_info.setStyleSheet("color: #d32f2f; font-weight: bold;")

    def open_settings(self):
        dlg = SettingsDialog(self.base_dir, self)
        if dlg.exec():
            self.base_dir = dlg.get_path()
            self.settings.setValue("venv_path", self.base_dir)
            self.update_loc_info()
            self.btn_new.setEnabled(bool(self.base_dir))
            if self.base_dir and not os.path.exists(self.base_dir):
                os.makedirs(self.base_dir, exist_ok=True)
            self.refresh()

    def load_links(self):
        if os.path.exists(self.links_file):
            with open(self.links_file, 'r') as f:
                data = json.load(f)
                return {v: [p for p in projs if os.path.exists(p)] for v, projs in data.items()}
        return {}

    def save_links(self):
        with open(self.links_file, 'w') as f: json.dump(self.project_links, f)

    def open_terminal(self, venv_path, project_path):
        activate = os.path.join(venv_path, "bin", "activate")
        cmd = f"bash --rcfile <(cat ~/.bashrc; echo 'source \"{activate}\"')"

        # Try Konsole
        if shutil.which("konsole"):
            subprocess.Popen(['konsole', '--workdir', project_path, '-e', 'bash', '-c', cmd])
        # Try Gnome Terminal
        elif shutil.which("gnome-terminal"):
            subprocess.Popen(['gnome-terminal', '--working-directory', project_path, '--', 'bash', '-c', cmd])
        # Try generic emulator
        else:
            subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "{cmd}"'])

    def link_project(self, venv_path):
        folder = QFileDialog.getExistingDirectory(self, "Link Project")
        if folder:
            if venv_path not in self.project_links: self.project_links[venv_path] = []
            if folder not in self.project_links[venv_path]:
                self.project_links[venv_path].append(folder)
                self.save_links(); self.refresh()

    def unlink_project(self, venv_path, project_path):
        if venv_path in self.project_links and project_path in self.project_links[venv_path]:
            self.project_links[venv_path].remove(project_path)
            self.save_links(); self.refresh()

    def launch_script(self, venv_path, project_path):
        file, _ = QFileDialog.getOpenFileName(self, "Run Script", project_path, "Python Files (*.py)")
        if file:
            py = os.path.join(venv_path, "bin", "python") if os.name != 'nt' else os.path.join(venv_path, "Scripts", "python.exe")
            subprocess.Popen([py, file], cwd=project_path)

    def refresh(self):
        if not self.base_dir:
            self.load_cards([]) # Clear and show empty state
            return
        self.scanner = VenvScanner(self.base_dir)
        self.scanner.finished.connect(self.load_cards)
        self.scanner.start()

    def load_cards(self, venvs):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for v in venvs:
            card = VenvCard(v, self.project_links.get(v['path'], []),
                            self.link_project, self.open_terminal, self.launch_script,
                            self.open_packages, self.unlink_project, self.delete_venv, self.clone_venv)
            self.cards_layout.addWidget(card)
            
            # Add line
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            line.setStyleSheet("color: #eee; margin: 10px 0;")
            self.cards_layout.addWidget(line)
        
        if not venvs:
            empty_msg = QLabel(
                "<h2>Welcome to Venv Manager!</h2>"
                "<p>To get started, please click the <b>Settings</b> button above and select a folder "
                "where you want to store your virtual environments.</p>"
                if not self.base_dir else
                "<h2>No environments found.</h2>"
                "<p>Click <b>Create New Venv</b> to build your first one!</p>"
            )
            empty_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_msg.setStyleSheet("color: #666; margin-top: 50px;")
            self.cards_layout.addWidget(empty_msg)

        self.cards_layout.addStretch()

    def create_venv_dialog(self):
        dlg = NewVenvDialog(self.base_dir, self)
        dlg.exec()

    def clone_venv(self, source_path):
        name, ok = QInputDialog.getText(self, "Clone Environment", "New Clone Name:")
        if ok and name:
            target_path = os.path.join(self.base_dir, name.replace(" ", "_"))
            
            if os.path.exists(target_path):
                QMessageBox.warning(self, "Duplicate Name", f"The environment '{name}' already exists at {target_path}.")
                return
            
            # Setup Console Dialog
            self.op_dialog = QDialog(self)
            self.op_dialog.setWindowTitle(f"Cloning to {name}...")
            self.op_dialog.resize(600, 400)
            lay = QVBoxLayout(self.op_dialog)
            self.op_console = QTextEdit()
            self.op_console.setReadOnly(True)
            self.op_console.setStyleSheet("background: #1e1e1e; color: #00ff00; font-family: monospace;")
            lay.addWidget(self.op_console)
            self.op_dialog.show()

            src_py = os.path.join(source_path, "bin", "python") if os.name != 'nt' else os.path.join(source_path, "Scripts", "python.exe")
            tgt_py = os.path.join(target_path, "bin", "python") if os.name != 'nt' else os.path.join(target_path, "Scripts", "python.exe")

            def stage1_finished(exit_code, exit_status):
                if exit_code != 0:
                    self.op_console.append(f"<b>Error:</b> Base environment creation failed with code {exit_code}")
                    self.op_dialog.setWindowTitle("Cloning Failed")
                    return

                # Intermediate refresh so the new venv appears in the list
                self.refresh()
                
                # Stage 2: Get requirements
                self.op_console.append("--- Environment created. Extracting packages... ---")
                res = subprocess.run([src_py, "-m", "pip", "freeze"], capture_output=True, text=True)
                reqs = res.stdout
                
                # Stage 3: Install requirements
                self.op_console.append("--- Installing packages in clone... ---")
                self.active_proc = QProcess(self)
                self.active_proc.readyReadStandardOutput.connect(lambda: self.op_console.append(self.active_proc.readAllStandardOutput().data().decode().strip()))
                self.active_proc.readyReadStandardError.connect(lambda: self.op_console.append(self.active_proc.readAllStandardError().data().decode().strip()))
                self.active_proc.finished.connect(lambda code, status: [self.op_dialog.setWindowTitle("Cloning Finished"), self.refresh()])
                
                # Using a temp file for pip install -r to avoid stdin issues with QProcess
                tmp_reqs = os.path.join(target_path, "reqs_clone_tmp.txt")
                with open(tmp_reqs, 'w') as f: f.write(reqs)
                
                self.active_proc.start(tgt_py, ["-m", "pip", "install", "-r", tmp_reqs])

            # Stage 1: Create venv
            self.op_console.append(f"Creating base venv at {target_path}...")
            self.active_proc = QProcess(self)
            self.active_proc.readyReadStandardOutput.connect(lambda: self.op_console.append(self.active_proc.readAllStandardOutput().data().decode().strip()))
            self.active_proc.finished.connect(stage1_finished)
            self.active_proc.start(sys.executable, ["-m", "venv", target_path])

    def delete_venv(self, path):
        if QMessageBox.question(self, "Delete", "Delete this venv?") == QMessageBox.StandardButton.Yes:
            shutil.rmtree(path); self.refresh()

    def open_packages(self, path): PackageManagerDialog(path, self).exec()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    w = MainWindow(); w.show(); sys.exit(app.exec())
