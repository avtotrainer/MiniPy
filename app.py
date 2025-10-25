#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniPy — მსუბუქი, ინტერაქტიული Python გარემო დამწყებთათვის.
UI: ზედა რედაქტორი (QPlainTextEdit) + ქვედა REPL (qtconsole/IPython).
ღილაკები: Open, Save, Run, Clear, Restart, Exit
Shortcut-ები: Ctrl+O, Ctrl+S, Ctrl+R, Ctrl+L, Ctrl+K, Ctrl+Q

პრინციპები:
- PySide6 + qtconsole/IPython (ipykernel ≥ 6, jupyter_client ≥ 7)
- სისტემური Python 3.12–3.13+ (შიდა venv არ ვიყენებთ)
- Run ასრულებს მიმდინარე ფაილს REPL-ში `%run -i`-ით (ინტერაქტიური namespace)
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSaveFile, QFile, QTextStream, QTimer, QSettings, QByteArray, QStringConverter
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager


class MiniPy(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MiniPy[*]")
        self.resize(1000, 700)

        # სტატუსბარი
        self.setStatusBar(QStatusBar(self))

        # კონფიგი (QSettings)
        self.settings = QSettings("MiniPy", "MiniPy")

        # Widgets
        self.editor = self._build_editor()
        self.repl = self._start_repl()

        # Toolbar container
        bar_widget = QWidget(self)
        bar_widget.setLayout(self._build_toolbar())

        # ლეაუთი
        root = QVBoxLayout()
        root.addWidget(bar_widget, 0)
        root.addWidget(self.editor, 1)
        root.addWidget(self.repl, 1)

        container = QWidget(self)
        container.setLayout(root)
        self.setCentralWidget(container)

        # მიმდინარე ფაილი
        self.current_path: Optional[Path] = None
        # ბოლო საქაღალდე
        self.last_dir = Path(self.settings.value("last_dir", str(Path.cwd())))

        # Shortcut-ები
        self._add_shortcuts()

        # ფანჯრის გეომეტრიის აღდგენა
        geo: QByteArray = self.settings.value("win_geometry", QByteArray())
        if geo:
            self.restoreGeometry(geo)

    # ------------------------------ Builders ------------------------------

    def _build_editor(self) -> QPlainTextEdit:
        ed = QPlainTextEdit(self)
        ed.setTabStopDistance(4 * ed.fontMetrics().horizontalAdvance(" "))
        ed.setPlaceholderText("# აქ ჩაწერე კოდი...\nprint('Hello, MiniPy!')\n")
        # სათაურის მოდიფიცირების ინდიკატორი
        ed.document().modificationChanged.connect(self.setWindowModified)
        return ed

    def _build_toolbar(self) -> QHBoxLayout:
        open_btn = QPushButton("Open", self)
        save_btn = QPushButton("Save", self)
        run_btn = QPushButton("Run ▶", self)
        clear_btn = QPushButton("Clear REPL", self)
        restart_btn = QPushButton("Restart Kernel", self)
        exit_btn = QPushButton("Exit", self)

        for b in (open_btn, save_btn, run_btn, clear_btn, restart_btn, exit_btn):
            b.setCursor(Qt.PointingHandCursor)

        open_btn.clicked.connect(self.open_file)
        save_btn.clicked.connect(self.save_file)
        run_btn.clicked.connect(self.run_current)
        clear_btn.clicked.connect(self._clear_repl)
        restart_btn.clicked.connect(self._restart_kernel)
        exit_btn.clicked.connect(QApplication.quit)

        h = QHBoxLayout()
        h.addWidget(open_btn)
        h.addWidget(save_btn)
        h.addWidget(run_btn)
        h.addWidget(clear_btn)
        h.addWidget(restart_btn)
        h.addWidget(exit_btn)
        h.addStretch(1)
        return h

    # ----------------------------- Kernel/REPL ----------------------------

    def _start_repl(self) -> RichJupyterWidget:
        """
        ქერნელის რობუსტ გაშვება:
        1) ვცდილობთ kernelspec 'python3'-ით.
        2) ჩავარდება? ვუშვებთ პირდაპირ sys.executable -m ipykernel.
        """
        w = RichJupyterWidget(self)
        km = QtKernelManager(kernel_name="python3")
        try:
            km.start_kernel(extra_arguments=["--colors=Linux", "--quiet"])
        except Exception:
            # kernelspec ვერ მოიძებნა ან გაშვება ჩავარდა — ჩავრთოთ პირდაპირ ipykernel
            km.kernel_cmd = [
                sys.executable,
                "-m",
                "ipykernel",
                "-f",
                "{connection_file}",
            ]
            try:
                km.start_kernel(extra_arguments=["--colors=Linux", "--quiet"])
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Kernel start failed",
                    f"{type(e).__name__}: {e}\n\n"
                    "დააყენე ipykernel/qtconsole/jupyter_client:\n"
                    "  pip install ipykernel qtconsole jupyter_client",
                )
                raise

        kc = km.client()
        kc.start_channels()

        w.kernel_manager = km
        w.kernel_client = kc
        w.banner = f"MiniPy — Python {sys.version.split()[0]} | Type ? for help"
        self.statusBar().showMessage("Kernel started", 2000)
        return w

    # ------------------------------ Actions -------------------------------

    def _maybe_save_changes(self) -> bool:
        if not self.editor.document().isModified():
            return True
        btn = QMessageBox.question(
            self,
            "შენახვა?",
            "ფაილი შეცვლილია. შევინახო?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if btn == QMessageBox.Cancel:
            return False
        if btn == QMessageBox.Yes:
            self.save_file()
        return True

    def open_file(self) -> None:
        if not self._maybe_save_changes():
            return
        start_dir = str(self.current_path.parent if self.current_path else self.last_dir)
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open", start_dir, "Python (*.py)"
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            data = path.read_bytes()
            text = data.decode("utf-8", errors="replace")
        except Exception as e:
            QMessageBox.critical(self, "Open error", f"{type(e).__name__}: {e}")
            return

        self.current_path = path
        self.last_dir = path.parent
        self.settings.setValue("last_dir", str(self.last_dir))
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.statusBar().showMessage(f"Opened: {self.current_path}", 3000)

    def save_file(self) -> None:
        if not self.current_path:
            start_dir = str(self.last_dir if self.last_dir else Path.cwd())
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
            ts.setEncoding(QStringConverter.Encoding.Utf8)
            ts << self.editor.toPlainText()
            if not sf.commit():
                raise OSError("commit failed")
        except Exception as e:
            QMessageBox.critical(self, "Save error", f"{type(e).__name__}: {e}")
            return

        self.last_dir = self.current_path.parent
        self.settings.setValue("last_dir", str(self.last_dir))
        self.editor.document().setModified(False)
        self.statusBar().showMessage(f"Saved: {self.current_path}", 3000)

    def run_current(self) -> None:
        # თუ ჯერ არ გვაქვს ფაილი — დროებითი გაშვება
        used_temp = False
        if not self.current_path:
            fd, tmp_name = tempfile.mkstemp(prefix="minipy_", suffix=".py")
            os.close(fd)
            target_path = Path(tmp_name)
            used_temp = True
        else:
            target_path = self.current_path

        # ფაილის სინქრონული ჩაწერა temp-შიც (თუ unsaved)
        if used_temp:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())

        code = f"%run -i {repr(str(target_path))}"
        self.repl.execute(code)
        self.statusBar().showMessage(f"Ran via %run -i: {target_path}", 3000)

        # დროებითი ფაილის გაწმენდა მცირე დაყოვნებით (ქერნელმა რომ მოასწროს წაკითხვა)
        if used_temp:
            QTimer.singleShot(3000, lambda p=target_path: p.exists() and p.unlink())

    def _clear_repl(self) -> None:
        self.repl.clear()
        self.statusBar().showMessage("REPL cleared", 2000)

    def _restart_kernel(self) -> None:
        try:
            if hasattr(self.repl, "kernel_client") and self.repl.kernel_client:
                self.repl.kernel_client.stop_channels()
            if hasattr(self.repl, "kernel_manager") and self.repl.kernel_manager:
                self.repl.kernel_manager.shutdown_kernel(now=True)
        except Exception:
            pass
        self.repl.deleteLater()
        self.repl = self._start_repl()
        # ჩანაცვლება ლეაუთში
        central = self.centralWidget().layout()
        # მესამე ელემენტი (0:toolbar, 1:editor, 2:repl)
        old = central.itemAt(2).widget()
        if old:
            old.setParent(None)
        central.addWidget(self.repl, 1)
        self.statusBar().showMessage("Kernel restarted", 2000)

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

        act_clear = QAction("Clear REPL", self)
        act_clear.setShortcut(QKeySequence("Ctrl+L"))
        act_clear.triggered.connect(self._clear_repl)

        act_restart = QAction("Restart Kernel", self)
        act_restart.setShortcut(QKeySequence("Ctrl+K"))
        act_restart.triggered.connect(self._restart_kernel)

        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(QApplication.quit)

        for act in (act_open, act_save, act_run, act_clear, act_restart, act_exit):
            self.addAction(act)

    # ------------------------------ Events --------------------------------

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
        # გეომეტრია/ბოლო საქაღალდე
        self.settings.setValue("win_geometry", self.saveGeometry())
        if self.current_path:
            self.settings.setValue("last_dir", str(self.current_path.parent))
        super().closeEvent(event)


# --------------------------------- main ----------------------------------

def main() -> int:
    # Wayland consideration (Manjaro Hyprland/GNOME)
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        os.environ.setdefault("QT_QPA_PLATFORM", "wayland")

    app = QApplication(sys.argv)
    win = MiniPy()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
