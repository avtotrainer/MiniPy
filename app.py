#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniPy — მსუბუქი Python UI დამწყებთათვის.
ღილაკები: Open, Save, Run, Clear, Exit.
Hotkeys: Ctrl+O / Ctrl+S / Ctrl+R / Ctrl+L / Ctrl+Q.
Run იყენებს: %run -i <მიმდინარე ფაილი>
"""

import os, sys, shlex
from typing import Optional

from PySide6.QtCore import Qt, QFile, QTextStream, QStringConverter, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QLabel,
    QStatusBar,
)
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager


class MiniPy(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiniPy")
        self.resize(960, 640)
        self.current_path: Optional[str] = None

        # --- Editor ---
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("# აქ დაწერე Python კოდი…")
        self.editor.document().modificationChanged.connect(self._on_modified)

        # --- Console ---
        self.console = self._make_console()

        # --- Buttons ---
        open_btn = QPushButton("Open")
        save_btn = QPushButton("Save")
        run_btn = QPushButton("Run")
        clear_btn = QPushButton("Clear")
        exit_btn = QPushButton("Exit")

        open_btn.clicked.connect(self.open_file)
        save_btn.clicked.connect(self.save_file)
        run_btn.clicked.connect(self.run_current_file)
        clear_btn.clicked.connect(self.clear_repl)
        exit_btn.clicked.connect(self.close)  # მნიშვნელოვანია: closeEvent გამოიძახოს

        h = QHBoxLayout()
        for b in (open_btn, save_btn, run_btn, clear_btn, exit_btn):
            h.addWidget(b)
        h.addStretch(1)

        top = QWidget()
        top.setLayout(h)

        v = QVBoxLayout()
        v.addWidget(top)
        v.addWidget(QLabel("კოდი:"))
        v.addWidget(self.editor, 3)
        v.addWidget(QLabel("REPL:"))
        v.addWidget(self.console, 2)

        cw = QWidget()
        cw.setLayout(v)
        self.setCentralWidget(cw)

        # --- Status bar ---
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.mod_label = QLabel("")  # „Modified“ ინდიკატორი
        self.status.addPermanentWidget(self.mod_label)

        # Actions / shortcuts
        self._make_actions()
        self._update_title()

        # Demo text
        if not self.editor.toPlainText().strip():
            self.editor.setPlainText(
                "# MiniPy\nprint('გამარჯობა MiniPy-დან!')\nx = 2 + 2\nprint('x =', x)\n"
            )

        # REPL ბანერი
        QTimer.singleShot(
            0, lambda: self._execute_in_repl("print('MiniPy kernel ready')")
        )

    # ------------------------------------------------------------------
    def _make_console(self) -> RichJupyterWidget:
        km = QtInProcessKernelManager()
        km.start_kernel(show_banner=False)
        self.kernel_manager = km
        self.kernel = km.kernel
        self.kernel.gui = "qt"

        kc = km.client()
        kc.start_channels()
        self.kernel_client = kc

        w = RichJupyterWidget()
        w.kernel_manager = km
        w.kernel_client = kc
        w.banner = ""
        return w

    def _execute_in_repl(self, code: str) -> None:
        self.console.execute(code)

    # ------------------------------------------------------------------
    def _on_modified(self, modified: bool) -> None:
        self.mod_label.setText("Modified" if modified else "")
        self._update_title()

    def _update_title(self) -> None:
        name = self.current_path or "untitled.py"
        mod = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"MiniPy — {os.path.basename(name)}{mod}")

    # ------------------------------------------------------------------
    def open_file(self):
        if not self._maybe_save_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "ფაილის გახსნა", "", "Python Files (*.py);;All Files (*)"
        )
        if not path:
            return

        qf = QFile(path)
        if not qf.open(QFile.ReadOnly | QFile.Text):
            QMessageBox.critical(self, "შეცდომა", f"ვერ გაიხსნა:\n{path}")
            return

        s = QTextStream(qf)
        s.setEncoding(QStringConverter.Encoding.Utf8)
        text = s.readAll()
        qf.close()

        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.current_path = path
        self._update_title()
        self.status.showMessage(f"გახსნილია: {path}", 3000)

    def save_file(self) -> bool:
        if not self.current_path:
            return self.save_file_as()
        return self._write_to_path(self.current_path)

    def save_file_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "შენახვა როგორც…",
            self.current_path or "untitled.py",
            "Python Files (*.py);;All Files (*)",
        )
        if not path:
            return False
        ok = self._write_to_path(path)
        if ok:
            self.current_path = path
            self._update_title()
        return ok

    def _write_to_path(self, path: str) -> bool:
        qf = QFile(path)
        if not qf.open(QFile.WriteOnly | QFile.Text):
            QMessageBox.critical(self, "შეცდომა", f"ვერ შეინახა:\n{path}")
            return False
        s = QTextStream(qf)
        s.setEncoding(QStringConverter.Encoding.Utf8)
        s << self.editor.toPlainText()
        qf.close()
        self.editor.document().setModified(False)
        self.mod_label.setText("")
        self.status.showMessage(f"შენახულია: {path}", 3000)
        return True

    # ------------------------------------------------------------------
    def run_current_file(self):
        if not self.current_path:
            if not self.save_file_as():
                QMessageBox.information(
                    self, "ინფორმაცია", "გასაშვებად საჭიროა ფაილის შენახვა."
                )
                return
        if self.editor.document().isModified():
            if not self._maybe_save_changes():
                return
        quoted = shlex.quote(self.current_path)
        self._execute_in_repl(f"%run -i {quoted}")
        self.status.showMessage(f"გაშვებულია: {self.current_path}", 3000)

    def clear_repl(self):
        try:
            self.console.clear()
        except Exception:
            try:
                self.console._control.clear()
            except Exception:
                pass

    # ------------------------------------------------------------------
    def _maybe_save_changes(self) -> bool:
        """თუ დოკუმენტი შეცვლილია — ეკითხება: [შენახვა] [უგულებელყოფა] [გაუქმება]."""
        if not self.editor.document().isModified():
            return True

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("შენახვა საჭიროა")
        msg.setText("ფაილი შეცვლილია და ჯერ არ არის შენახული.")
        msg.setInformativeText("გინდა შევინახო?")
        save_btn = msg.addButton("შენახვა", QMessageBox.AcceptRole)
        discard_btn = msg.addButton(
            "უგულებელყოფა", QMessageBox.DestructiveRole
        )  # ← სწორი enum
        cancel_btn = msg.addButton("გაუქმება", QMessageBox.RejectRole)
        msg.setDefaultButton(save_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is cancel_btn:
            return False
        if clicked is save_btn:
            return bool(self.save_file())
        return True  # Discard

    def closeEvent(self, event):
        if self._maybe_save_changes():
            try:
                self.kernel_client.stop_channels()
                self.kernel_manager.shutdown_kernel(now=True)
            except Exception:
                pass
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    def _make_actions(self):
        actions = [
            ("Open", "Ctrl+O", self.open_file),
            ("Save", "Ctrl+S", self.save_file),
            ("Run", "Ctrl+R", self.run_current_file),
            ("Clear", "Ctrl+L", self.clear_repl),
            ("Exit", "Ctrl+Q", self.close),
        ]
        for text, key, slot in actions:
            act = QAction(text, self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(slot)
            self.addAction(act)


def main() -> int:
    # Qt-ს DPI ატრიბუტი შეიძლება იყოს Deprecated — უსაფრთხოდ ვცადოთ და იგნორირება მოვახდინოთ შეცდომის.
    # try:
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # except Exception:
    # pass

    app = QApplication(sys.argv)
    w = MiniPy()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
