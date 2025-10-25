#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniPy — მსუბუქი, ინტერაქტიული Python გარემო დამწყებთათვის.
UI: ზედა რედაქტორი (QPlainTextEdit) + ქვედა REPL (qtconsole/IPython).
ღილაკები: Open, Save, Run, Clear
Shortcut-ები: Ctrl+O, Ctrl+S, Ctrl+R, Ctrl+L

ძირითადი პრინციპები:
- PySide6 + qtconsole/IPython (ipykernel ≥ 6, jupyter_client ≥ 7)
- სისტემური Python 3.12–3.13+ (შიდა venv არ ვიყენებთ)
- Run ასრულებს მიმდინარე ფაილს REPL-ში `%run -i`-ით (ინტერაქტიური namespace)
- UI უცვლელია: ზედა რედაქტორი, ქვედა REPL, ზემოთ ღილაკების ზოლი

პლატფორმა:
- Manjaro/Linux (Wayland/X11): სჯობს `QT_QPA_PLATFORM=wayland` Wayland სესიაზე.
- Windows 10/11: მუშაობს სისტემურ Python-თან (python.org installer, არა Store)

დამოკიდებულებები:
Linux (Manjaro):
    sudo pacman -S python-pip python-jupyter_client python-ipykernel qt6-base
    pip install --user PySide6 qtconsole
Windows (PowerShell):
    py -m pip install --upgrade pip
    py -m pip install PySide6 qtconsole jupyter_client ipykernel
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSaveFile, QFile, QTextStream, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QMessageBox,
    QStatusBar,
)

# qtconsole / IPython
try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
    from qtconsole.manager import QtKernelManager
except Exception as _e:
    sys.stderr.write(
        "[MiniPy] qtconsole პაკეტი ვერ ჩაიტვირთა. დააყენეთ:\n"
        "  pip install PySide6 qtconsole jupyter_client ipykernel\n"
        f"დეტალი: {type(_e).__name__}: {_e}\n"
    )
    raise


