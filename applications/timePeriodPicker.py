"""Interactive time-period selector for Jupyter notebooks.

Notebook usage
--------------
from applications.timePeriodPicker import timePicker

timePicker.show()

After clicking "Apply time period":
    period = timePicker.period
    selected_data = data.loc[period]

Create an independent selector:
    from datetime import datetime
    from time_period_picker import TimePeriodPicker

    selector = TimePeriodPicker(
        start=datetime(2025, 1, 1, 0, 0),
        end=datetime(2025, 12, 31, 23, 0),
    )
    selector
"""

from datetime import datetime
from typing import Optional

import ipywidgets as widgets
from IPython.display import display

__version__ = "2.0.0"


class TimePeriodPicker(widgets.VBox):
    """Jupyter widget for selecting a time period"""

    def __init__(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        title: str = "Select the evaluation period",
    ) -> None:
        self._initial_start = start or datetime(2025, 1, 1, 0, 0)
        self._initial_end = end or datetime(2025, 12, 31, 23, 0)

        if self._initial_start > self._initial_end:
            raise ValueError("The start time must be before the end time.")

        self.period = slice(self._initial_start, self._initial_end)

        self.start_picker = widgets.NaiveDatetimePicker(
            description="Start:",
            value=self._initial_start,
            layout=widgets.Layout(width="380px"),
        )

        self.end_picker = widgets.NaiveDatetimePicker(
            description="Ende:",
            value=self._initial_end,
            layout=widgets.Layout(width="380px"),
        )

        self.apply_button = widgets.Button(
            description="Apply time period",
            icon="check",
            button_style="success",
            tooltip="Save selected time period",
        )

        self.reset_button = widgets.Button(
            description="Reset",
            icon="undo",
            tooltip="Restore the original time period",
        )

        self.status = widgets.HTML()

        self.apply_button.on_click(self._apply_selection)
        self.reset_button.on_click(self._reset_selection)

        controls = widgets.HBox(
            [self.apply_button, self.reset_button],
            layout=widgets.Layout(gap="8px"),
        )

        super().__init__(
            children=[
                widgets.HTML(f"<h4>{title}</h4>"),
                self.start_picker,
                self.end_picker,
                controls,
                self.status,
            ]
        )

        self._show_current_period()

    @property
    def start(self) -> datetime:
        """Currently selected start time."""
        return self.period.start

    @property
    def end(self) -> datetime:
        """Currently accepted end time"""
        return self.period.stop

    def _apply_selection(self, _button=None) -> None:
        start = self.start_picker.value
        end = self.end_picker.value

        if start is None or end is None:
            self.status.value = (
                "<span style='color:#b00020'>"
                "Please select start and end time."
                "</span>"
            )
            return

        if start > end:
            self.status.value = (
                "<span style='color:#b00020'>"
                "The start time must be before the end time."
                "</span>"
            )
            return

        self.period = slice(start, end)
        self._show_current_period()

    def _reset_selection(self, _button=None) -> None:
        self.start_picker.value = self._initial_start
        self.end_picker.value = self._initial_end
        self.period = slice(self._initial_start, self._initial_end)
        self._show_current_period()

    def _show_current_period(self) -> None:
        self.status.value = (
            "<b>Active Period:</b> "
            f"{self.period.start:%d.%m.%Y %H:%M} bis "
            f"{self.period.stop:%d.%m.%Y %H:%M}"
        )

    def show(self):
        """Display the widget explicitly in the current notebook output and return itself."""
        display(self)
        return self

timePicker = TimePeriodPicker()
