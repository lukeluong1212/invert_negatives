from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from invertneg.core.image_processing import image_to_bytes, make_preview, process_image
from invertneg.core.models import ImageSettings, parse_settings


class DesktopApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Negative Review Lab Desktop")
        self.resize(1600, 920)

        self.image_paths: list[Path] = []
        self.settings: dict[Path, ImageSettings] = {}
        self.previous_settings: dict[Path, ImageSettings | None] = {}
        self.current_index: int = -1
        self.has_pending_changes = False

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)

        sidebar = QVBoxLayout()
        main_layout.addLayout(sidebar, 2)

        controls = QHBoxLayout()
        self.btn_import = QPushButton("Import Images")
        self.btn_import.clicked.connect(self.import_images)
        controls.addWidget(self.btn_import)

        self.btn_prev = QPushButton("Prev")
        self.btn_prev.clicked.connect(self.show_prev)
        self.btn_prev.setEnabled(False)
        controls.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.show_next)
        self.btn_next.setEnabled(False)
        controls.addWidget(self.btn_next)
        sidebar.addLayout(controls)

        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.on_image_selected)
        sidebar.addWidget(self.image_list)

        form = QFormLayout()
        sidebar.addLayout(form)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["auto", "color", "bw"])
        self.mode_combo.currentTextChanged.connect(self.on_controls_edited)
        form.addRow("Mode", self.mode_combo)

        percentile_row, self.percentile, self.percentile_value = self._slider_with_value(0, 500, 50)
        form.addRow("Percentile", percentile_row)

        exposure_row, self.exposure, self.exposure_value = self._slider_with_value(-40, 40, 0)
        form.addRow("Exposure", exposure_row)

        white_balance_row, self.white_balance, self.white_balance_value = self._slider_with_value(-100, 100, 0)
        form.addRow("White Balance", white_balance_row)

        contrast_row, self.contrast, self.contrast_value = self._slider_with_value(-100, 100, 0)
        form.addRow("Contrast", contrast_row)

        saturation_row, self.saturation, self.saturation_value = self._slider_with_value(-100, 100, 0)
        form.addRow("Saturation", saturation_row)

        clarity_row, self.clarity, self.clarity_value = self._slider_with_value(-100, 100, 0)
        form.addRow("Clarity", clarity_row)

        red_tint_row, self.red_tint, self.red_tint_value = self._slider_with_value(-100, 100, 0)
        form.addRow("Red Tint", red_tint_row)

        green_tint_row, self.green_tint, self.green_tint_value = self._slider_with_value(-100, 100, 0)
        form.addRow("Green Tint", green_tint_row)

        blue_tint_row, self.blue_tint, self.blue_tint_value = self._slider_with_value(-100, 100, 0)
        form.addRow("Blue Tint", blue_tint_row)

        self.btn_apply_settings = QPushButton("Apply Settings")
        self.btn_apply_settings.clicked.connect(self.apply_current_settings)
        self.btn_apply_settings.setEnabled(False)
        sidebar.addWidget(self.btn_apply_settings)

        export_row = QHBoxLayout()
        self.btn_export_current = QPushButton("Export Current")
        self.btn_export_current.clicked.connect(self.export_current)
        self.btn_export_current.setEnabled(False)
        export_row.addWidget(self.btn_export_current)

        self.btn_export_all = QPushButton("Export All")
        self.btn_export_all.clicked.connect(self.export_all)
        self.btn_export_all.setEnabled(False)
        export_row.addWidget(self.btn_export_all)
        sidebar.addLayout(export_row)

        action_row = QHBoxLayout()
        self.btn_apply_all = QPushButton("Apply To All")
        self.btn_apply_all.clicked.connect(self.apply_to_all)
        self.btn_apply_all.setEnabled(False)
        action_row.addWidget(self.btn_apply_all)

        self.btn_undo = QPushButton("Undo")
        self.btn_undo.clicked.connect(self.undo_current)
        self.btn_undo.setEnabled(False)
        action_row.addWidget(self.btn_undo)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_current)
        self.btn_reset.setEnabled(False)
        action_row.addWidget(self.btn_reset)
        sidebar.addLayout(action_row)

        self.show_original = QCheckBox("Show Original")
        self.show_original.setChecked(True)
        self.show_original.toggled.connect(lambda _: self.refresh_previews())
        sidebar.addWidget(self.show_original)

        self.status_label = QLabel("Import images to begin.")
        self.status_label.setWordWrap(True)
        sidebar.addWidget(self.status_label)

        viewer = QHBoxLayout()
        main_layout.addLayout(viewer, 5)

        self.original_label = QLabel("Original")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setMinimumSize(420, 720)
        self.original_label.setStyleSheet("border: 1px solid #444; background: #1f1f1f; color: #d8d8d8;")
        viewer.addWidget(self.original_label)

        self.processed_label = QLabel("Positive Preview")
        self.processed_label.setAlignment(Qt.AlignCenter)
        self.processed_label.setMinimumSize(420, 720)
        self.processed_label.setStyleSheet("border: 1px solid #444; background: #1f1f1f; color: #d8d8d8;")
        viewer.addWidget(self.processed_label)

    def _slider_with_value(self, minimum: int, maximum: int, value: int) -> tuple[QWidget, QSlider, QLabel]:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(self.on_controls_edited)
        value_label = QLabel("")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setFixedWidth(56)
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        return container, slider, value_label

    def _set_pending_changes(self, pending: bool, message: str | None = None) -> None:
        self.has_pending_changes = pending
        if message:
            self.status_label.setText(message)
        self.update_button_states()

    def _update_slider_value_labels(self) -> None:
        self.percentile_value.setText(f"{self.percentile.value() / 100:.1f}")
        self.exposure_value.setText(f"{self.exposure.value() / 10:.1f}")
        self.white_balance_value.setText(f"{self.white_balance.value()}")
        self.contrast_value.setText(f"{self.contrast.value()}%")
        self.saturation_value.setText(f"{self.saturation.value()}%")
        self.clarity_value.setText(f"{self.clarity.value()}%")
        self.red_tint_value.setText(f"{self.red_tint.value()}%")
        self.green_tint_value.setText(f"{self.green_tint.value()}%")
        self.blue_tint_value.setText(f"{self.blue_tint.value()}%")

    def update_button_states(self) -> None:
        has_image = self.current_index >= 0 and self.current_index < len(self.image_paths)
        self.btn_prev.setEnabled(has_image and self.current_index > 0)
        self.btn_next.setEnabled(has_image and self.current_index < len(self.image_paths) - 1)
        self.btn_export_current.setEnabled(has_image)
        self.btn_export_all.setEnabled(bool(self.image_paths))
        self.btn_apply_all.setEnabled(has_image)
        self.btn_undo.setEnabled(has_image and self.previous_settings.get(self.image_paths[self.current_index]) is not None)
        self.btn_reset.setEnabled(has_image)
        self.btn_apply_settings.setEnabled(has_image and self.has_pending_changes)

    def import_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select scans",
            str(Path.cwd()),
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)",
        )
        if not files:
            return

        self.image_paths = [Path(path) for path in files]
        self.settings = {path: ImageSettings() for path in self.image_paths}
        self.previous_settings = {path: None for path in self.image_paths}
        self.image_list.clear()

        for path in self.image_paths:
            item = QListWidgetItem(path.name)
            item.setData(Qt.UserRole, str(path))
            self.image_list.addItem(item)

        self.current_index = 0
        self.image_list.setCurrentRow(0)
        self._set_pending_changes(False, "Images loaded. Adjust settings and click Apply Settings.")
        self.update_button_states()

    def on_image_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.image_paths):
            return
        self.current_index = row
        settings = self.settings[self.image_paths[row]]
        self._load_controls(settings)
        self._set_pending_changes(False, f"Loaded {self.image_paths[row].name}")
        self.refresh_previews(settings=settings)

    def _load_controls(self, settings: ImageSettings) -> None:
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(settings.mode)
        self.mode_combo.blockSignals(False)

        self.percentile.blockSignals(True)
        self.percentile.setValue(int(round(settings.percentile * 100)))
        self.percentile.blockSignals(False)

        self.exposure.blockSignals(True)
        self.exposure.setValue(int(round(settings.exposure * 10)))
        self.exposure.blockSignals(False)

        self.white_balance.blockSignals(True)
        self.white_balance.setValue(int(round(settings.white_balance)))
        self.white_balance.blockSignals(False)

        self.contrast.blockSignals(True)
        self.contrast.setValue(int(round(settings.contrast)))
        self.contrast.blockSignals(False)

        self.saturation.blockSignals(True)
        self.saturation.setValue(int(round(settings.saturation)))
        self.saturation.blockSignals(False)

        self.clarity.blockSignals(True)
        self.clarity.setValue(int(round(settings.clarity)))
        self.clarity.blockSignals(False)

        self.red_tint.blockSignals(True)
        self.red_tint.setValue(int(round(settings.red_tint)))
        self.red_tint.blockSignals(False)

        self.green_tint.blockSignals(True)
        self.green_tint.setValue(int(round(settings.green_tint)))
        self.green_tint.blockSignals(False)

        self.blue_tint.blockSignals(True)
        self.blue_tint.setValue(int(round(settings.blue_tint)))
        self.blue_tint.blockSignals(False)

        self._update_slider_value_labels()

    def _draft_settings(self) -> ImageSettings | None:
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return None

        try:
            parsed = parse_settings(
                mode=self.mode_combo.currentText(),
                percentile=self.percentile.value() / 100.0,
                exposure=self.exposure.value() / 10.0,
                white_balance=float(self.white_balance.value()),
                contrast=float(self.contrast.value()),
                saturation=float(self.saturation.value()),
                clarity=float(self.clarity.value()),
                red_tint=float(self.red_tint.value()),
                green_tint=float(self.green_tint.value()),
                blue_tint=float(self.blue_tint.value()),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return None
        return parsed

    def on_controls_edited(self) -> None:
        if self.current_index < 0:
            return
        self._update_slider_value_labels()
        self._set_pending_changes(True, "Changes staged. Click Apply Settings to process.")

    def apply_current_settings(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return

        draft = self._draft_settings()
        if draft is None:
            return

        path = self.image_paths[self.current_index]
        current = self.settings[path]
        if draft != current:
            self.previous_settings[path] = ImageSettings(**asdict(current))
            self.settings[path] = draft

        self._set_pending_changes(False, f"Applied settings for {path.name}")
        self.refresh_previews(settings=draft)

    def apply_to_all(self) -> None:
        if self.current_index < 0:
            return

        current = self._draft_settings()
        if current is None:
            return

        for path in self.image_paths:
            existing = self.settings[path]
            if existing != current:
                self.previous_settings[path] = ImageSettings(**asdict(existing))
                self.settings[path] = ImageSettings(**asdict(current))

            self._set_pending_changes(False, f"Applied settings to {len(self.image_paths)} images")
            self.refresh_previews(settings=self.settings[self.image_paths[self.current_index]])

    def undo_current(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return

        path = self.image_paths[self.current_index]
        previous = self.previous_settings.get(path)
        if previous is None:
            return

        current = self.settings[path]
        self.settings[path] = ImageSettings(**asdict(previous))
        self.previous_settings[path] = ImageSettings(**asdict(current))
        self._load_controls(self.settings[path])
        self._set_pending_changes(True, "Settings reverted to previous state. Click Apply Settings.")
        self.update_button_states()

    def reset_current(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return

        path = self.image_paths[self.current_index]
        current = self.settings[path]
        defaults = ImageSettings()
        if current != defaults:
            self.previous_settings[path] = ImageSettings(**asdict(current))
        self._load_controls(defaults)
        self._set_pending_changes(True, "Reset staged. Click Apply Settings to process.")
        self.update_button_states()

    def _to_qpixmap(self, image: Image.Image) -> QPixmap:
        data = image_to_bytes(image, format_name="PNG")
        qimage = QImage.fromData(data, "PNG")
        return QPixmap.fromImage(qimage)

    def refresh_previews(self, settings: ImageSettings | None = None) -> None:
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return

        path = self.image_paths[self.current_index]
        active_settings = settings or self.settings[path]

        with Image.open(path) as source:
            original_preview = make_preview(source, max_size=(820, 820))
            processed = process_image(source, **asdict(active_settings))
            processed_preview = make_preview(processed, max_size=(820, 820))

        if self.show_original.isChecked():
            self.original_label.setVisible(True)
            self.original_label.setPixmap(
                self._to_qpixmap(original_preview).scaled(
                    self.original_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            self.original_label.setVisible(False)

        self.processed_label.setPixmap(
            self._to_qpixmap(processed_preview).scaled(
                self.processed_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.refresh_previews()

    def show_prev(self) -> None:
        if self.current_index > 0:
            self.image_list.setCurrentRow(self.current_index - 1)

    def show_next(self) -> None:
        if self.current_index < len(self.image_paths) - 1:
            self.image_list.setCurrentRow(self.current_index + 1)

    def export_current(self) -> None:
        if self.current_index < 0:
            return

        settings = self.settings[self.image_paths[self.current_index]]
        if settings is None:
            return

        src = self.image_paths[self.current_index]
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Export current image",
            str(src.with_name(f"{src.stem}_positive.jpg")),
            "JPEG (*.jpg *.jpeg)",
        )
        if not target:
            return

        with Image.open(src) as image:
            process_image(image, **asdict(settings)).save(target, quality=95)

    def export_all(self) -> None:
        if not self.image_paths:
            return

        target_dir = QFileDialog.getExistingDirectory(self, "Select export folder", str(Path.cwd()))
        if not target_dir:
            return

        out = Path(target_dir)
        for path in self.image_paths:
            settings = self.settings[path]
            with Image.open(path) as image:
                result = process_image(image, **asdict(settings))
                result.save(out / f"{path.stem}_positive.jpg", quality=95)

        QMessageBox.information(self, "Export complete", f"Exported {len(self.image_paths)} images to\n{out}")


def run() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(
        """
        QWidget { background: #111318; color: #e7e7e7; }
        QPushButton { background: #262c36; border: 1px solid #3a4252; padding: 6px; }
        QPushButton:hover { background: #31394a; }
        QListWidget { background: #171b23; border: 1px solid #343b49; }
        QComboBox, QSlider { background: #171b23; }
        """
    )
    window = DesktopApp()
    window.show()
    return app.exec()