class MiniPy(QMainWindow):
    """MiniPy მთავარი ფანჯარა: რედაქტორი + REPL + ღილაკების ზოლი + shortcut-ები."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MiniPy")
        self.resize(1000, 700)

        # სტატუსბარი
        self.setStatusBar(QStatusBar(self))

        # Widgets
        self.editor = self._build_editor()
        self.repl = self._start_repl()
        bar = self._build_toolbar()

        # განლაგება
        root = QVBoxLayout()
        root.addLayout(bar)
        root.addWidget(self.editor, 2)
        root.addWidget(self.repl, 1)

        container = QWidget(self)
        container.setLayout(root)
        self.setCentralWidget(container)

        # მიმდინარე ფაილი
        self.current_path: Optional[Path] = None

        # Shortcut-ები
        self._add_shortcuts()

    # ------------------------------------------------------------------ #
    # UI helper-ები
    # ------------------------------------------------------------------ #
    def _build_editor(self) -> QPlainTextEdit:
        ed = QPlainTextEdit(self)
        ed.setTabStopDistance(4 * ed.fontMetrics().horizontalAdvance(" "))
        ed.setPlaceholderText("# აქ ჩაწერე კოდი...\nprint('Hello, MiniPy!')\n")
        return ed

    def _build_toolbar(self) -> QHBoxLayout:
        open_btn = QPushButton("Open", self)
        save_btn = QPushButton("Save", self)
        run_btn = QPushButton("Run ▶", self)
        clear_btn = QPushButton("Clear REPL", self)
        exit_btn = QPushButton("Exit", self)

        for b in (open_btn, save_btn, run_btn, clear_btn, exit_btn):
            b.setCursor(Qt.PointingHandCursor)

        open_btn.clicked.connect(self.open_file)
        save_btn.clicked.connect(self.save_file)
        run_btn.clicked.connect(self.run_current)
        clear_btn.clicked.connect(self._clear_repl)
        exit_btn.clicked.connect(QApplication.quit)

        h = QHBoxLayout()
        h.addWidget(open_btn)
        h.addWidget(save_btn)
        h.addWidget(run_btn)
        h.addWidget(clear_btn)
        h.addWidget(exit_btn)
        h.addStretch(1)
        return h

    # ------------------------------------------------------------------ #
    # REPL setup
    # ------------------------------------------------------------------ #
    def _start_repl(self) -> RichJupyterWidget:
        km = QtKernelManager(kernel_name="python3")
        km.start_kernel(extra_arguments=["--colors=Linux", "--quiet"])
        kc = km.client()
        kc.start_channels()

        w = RichJupyterWidget(self)
        w.kernel_manager = km
        w.kernel_client = kc
        w.banner = f"MiniPy — Python {sys.version.split()[0]} | Type ? for help"

        return w

    # ------------------------------------------------------------------ #
    # ფაილის ოპერაციები
    # ------------------------------------------------------------------ #
    def open_file(self) -> None:
        if not self._maybe_save_changes():
            return
        start_dir = str(self.current_path.parent if self.current_path else Path.cwd())
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open", start_dir, "Python (*.py)"
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            data = path.read_bytes()
            if data.startswith(b"\xef\xbb\xbf"):
                text = data[3:].decode("utf-8", errors="replace")
            else:
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = data.decode("latin-1", errors="replace")
        except Exception as e:
            QMessageBox.critical(self, "Open error", f"{type(e).__name__}: {e}")
            return

        self.current_path = path
        self.editor.setPlainText(text)
        self.statusBar().showMessage(f"Opened: {self.current_path}", 3000)

    def save_file(self) -> None:
        if not self.current_path:
            start_dir = str(Path.cwd())
            path_str, _ = QFileDialog.getSaveFileName(
                self, "Save", start_dir, "Python (*.py)"
            )
            if not path_str:
                return
            if not path_str.endswith(".py"):
                path_str += ".py"
            self.current_path = Path(path_str)

        try:
            sf = QSaveFile(str(self.current_path))
            if not sf.open(QFile.WriteOnly | QFile.Truncate | QFile.Text):
                raise OSError("cannot open for writing")
            ts = QTextStream(sf)
            ts.setEncoding("UTF-8")
            ts << self.editor.toPlainText()
            if not sf.commit():
                raise OSError("commit failed")
        except Exception as e:
            QMessageBox.critical(self, "Save error", f"{type(e).__name__}: {e}")
            return

        self.statusBar().showMessage(f"Saved: {self.current_path}", 3000)

    # ------------------------------------------------------------------ #
    # Run / Clear
    # ------------------------------------------------------------------ #
    def run_current(self) -> None:
        # თუ ჯერ არ გვაქვს ფაილი — დროებითი გაშვება
        if not self.current_path:
            fd, tmp_name = tempfile.mkstemp(prefix="minipy_", suffix=".py")
            os.close(fd)
            target_path = Path(tmp_name)
        else:
            target_path = self.current_path

        # ყოველთვის ჩავწეროთ მიმდინარე ტექსტი (auto-save ან temp)
        try:
            sf = QSaveFile(str(target_path))
            if not sf.open(QFile.WriteOnly | QFile.Truncate | QFile.Text):
                raise OSError("cannot open for writing")
            ts = QTextStream(sf)
            ts.setEncoding("UTF-8")
            ts << self.editor.toPlainText()
            if not sf.commit():
                raise OSError("commit failed")
        except Exception as e:
            QMessageBox.critical(self, "Run error", f"{type(e).__name__}: {e}")
            return

        code = f"%run -i {repr(str(target_path))}"
        self.repl.execute(code)
        self.statusBar().showMessage(f"Ran via %run -i: {target_path}", 3000)

    def _clear_repl(self) -> None:
        self.repl.clear()
        self.statusBar().showMessage("REPL cleared", 2000)

    # ------------------------------------------------------------------ #
    # Shortcut-ები
    # ------------------------------------------------------------------ #
    def _add_shortcuts(self) -> None:
        act_open = QAction("Open", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self.open_file)

        act_save = QAction("Save", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self.save_file)

        act_run = QAction("Run", self)
        act_run.setShortcut(QKeySequence("Ctrl+R"))
        act_run.triggered.connect(self.run_current)

        act_clear = QAction("Clear", self)
        act_clear.setShortcut(QKeySequence("Ctrl+L"))
        act_clear.triggered.connect(self._clear_repl)

        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(QApplication.quit)

        for act in (act_open, act_save, act_run, act_clear, act_exit):
            self.addAction(act)

    # ------------------------------------------------------------------ #
    # Lifecycle / უსაფრთხო დახურვა
    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._maybe_save_changes():
            event.ignore()
            return
        try:
            if hasattr(self.repl, "kernel_client") and self.repl.kernel_client:
                self.repl.kernel_client.stop_channels()
            if hasattr(self.repl, "kernel_manager") and self.repl.kernel_manager:
                self.repl.kernel_manager.shutdown_kernel(now=True)
        except Exception:
            pass
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    # Unsaved changes guard
    # ------------------------------------------------------------------ #
    def _maybe_save_changes(self) -> bool:
        doc = self.editor.document()
        if not doc.isModified():
            return True
        ret = QMessageBox.question(
            self,
            "Unsaved changes",
            "შეინახო ცვლილებები?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if ret == QMessageBox.Yes:
            self.save_file()
            return not self.editor.document().isModified()
        return ret == QMessageBox.No


# ---------------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------------- #
def main() -> int:
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        os.environ.setdefault("QT_QPA_PLATFORM", "wayland")

    app = QApplication(sys.argv)
    win = MiniPy()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
