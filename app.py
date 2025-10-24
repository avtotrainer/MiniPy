#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniPy — მსუბუქი, ინტერაქტიული Python გარემო დამწყებთათვის.
UI: ზედა რედაქტორი (QPlainTextEdit) + ქვედა REPL (qtconsole/IPython).
ღილაკები: Open, Save, Run, Clear
Shortcut-ები: Ctrl+O, Ctrl+S, Ctrl+R, Ctrl+L

ძირითადი პრინციპები (პროექტის ჭეშმარიტებები):
- PySide6 + qtconsole/IPython (ipykernel ≥ 6, jupyter_client ≥ 7)
- სისტემური Python 3.12–3.13+ (შიდა venv არ ვიყენებთ)
- Run ასრულებს მიმდინარე ფაილს REPL-ში `%run -i`-ით (ინტერაქტიური namespace-ის შენარჩუნება)
- UI განლაგება უცვლელია: ზედა რედაქტორი, ქვედა REPL, ზემოთ ღილაკების ზოლი

პლატფორმა:
- Manjaro/Linux (Wayland/X11): სჯობს `QT_QPA_PLATFORM=wayland` Wayland სესიაზე.
- Windows 10/11: მუშაობს სისტემურ Python-თან (python.org installer ან Store-ის გარეშე უკეთესი)

დამოკიდებულებები:
Linux (Manjaro):
    sudo pacman -S python-pip python-jupyter_client python-ipykernel qt6-base
    pip install --user PySide6 qtconsole
Windows 10/11 (PowerShell):
    py -m pip install --upgrade pip
    py -m pip install PySide6 qtconsole jupyter_client ipykernel

გაშვება:
Linux:
    python app.py
Windows:
    py app.py

შენიშვნები:
- თუ qtconsole/ipykernel არ არის დაყენებული, პროგრამა გამოიტანს ნათელ შეტყობინებას.
- Ctrl+L ასუფთავებს მხოლოდ REPL-ს (არ შეეხება რედაქტორს).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# QtCore/QtWidgets
from PySide6.QtCore import Qt
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

# qtconsole/Jupyter კომპონენტები (დაინსტალირებული უნდა იყოს იმავე env-ში)
try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
    from qtconsole.manager import QtKernelManager
except Exception as _e:  # გვინდა მკაფიო შეცდომა GUI-ს გაშვებამდე
    sys.stderr.write(
        "[MiniPy] qtconsole პაკეტი ვერ ჩაიტვირთა. დააყენეთ:\n"
        "  pip install PySide6 qtconsole jupyter_client ipykernel\n"
        f"დეტალი: {type(_e).__name__}: {_e}\n"
    )
    raise


