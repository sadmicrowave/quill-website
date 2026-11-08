"""Draw the real Quill windows, offscreen, as vector PDFs (one per screen) for the website.

Run with the Quill app's Python so the real widgets are drawn:

    ../quill-dictation-app/.venv/bin/python tools/make_pdfs.py

then convert them to SVG (text as outlines, so no font is needed to view them and nothing pixelates at any size):

    python tools/pdf_to_svg.py        # needs PyMuPDF (pip install pymupdf)
"""
import os
import pathlib
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = pathlib.Path(__file__).resolve().parents[2] / "quill-dictation-app"
sys.path.insert(0, str(APP))

from PySide6.QtCore import QMarginsF, QPoint, QSizeF                              # noqa: E402
from PySide6.QtGui import QPageSize, QPainter, QPdfWriter                  # noqa: E402
from PySide6.QtWidgets import QApplication                                 # noqa: E402

from quill.config.settings import Settings                                 # noqa: E402
from quill.learning import LinkStore                                       # noqa: E402
from quill.parser.vocab import Vocabulary                                  # noqa: E402
from quill.stream import WordMatch                                         # noqa: E402
from quill.ui import icons                                                 # noqa: E402
from quill.ui.main_window import MainWindow                                # noqa: E402
from quill.ui.settings_dialog import SettingsDialog                        # noqa: E402
from quill.ui.sorting_window import SortingWindow                          # noqa: E402
from quill.ui.theme import apply_spacing, apply_theme, colors_for          # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "build" / "pdf"
icons.make_icon.__defaults__ = (18, 8, False)          # icons are small pictures inside the vector page: draw them sharp at 8x


def to_pdf(widget, name: str, crop_top: int = 0) -> None:
    """One widget as one vector PDF page the size of the widget (points = pixels at 72 dpi)."""
    OUT.mkdir(parents=True, exist_ok=True)
    w, h = widget.width(), widget.height()
    writer = QPdfWriter(str(OUT / f"{name}.pdf"))
    writer.setResolution(72)
    writer.setPageSize(QPageSize(QSizeF(w, h - crop_top), QPageSize.Unit.Point))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    painter = QPainter(writer)
    painter.translate(0, -crop_top)
    widget.render(painter, QPoint(0, 0))
    painter.end()
    print("wrote", name, w, h - crop_top)


def native(window: MainWindow) -> MainWindow:
    """Hide the in-window icon buttons and menu bar, as on macOS where they sit in the title bar and the screen's menu bar."""
    for what in ("help", "undo", "settings", "mini", "file", "turn"):
        getattr(window, f"set_native_{what}_button")(True)
    return window


def settle(app, window=None) -> None:
    for _ in range(25):
        app.processEvents()


def main() -> None:
    app = QApplication(sys.argv)
    theme = "light"
    apply_theme(app, theme, "violet", "compact")
    colors = colors_for(False, "violet")
    known = ("black", "t-shirt", "large", "good", "appraisal", "thirty", "five", "navy", "blue", "jacket")

    # 1. the main window, mid-dictation
    main_window = native(MainWindow(log_collapsed=True))
    main_window.setup()
    main_window.update_workbooks(["Apparel Inventory.xlsx"], "Apparel Inventory.xlsx")
    main_window.set_listening_indicator(True)
    main_window.set_quiet_countdown(8, 0.8)
    main_window.refresh_icons(colors["text"], colors["on_accent"], colors["accent"])
    main_window.set_stream_classifier(lambda words: [WordMatch(w in known, "Color") for w in words])
    main_window.add_stream_text("black t-shirt large good appraisal thirty five")
    main_window.update_current_row({"Type": "T-Shirt", "Color": "Black", "Size": "L", "Condition": "Good", "Appraisal": 35})
    main_window.set_last_saved("Row 6", {"Type": "Blouse", "Color": "Navy", "Size": "M"})
    main_window.widget.menuBar().hide()                              # (the menu bar is at the top of the screen on a Mac)
    main_window.widget.resize(453, 470)
    main_window.widget.show()
    settle(app)
    to_pdf(main_window.widget, "main")

    # 2. the Term Helper, answering by voice
    vocab = Vocabulary()
    vocab.load({"Era": ["1980s", "1990s"], "Color": ["Black", "Navy Blue"], "Type": ["T-Shirt", "Hoodie"]}, [])
    helper = SortingWindow(vocab, lambda *a: None)
    helper.setup(parent=main_window.widget)
    helper.set_items([(None, "teal"), ("Era", "90s")])
    helper.set_voice_active(True)
    apply_spacing(helper.widget, "compact")
    helper.help_button.setVisible(False)                             # (on a Mac Help and Undo sit in the title bar, so the Start button spans the width)
    helper.undo_button.setVisible(False)
    helper.widget.resize(520, 470)                                   # tall enough that both rows show whole
    helper.show()
    settle(app)
    to_pdf(helper.widget, "term-helper")

    # 3. Settings > Learned Words (a word taught by voice, and a word to skip)
    settings = Settings.defaults()
    links = LinkStore()
    for word, column, name in (("sold", "Sale Date", "Sales.xlsx"), ("paid", "Cost", "Sales.xlsx"), ("spotted", "Observation Date", "Whales.xlsx")):
        links.teach(word, column, "/x/" + name, name)
    settings.links = links
    settings.skip_words = ["kinda", "sorta"]
    dialog = SettingsDialog(settings)
    window = dialog.build()
    dialog.nav.setCurrentRow(dialog._nav_row("Learned Words"))
    window.resize(960, 1010)
    window.show()
    settle(app)
    to_pdf(window, "settings-learned")

    # 4. the mini view
    mini = native(MainWindow(log_collapsed=True))
    mini.setup()
    mini.set_mini(True)
    mini.set_listening_indicator(True)
    mini.set_sorting_count(2)
    mini.refresh_icons(colors["text"], colors["on_accent"], colors["accent"])
    mini.widget.menuBar().hide()
    mini.widget.resize(MainWindow.MINI_WIDTH, 58)                    # the real mini view: only the status row (no heard words, no grid)
    mini.widget.show()
    settle(app)
    to_pdf(mini.widget, "mini")


if __name__ == "__main__":
    main()
