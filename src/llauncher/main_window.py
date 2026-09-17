"""Llauncher main window: llama-server configurator.

Left: auto-generated option forms (one tab per category, every flag).
Right: profile bar, models directory + model picker, live bash preview,
embedded server console (QProcess) with Run/Stop, stdin input.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QDialog,
)

from llauncher.command import build_argv, parse_command, to_bash, to_script
from llauncher.config import Settings
from llauncher.presets import DEFAULT_BINARY
from llauncher.server_options import CATEGORIES, OPTIONS, OptionSpec, uncovered_flags
from llauncher.server_profile import (
    ServerProfile,
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
    scan_models,
)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._fields: dict[str, tuple[OptionSpec, QWidget]] = {}
        self._loading = False
        self.proc: QProcess | None = None

        self.setWindowTitle("Llauncher — unsloth configurator")
        self.resize(1280, 800)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addLayout(self._build_profile_bar())
        root.addLayout(self._build_paths_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._build_options_tabs())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        self.setStatusBar(QStatusBar(self))
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #1e1e2e; color: #e8eaed; font-size: 13px; }
            QLineEdit, QComboBox, QPlainTextEdit { background: #313244; border: 1px solid #585b70;
                border-radius: 6px; padding: 6px; }
            QPushButton { background: #45475a; border: none; border-radius: 6px; padding: 7px 12px; }
            QPushButton:hover { background: #585b70; }
            QPushButton:disabled { background: #313244; color: #777; }
            QPushButton#runBtn { background: #2e7d46; font-weight: bold; }
            QPushButton#runBtn:hover { background: #37965a; }
            QPushButton#stopBtn { background: #8d2f33; font-weight: bold; }
            QTabWidget::pane { border: 1px solid #45475a; border-radius: 6px; }
            QTabBar::tab { background: #313244; padding: 6px 10px; border-top-left-radius: 6px;
                border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #45475a; }
            QLabel#mono, QPlainTextEdit#mono { font-family: monospace; }
            """
        )

        self._refresh_profile_list(select=settings.last_profile or "default")
        self.rescan_models()
        self.refresh_bash()

    # ---------------- top bars ----------------
    def _build_profile_bar(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox(self)
        self.profile_combo.currentTextChanged.connect(self._on_profile_selected)
        lay.addWidget(self.profile_combo, 1)
        for text, slot in (("New", self.new_profile), ("Save", self.save_current),
                           ("Delete", self.delete_current), ("Import", self.import_command)):
            btn = QPushButton(text, self)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        self.help_btn = QPushButton("Check --help coverage", self)
        self.help_btn.setToolTip("Run <binary> --help and report flags missing from the form")
        self.help_btn.clicked.connect(self.check_help_coverage)
        lay.addWidget(self.help_btn)
        return lay

    def _build_paths_bar(self) -> QVBoxLayout:
        outer = QVBoxLayout()
        # row 1: server binary
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Server binary:"))
        self.binary_edit = QLineEdit(self.settings.server_binary or DEFAULT_BINARY, self)
        self.binary_edit.setPlaceholderText("unsloth run (or llama serve / full path)")
        self.binary_edit.setToolTip("Tip: you can paste a full path directly here (Ctrl+V)")
        self.binary_edit.textChanged.connect(self.refresh_bash)
        row1.addWidget(self.binary_edit, 1)
        browse_bin = QPushButton("Browse…", self)
        browse_bin.clicked.connect(self.browse_binary)
        row1.addWidget(browse_bin)
        outer.addLayout(row1)
        # row 2: models dir + model picker
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Models dir:"))
        self.models_dir_edit = QLineEdit(self.settings.models_dir, self)
        self.models_dir_edit.setPlaceholderText("~/models — user-defined .gguf library")
        self.models_dir_edit.setToolTip(
            "Tip: you can paste a folder path directly here (Ctrl+V).\n"
            "In Browse… (native system dialog): press Ctrl+L to type/paste a location."
        )
        self.models_dir_edit.textChanged.connect(self._on_models_dir_changed)
        row2.addWidget(self.models_dir_edit, 1)
        browse_dir = QPushButton("Browse…", self)
        browse_dir.clicked.connect(self.browse_models_dir)
        row2.addWidget(browse_dir)
        row2.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox(self)
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(260)
        self.model_combo.currentTextChanged.connect(self.refresh_bash)
        row2.addWidget(self.model_combo, 1)
        rescan = QPushButton("Rescan", self)
        rescan.clicked.connect(self.rescan_models)
        row2.addWidget(rescan)
        outer.addLayout(row2)
        return outer

    # ---------------- left: option tabs ----------------
    def _build_options_tabs(self) -> QTabWidget:
        tabs = QTabWidget(self)
        by_cat: dict[str, list[OptionSpec]] = {c: [] for c in CATEGORIES}
        for spec in OPTIONS:
            if spec.flag == "--model":  # handled by the model picker row
                continue
            by_cat.setdefault(spec.category, []).append(spec)
        for cat in CATEGORIES:
            specs = by_cat.get(cat, [])
            if not specs:
                continue
            page = QScrollArea(self)
            page.setWidgetResizable(True)
            inner = QWidget(page)
            form = QFormLayout(inner)
            for spec in specs:
                w = self._make_field(spec)
                self._fields[spec.flag] = (spec, w)
                title = spec.flag + (f"  ({spec.short})" if spec.short else "")
                label = QLabel(title, self)
                label.setToolTip(self._tooltip(spec))
                form.addRow(label, w)
            page.setWidget(inner)
            tabs.addTab(page, f"{cat} ({len(specs)})")
        return tabs

    def _tooltip(self, spec: OptionSpec) -> str:
        parts = [spec.help] if spec.help else []
        if spec.default:
            parts.append(f"Default: {spec.default}")
        if spec.neg:
            parts.append(f"Off flag: {spec.neg}")
        if spec.env:
            parts.append(f"Env: {spec.env}")
        return "\n".join(parts)

    def _make_field(self, spec: OptionSpec) -> QWidget:
        if spec.kind == "bool":
            box = QCheckBox(f"Default: {'on' if spec.default_on else 'off'}", self)
            box.setChecked(spec.default_on)
            box.setToolTip(self._tooltip(spec))
            box.toggled.connect(self.refresh_bash)
            return box
        if spec.kind == "choice":
            combo = QComboBox(self)
            default_txt = f"(default{': ' + spec.default if spec.default else ''})"
            combo.addItem(default_txt, "")
            for choice in spec.choices:
                combo.addItem(choice, choice)
            combo.setEditable(True)
            combo.setToolTip(self._tooltip(spec) + "\nYou can also type a custom value.")
            combo.currentTextChanged.connect(self.refresh_bash)
            return combo
        edit = QLineEdit(self)
        edit.setPlaceholderText(f"default: {spec.default}" if spec.default else "unset (server default)")
        edit.setClearButtonEnabled(True)
        edit.setToolTip(self._tooltip(spec))
        edit.textChanged.connect(self.refresh_bash)
        return edit

    # ---------------- right panel ----------------
    def _build_right_panel(self) -> QWidget:
        panel = QWidget(self)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(QLabel("Extra raw args (appended verbatim):"))
        self.extra_edit = QLineEdit(self)
        self.extra_edit.setPlaceholderText("--verbose --jinja ...")
        self.extra_edit.textChanged.connect(self.refresh_bash)
        lay.addWidget(self.extra_edit)

        lay.addWidget(QLabel("Generated bash:"))
        self.bash_view = QPlainTextEdit(self)
        self.bash_view.setReadOnly(True)
        self.bash_view.setObjectName("mono")
        self.bash_view.setFont(QFont("monospace", 10))
        self.bash_view.setMaximumBlockCount(200)
        lay.addWidget(self.bash_view, 1)

        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy bash", self)
        self.copy_btn.clicked.connect(self.copy_bash)
        self.export_btn = QPushButton("Export .sh…", self)
        self.export_btn.clicked.connect(self.export_script)
        self.run_btn = QPushButton("▶ Run", self)
        self.run_btn.setObjectName("runBtn")
        self.run_btn.clicked.connect(self.run_server)
        self.run_btn.setToolTip("Run the generated command (Ctrl+Enter)")
        self.run_btn.setShortcut("Ctrl+Return")
        self.stop_btn = QPushButton("■ Stop", self)
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        for b in (self.copy_btn, self.export_btn, self.run_btn, self.stop_btn):
            btn_row.addWidget(b)
        lay.addLayout(btn_row)

        lay.addWidget(QLabel("Embedded server console:"))
        self.console = QPlainTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setObjectName("mono")
        self.console.setFont(QFont("monospace", 10))
        self.console.setMaximumBlockCount(500)
        lay.addWidget(self.console, 2)

        stdin_row = QHBoxLayout()
        self.stdin_edit = QLineEdit(self)
        self.stdin_edit.setPlaceholderText("Type here to send stdin to the server… (Enter to send)")
        self.stdin_edit.returnPressed.connect(self.send_stdin)
        send_btn = QPushButton("Send", self)
        send_btn.clicked.connect(self.send_stdin)
        clear_btn = QPushButton("Clear", self)
        clear_btn.clicked.connect(lambda: self.console.clear())
        stdin_row.addWidget(self.stdin_edit, 1)
        stdin_row.addWidget(send_btn)
        stdin_row.addWidget(clear_btn)
        lay.addLayout(stdin_row)
        return panel

    # ---------------- state <-> UI ----------------
    def current_profile(self) -> ServerProfile:
        name = self.profile_combo.currentText().strip() or "default"
        return ServerProfile(
            name=name,
            server_binary=self.binary_edit.text().strip() or DEFAULT_BINARY,
            model=self._selected_model(),
            models_dir=self.models_dir_edit.text().strip(),
            options=self.collect_options(),
            extra_args=self.extra_edit.text().strip(),
        )

    def _selected_model(self) -> str:
        text = self.model_combo.currentText().strip()
        if not text:
            return ""
        p = Path(text).expanduser()
        if p.is_absolute() and p.exists():
            return str(p)
        base = Path(self.models_dir_edit.text().strip()).expanduser()
        cand = base / text
        if base.is_dir() and cand.exists():
            return str(cand)
        return text  # may be --hf-repo style or not-yet-existing path

    def collect_options(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for flag, (spec, w) in self._fields.items():
            if isinstance(w, QCheckBox):
                if w.isChecked() != spec.default_on:
                    out[flag] = "true" if w.isChecked() else "false"
            elif isinstance(w, QComboBox):
                # Editable: typed text does NOT move currentIndex, so the
                # selected item's data may be stale. Trust it only when the
                # visible text still matches the selected item.
                text = w.currentText().strip()
                placeholder = w.itemText(0).strip() if w.count() else ""
                idx = w.currentIndex()
                if idx > 0 and w.itemText(idx).strip() == text:
                    out[flag] = str(w.itemData(idx))
                elif text and text != placeholder:
                    out[flag] = text  # custom typed value
            elif isinstance(w, QLineEdit) and w.text().strip():
                out[flag] = w.text().strip()
        return out

    def apply_profile(self, profile: ServerProfile) -> None:
        self._loading = True
        try:
            self.binary_edit.setText(profile.server_binary)
            self.models_dir_edit.setText(profile.models_dir)
            self.extra_edit.setText(profile.extra_args)
            for flag, (spec, w) in self._fields.items():
                val = profile.options.get(flag, "")
                if isinstance(w, QCheckBox):
                    if val == "":
                        w.setChecked(spec.default_on)
                    else:
                        w.setChecked(str(val).lower() in ("1", "true", "yes", "on"))
                elif isinstance(w, QComboBox):
                    idx = w.findData(val) if val else 0
                    w.setCurrentIndex(max(idx, 0))
                    if val and idx < 0:  # value not in list (e.g. from --help import)
                        w.addItem(val, val)
                        w.setCurrentIndex(w.count() - 1)
                elif isinstance(w, QLineEdit):
                    w.setText(val)
            self.rescan_models()
            # restore model selection
            if profile.model:
                base = Path(profile.models_dir).expanduser() if profile.models_dir else None
                shown = profile.model
                try:
                    if base and base.is_dir():
                        shown = str(Path(profile.model).relative_to(base))
                except ValueError:
                    pass
                self.model_combo.setCurrentText(shown)
        finally:
            self._loading = False
        self.refresh_bash()

    def refresh_bash(self) -> None:
        if self._loading:
            return
        bash = to_bash(self.current_profile())
        self.bash_view.setPlainText(bash or "# (set a model or options to build a command)")

    # ---------------- profiles ----------------
    def _refresh_profile_list(self, select: str = "default") -> None:
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        names = list_profiles()
        if not names:
            names = ["default"]
        self.profile_combo.addItems(names)
        idx = self.profile_combo.findText(select)
        self.profile_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.profile_combo.blockSignals(False)
        # load the selected one into the form
        try:
            self.apply_profile(load_profile(self.profile_combo.currentText()))
        except (OSError, ValueError):
            pass

    def _on_profile_selected(self, name: str) -> None:
        if not name or self._loading:
            return
        try:
            self.apply_profile(load_profile(name))
            self.settings.last_profile = name
            from llauncher.config import save_settings
            save_settings(self.settings)
        except (OSError, ValueError) as exc:
            self.statusBar().showMessage(f"Could not load profile '{name}': {exc}", 5000)

    def new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New profile", "Profile name:")
        if not ok or not name.strip():
            return
        prof = self.current_profile()
        prof.name = name.strip()
        save_profile(prof)
        self._refresh_profile_list(select=prof.name)

    def save_current(self) -> None:
        prof = self.current_profile()
        # persist models_dir for next launch
        self.settings.models_dir = prof.models_dir
        self.settings.server_binary = prof.server_binary
        self.settings.last_profile = prof.name
        from llauncher.config import save_settings
        save_settings(self.settings)
        save_profile(prof)
        self._refresh_profile_list(select=prof.name)
        self.statusBar().showMessage(f"Saved profile '{prof.name}'", 4000)

    def delete_current(self) -> None:
        name = self.profile_combo.currentText()
        if QMessageBox.question(self, "Delete profile", f"Delete profile '{name}'?") != QMessageBox.StandardButton.Yes:
            return
        delete_profile(name)
        self._refresh_profile_list(select="default")

    def import_command(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Import command")
        dialog.resize(600, 300)
        lay = QVBoxLayout(dialog)
        lay.addWidget(QLabel("Paste an unsloth run command to parse flags into a profile:"))
        text_edit = QPlainTextEdit(dialog)
        text_edit.setPlaceholderText("unsloth run --model /path/to/model.gguf --alias MyModel --ctx-size 4096 ...")
        lay.addWidget(text_edit, 1)
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Import", dialog)
        cancel_btn = QPushButton("Cancel", dialog)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        cmd = text_edit.toPlainText().strip()
        if not cmd:
            return
        try:
            profile = parse_command(cmd)
            self.apply_profile(profile)
            self.statusBar().showMessage(f"Imported: {profile.server_binary} model={profile.model or '(none)'} options={len(profile.options)}", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "Import error", f"Could not parse command:\n{exc}")

    # ---------------- models dir ----------------
    def _on_models_dir_changed(self) -> None:
        self.rescan_models()
        self.refresh_bash()

    def _dialog_start_dir(self, text: str) -> str:
        """Start location for file dialogs: current field value if valid, else home."""
        stripped = text.strip()
        if stripped and (stripped.startswith(("/", "~"))):
            cand = Path(stripped).expanduser()
            if cand.is_dir():
                return str(cand)
            if cand.is_absolute() and cand.parent.is_dir():  # pasted file path -> parent
                return str(cand.parent)
        return str(Path.home())

    def _native_dialog(self, *, title: str, start: str, file_mode) -> QFileDialog:
        """A system-native dialog (KDE/GNOME style): editable location bar,
        Ctrl+L / Ctrl+V paste support, standard Places sidebar."""
        dlg = QFileDialog(self, title, start)
        dlg.setFileMode(file_mode)
        dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        # Explicitly request the native dialog so it matches system defaults
        # (location bar, breadcrumbs, Places) instead of Qt's built-in one.
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, False)
        try:
            from PySide6.QtCore import QStandardPaths, QUrl

            sidebar: list[QUrl] = []
            for loc in (
                QStandardPaths.StandardLocation.HomeLocation,
                QStandardPaths.StandardLocation.DocumentsLocation,
                QStandardPaths.StandardLocation.DownloadLocation,
            ):
                d = QStandardPaths.writableLocation(loc)
                if d:
                    sidebar.append(QUrl.fromLocalFile(d))
            if sidebar:
                dlg.setSidebarUrls(sidebar + dlg.sidebarUrls())
        except Exception:
            pass
        return dlg

    def browse_binary(self) -> None:
        dlg = self._native_dialog(
            title="Select unsloth binary",
            start=self._dialog_start_dir(self.binary_edit.text()),
            file_mode=QFileDialog.FileMode.ExistingFile,
        )
        if dlg.exec():
            files = dlg.selectedFiles()
            if files:
                self.binary_edit.setText(files[0])

    def browse_models_dir(self) -> None:
        dlg = self._native_dialog(
            title="Select models directory",
            start=self._dialog_start_dir(self.models_dir_edit.text()),
            file_mode=QFileDialog.FileMode.Directory,
        )
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            files = dlg.selectedFiles()
            if files:
                self.models_dir_edit.setText(files[0])

    def rescan_models(self) -> None:
        current = self.model_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        models = scan_models(self.models_dir_edit.text())
        base = Path(self.models_dir_edit.text().strip()).expanduser()
        for m in models:
            try:
                rel = str(m.relative_to(base)) if base.is_dir() else str(m)
            except ValueError:
                rel = str(m)
            self.model_combo.addItem(f"{rel}", str(m))
        # show relative path but store absolute in UserData; display text fix:
        for i in range(self.model_combo.count()):
            full = self.model_combo.itemData(i)
            try:
                rel = str(Path(full).relative_to(base))
            except (ValueError, TypeError):
                rel = full
            self.model_combo.setItemText(i, rel)
        if current:
            self.model_combo.setCurrentText(current)
        self.model_combo.blockSignals(False)
        n = self.model_combo.count()
        self.statusBar().showMessage(
            f"{n} .gguf model(s) in {self.models_dir_edit.text() or '(no models dir)'}", 4000
        )

    # ---------------- bash actions ----------------
    def copy_bash(self) -> None:
        QApplication.clipboard().setText(self.bash_view.toPlainText())
        self.statusBar().showMessage("Bash command copied", 3000)

    def export_script(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export run script", f"{self.current_profile().name}.sh", "Shell scripts (*.sh)"
        )
        if not path:
            return
        Path(path).write_text(to_script(self.current_profile()), encoding="utf-8")
        try:
            import os
            os.chmod(path, 0o755)
        except OSError:
            pass
        self.statusBar().showMessage(f"Exported {path}", 4000)

    def check_help_coverage(self) -> None:
        binary = self.binary_edit.text().strip() or DEFAULT_BINARY
        try:
            out = subprocess.run([*shlex.split(binary), "--help"], capture_output=True, text=True, timeout=15, check=False)
            text = (out.stdout or "") + (out.stderr or "")
        except (OSError, subprocess.SubprocessError) as exc:
            QMessageBox.warning(self, "Coverage check", f"Could not run '{binary} --help':\n{exc}")
            return
        missing = uncovered_flags(text)
        total = len(__import__("llauncher.server_options", fromlist=["parse_help_flags"]).parse_help_flags(text))
        if missing:
            QMessageBox.information(
                self, "Coverage check",
                f"{binary} reports ~{total} flags, {len(missing)} not in the form.\n\n"
                + ", ".join(missing[:40])
                + ("\n…(put them in Extra raw args)" if len(missing) > 40 else "\n(Put them in Extra raw args.)"),
            )
        else:
            QMessageBox.information(self, "Coverage check", f"All ~{total} flags from --help are covered.")

    # ---------------- embedded run ----------------
    def run_server(self) -> None:
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.statusBar().showMessage("Server already running — Stop it first", 4000)
            return
        argv = build_argv(self.current_profile())
        if len(argv) < 3 and not self.current_profile().extra_args.strip():
            QMessageBox.warning(self, "Nothing to run", "Select a model (or set --hf-repo) first.")
            return
        self.console.appendPlainText(f"$ {to_bash(self.current_profile())}\n")
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        # Run with the plain system environment so the launched process
        # behaves exactly like pasting the generated command in a terminal.
        self.proc.setEnvironment(QProcess.systemEnvironment())
        self.proc.readyReadStandardOutput.connect(self._on_proc_output)
        self.proc.finished.connect(self._on_proc_finished)
        self.proc.start(argv[0], argv[1:])
        if not self.proc.waitForStarted(5000):
            self.console.appendPlainText(f"[failed to start: {self.proc.errorString()}]")
            self.proc = None
            return
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar().showMessage(f"Running pid {self.proc.processId()}…", 5000)

    def _on_proc_output(self) -> None:
        if self.proc is None:
            return
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.console.moveCursor(QTextCursor.End)
            self.console.insertPlainText(data)
            self.console.moveCursor(QTextCursor.End)

    def _on_proc_finished(self, code: int, status) -> None:
        self.console.appendPlainText(f"\n[process exited with code {code}]")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage(f"Server exited ({code})", 5000)

    def stop_server(self) -> None:
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.terminate()
            if not self.proc.waitForFinished(3000):
                self.proc.kill()

    def send_stdin(self) -> None:
        text = self.stdin_edit.text()
        if not text:
            return
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.write((text + "\n").encode())
            self.console.appendPlainText(f"> {text}")
            self.stdin_edit.clear()
        else:
            self.statusBar().showMessage("Server is not running", 3000)

    def closeEvent(self, event) -> None:
        self.stop_server()
        super().closeEvent(event)