class MiniPy(QMainWindow):
    """
    MiniPy მთავარი ფანჯარა: რედაქტორი + REPL + ღილაკების ზოლი + shortcut-ები.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MiniPy")
        self.resize(1000, 700)

        # სტატუსბარი — აქ ვაჩვენებთ მოკლე შეტყობინებებს (არჩევითი, მაგრამ სასარგებლო)
        self.setStatusBar(QStatusBar(self))

        # --- რედაქტორი ---
        self.editor = self._build_editor()

        # --- REPL (IPython via qtconsole) ---
        self.repl = self._start_repl()

        # --- ღილაკები ---
        bar = self._build_toolbar()

        # --- განლაგება ---
        root = QVBoxLayout()
        root.addLayout(bar)
        root.addWidget(self.editor, 2)
        root.addWidget(self.repl, 1)

        container = QWidget(self)
        container.setLayout(root)
        self.setCentralWidget(container)

        # მიმდინარე ფაილის ბილიკი (None სანამ არაფერი გაგვიღია/შევსუფთავეთ)
        self.current_path: Optional[Path] = None

        # --- გლობალური Shortcut-ები ---
        self._add_shortcuts()

    # --------------------------------------------------------------------- #
    # Helper builders
    # --------------------------------------------------------------------- #
    def _build_editor(self) -> QPlainTextEdit:
        """
        ქმნის და კონფიგურირებს ტექსტურ რედაქტორს.
        - Tabs = 4 space
        - საწყისი placeholder ტექსტი
        """
        ed = QPlainTextEdit(self)
        # Tab ზომა (სიმბოლოების სიგანის მიხედვით)
        ed.setTabStopDistance(4 * ed.fontMetrics().horizontalAdvance(" "))
        ed.setPlaceholderText("# აქ ჩაწერე კოდი...\nprint('Hello, MiniPy!')\n")
        return ed

    def _build_toolbar(self) -> QHBoxLayout:
        """
        ზედა ღილაკების ზოლის შექმნა და სიგნალების მიბმა.
        ღილაკები:
            Open, Save, Run ▶, Clear REPL
        """
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

    # --------------------------------------------------------------------- #
    # REPL setup
    # --------------------------------------------------------------------- #
    def _start_repl(self) -> RichJupyterWidget:
        """
        სტარტავს IPython kernel-ს სისტემურ Python-ზე და აბამს qtconsole widget-ს.
        იყენებს მიმდინარე Python ინტერპრეტატორს (3.12/3.13+).
        """
        # KernelManager — kernel_name="python3" გამოიყენებს აქტიურ ინტერპრეტატორს
        km = QtKernelManager(kernel_name="python3")

        # Linux ტერმინალის ფერების პროფილი საკმარისია (პლატფორმა-აგნოსტური)
        km.start_kernel(extra_arguments=["--colors=Linux"])  # type: ignore[arg-type]

        kc = km.client()
        kc.start_channels()

        w = RichJupyterWidget(self)
        w.kernel_manager = km
        w.kernel_client = kc

        # საწყისი ბანერი (ვაჩვენოთ Python ვერსია)
        w.banner = f"MiniPy — Python {sys.version.split()[0]} | Type ? for help"

        # გაშვებისას გავასუფთავოთ ეკრანი
        w.clear()
        return w

    # --------------------------------------------------------------------- #
    # File operations
    # --------------------------------------------------------------------- #
    def open_file(self) -> None:
        """
        გახსნა: აბაზღაურებს რედაქტორში არჩეული .py ფაილის შიგთავსს.
        """
        start_dir = str(self.current_path.parent if self.current_path else Path.cwd())
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open", start_dir, "Python (*.py)"
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Open error", f"{type(e).__name__}: {e}")
            return

        self.current_path = path
        self.editor.setPlainText(text)
        self.statusBar().showMessage(f"Opened: {self.current_path}", 3000)

    def save_file(self) -> None:
        """
        შენახვა: ინახავს რედაქტორის ტექსტს self.current_path-ში.
        თუ გზა ჯერ არ გვაქვს, გვკითხავს სად შევინახოთ.
        """
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
            self.current_path.write_text(self.editor.toPlainText(), encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Save error", f"{type(e).__name__}: {e}")
            return

        self.statusBar().showMessage(f"Saved: {self.current_path}", 3000)

    # --------------------------------------------------------------------- #
    # Run/Clear actions
    # --------------------------------------------------------------------- #
    def run_current(self) -> None:
        """
        ასრულებს მიმდინარე ფაილს REPL-ში `%run -i`-ით (ინტერაქტიური namespace-ის შენარჩუნება).
        """
        # ფაილის მიღწევადობისა და ცვლილებების დაცვა
        if not self.current_path:
            self.save_file()
            if not self.current_path:
                return

        # ფაილის ბოლო რედაქტირება შევინახოთ
        self.save_file()

        # Windows პათების ეսկეიპი — qtconsole-ში სწორი სტრინგის გადასაცემად
        safe_path = str(self.current_path).replace("\\", "\\\\").replace('"', r"\"")

        # `%run -i` ინარჩუნებს namespace-ს (როგორც პროექტშია მოთხოვნილი)
        code = f'%run -i "{safe_path}"'
        self.repl.execute(code)
        self.statusBar().showMessage("Ran current script via %run -i", 3000)

    def _clear_repl(self) -> None:
        """გაასუფთავებს REPL კონსოლს."""
        self.repl.clear()
        self.statusBar().showMessage("REPL cleared", 2000)

    # --------------------------------------------------------------------- #
    # Keyboard shortcuts
    # --------------------------------------------------------------------- #
    def _add_shortcuts(self) -> None:
        """
        ამატებს გლობალურ Shortcut-ებს:
            Ctrl+O → open_file()
            Ctrl+S → save_file()
            Ctrl+R → run_current()
            Ctrl+L → clear REPL
        """
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
            # QAction-ების დამატება QMainWindow-ზე → იმუშავებს აქტიური focus-ის მიუხედავად
            self.addAction(act)

    # --------------------------------------------------------------------- #
    # Lifecycle
    # --------------------------------------------------------------------- #
    def closeEvent(self, event) -> None:  # type: ignore[override]
        """
        ფანჯრის დახურვისას kernel-ის კორექტული დახურვა.
        """
        try:
            if hasattr(self.repl, "kernel_client") and self.repl.kernel_client:
                self.repl.kernel_client.stop_channels()
            if hasattr(self.repl, "kernel_manager") and self.repl.kernel_manager:
                self.repl.kernel_manager.shutdown_kernel(now=True)
        except Exception:
            # ჩუმად გავატაროთ, რომ დახურვა არ გადაიშალოს მცირე შეცდომით
            pass
        super().closeEvent(event)


# ------------------------------------------------------------------------- #
# Entry point
# ------------------------------------------------------------------------- #
def main() -> int:
    """
    აპის Entry-point.
    - Wayland-ზე ვურჩევთ Qt-ს Wayland backend-ს.
    - ვქმნით QApplication-ს და ვუშვებთ მთავარი ფანჯარას.
    """
    # Wayland პრიორიტეტი Linux-ზე (თუ უკვე მითითებული არაა)
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        os.environ.setdefault("QT_QPA_PLATFORM", "wayland")

    app = QApplication(sys.argv)
    win = MiniPy()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
