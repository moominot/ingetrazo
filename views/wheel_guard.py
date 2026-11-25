# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Drop-downs, number boxes, sliders and dials answer the wheel only when
they have the focus, in every window of the application.

A panel of properties is nearly all fields: a wheel notch meant to scroll
it landed on whichever one was under the pointer, changed its value, and
the scrolling stopped there (#1163 on the composer, #1483 everywhere). One
filter on the application covers the panels there are, the ones to come
and the ones extensions add.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox,
                               QDial, QSlider)

#: Not QAbstractSlider: a QScrollBar is one too, and the wheel is its job.
_FIELDS = (QAbstractSpinBox, QComboBox, QSlider, QDial)


class _WheelGuard(QObject):
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        kind = event.type()
        if kind == QEvent.Polish:
            # With WheelFocus, Qt gives the field the focus before anyone
            # sees the wheel event, and it would pass for a picked one.
            # StrongFocus is the Tab key and the click: the click too for
            # a slider whose style leaves it to the Tab key alone, as that
            # is how it gets picked. NoFocus is somebody's choice.
            if isinstance(obj, _FIELDS) and obj.focusPolicy() != Qt.NoFocus:
                obj.setFocusPolicy(Qt.StrongFocus)
        elif (kind == QEvent.Wheel and isinstance(obj, _FIELDS)
                and not obj.hasFocus()):
            # Ignored, not swallowed: Qt hands it on to the parents, up to
            # the scroll area that wanted it.
            event.ignore()
            return True
        return False


_guard = None


def install_wheel_guard() -> None:
    """Install, once, the rule above for every window of the application.
    Before the widgets are built: each one is caught as Qt polishes it."""
    global _guard
    app = QApplication.instance()
    if app is None or _guard is not None:
        return
    _guard = _WheelGuard(app)
    app.installEventFilter(_guard)
