# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""In every panel and window, an extension's too, the wheel over a drop-down,
number box, slider or dial that was not picked scrolls the panel and leaves
the value alone (#1483, #1163)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEventLoop, QPoint, QPointF, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QComboBox, QDateEdit, QDial,
                               QDoubleSpinBox, QFontComboBox, QLabel,
                               QLineEdit, QListWidget, QScrollArea,
                               QScrollBar, QSlider, QSpinBox, QVBoxLayout,
                               QWidget)

_app = QApplication.instance() or QApplication([])


def _settle(ms=40):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


@pytest.fixture(scope="module")
def main_window():
    """The application as it runs: the panels below get no help of their own."""
    from views.main_window import MainWindow
    win = MainWindow()
    yield win
    win._saved_version = win.viewport.scene.version
    win.close()


def _combo(editable=False):
    combo = QComboBox()
    combo.setEditable(editable)
    combo.addItems([f"item {i}" for i in range(8)])
    combo.setCurrentIndex(3)
    return combo


def _ranged(cls):
    field = cls()
    field.setRange(0, 100)
    field.setValue(50)
    return field


def _slider():
    slider = _ranged(QSlider)
    slider.setOrientation(Qt.Horizontal)
    return slider


def _date():
    from PySide6.QtCore import QDate
    edit = QDateEdit()
    edit.setDate(QDate(2026, 6, 15))
    return edit


def _font():
    combo = QFontComboBox()
    combo.setCurrentIndex(0)
    return combo


FIELDS = {
    "combo": _combo,
    "editable combo": lambda: _combo(editable=True),
    "font combo": _font,
    "spin box": lambda: _ranged(QSpinBox),
    "double spin box": lambda: _ranged(QDoubleSpinBox),
    "date": _date,
    "slider": _slider,
    "dial": lambda: _ranged(QDial),
}


def _value(field):
    if isinstance(field, QComboBox):
        return field.currentIndex()
    if isinstance(field, QDateEdit):
        return field.date()
    return field.value()


@pytest.fixture
def panel(main_window):
    """A scrolling panel built the way an extension builds one."""
    windows = []

    def build(field):
        window = QWidget()
        outer = QVBoxLayout(window)
        scroll = QScrollArea()
        outer.addWidget(scroll)
        inner = QWidget()
        column = QVBoxLayout(inner)
        elsewhere = QLineEdit()
        column.addWidget(elsewhere)
        column.addWidget(field)
        for i in range(40):
            column.addWidget(QLabel(f"row {i}"))
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        window.resize(300, 300)
        window.show()
        window.activateWindow()
        _settle(60)
        elsewhere.setFocus()
        _settle()
        windows.append(window)
        bar = scroll.verticalScrollBar()
        assert bar.maximum() > 0
        assert bar.value() == 0
        return bar

    yield build
    for window in windows:
        window.close()


def _notch(widget, delta=-120, point=None):
    """A real wheel notch over the widget, through its window: only those
    make Qt hand out the focus and walk up to the parents, as it does for
    the mouse."""
    window = widget.window()
    point = widget.mapTo(window, point or widget.rect().center())
    QTest.wheelEvent(window.windowHandle(), QPointF(point), QPoint(0, delta))
    _settle()


@pytest.mark.parametrize("kind", FIELDS)
def test_the_wheel_over_a_field_not_picked_scrolls_the_panel(panel, kind):
    field = FIELDS[kind]()
    bar = panel(field)
    before = _value(field)
    _notch(field)
    assert _value(field) == before          # the value stayed ...
    assert not field.hasFocus()             # ... the field took no focus ...
    first = bar.value()
    assert first > 0                        # ... and the panel moved


@pytest.mark.parametrize("kind", FIELDS)
def test_a_picked_field_still_answers_the_wheel(panel, kind):
    field = FIELDS[kind]()
    bar = panel(field)
    field.setFocus()
    _settle()
    assert field.hasFocus()
    before = _value(field)
    _notch(field)
    assert _value(field) != before
    assert bar.value() == 0


def test_a_click_picks_a_slider(panel):
    slider = _slider()
    slider.setFocusPolicy(Qt.TabFocus)      # as some styles (macOS) leave it
    panel(slider)
    QTest.mouseClick(slider, Qt.LeftButton, pos=QPoint(2, 2))
    _settle()
    assert slider.hasFocus()


def test_a_field_that_never_takes_the_focus_keeps_it_that_way(panel):
    combo = _combo()
    combo.setFocusPolicy(Qt.NoFocus)
    bar = panel(combo)
    _notch(combo)
    assert combo.focusPolicy() == Qt.NoFocus
    assert combo.currentIndex() == 3
    assert bar.value() > 0


def test_an_open_drop_down_list_scrolls_with_the_wheel(panel):
    combo = QComboBox()
    combo.addItems([f"item {i}" for i in range(200)])
    bar = panel(combo)
    combo.showPopup()
    _settle(80)
    try:
        view = combo.view()
        list_bar = view.verticalScrollBar()
        assert list_bar.maximum() > 0
        before = list_bar.value()
        _notch(view.viewport())
        assert list_bar.value() > before
        assert bar.value() == 0
    finally:
        combo.hidePopup()


def test_a_list_not_picked_scrolls_with_the_wheel(panel):
    rows = QListWidget()
    rows.addItems([f"item {i}" for i in range(100)])
    rows.setFixedHeight(100)
    panel(rows)
    _notch(rows.viewport())
    assert rows.verticalScrollBar().value() > 0


def test_a_scroll_bar_not_picked_answers_the_wheel(panel):
    scroll_bar = QScrollBar(Qt.Horizontal)
    scroll_bar.setRange(0, 100)
    scroll_bar.setValue(50)
    panel(scroll_bar)
    _notch(scroll_bar)
    assert scroll_bar.value() != 50
