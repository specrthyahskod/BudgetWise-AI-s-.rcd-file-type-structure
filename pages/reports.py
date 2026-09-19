"""Financial report page with weekly .rcd export."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.rcd_format import RCDFileManager


class FinancialReportPage(QWidget):
    """Displays financial reports and supports weekly ledger export."""

    def __init__(
        self,
        username: str = "user",
        transactions: list[dict] | None = None,
        currency: str = "AUD",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.username = username
        self.transactions = transactions or []
        self.currency = currency

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.download_week_btn = QPushButton("Download Week")
        self.download_week_btn.clicked.connect(self._download_week)
        layout.addWidget(self.download_week_btn)

    @staticmethod
    def _current_week_range(reference: date | None = None) -> tuple[date, date]:
        today = reference or date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday

    @staticmethod
    def _parse_transaction_date(value: object) -> date | None:
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def _filter_week_transactions(
        self, week_start: date, week_end: date
    ) -> list[dict]:
        filtered: list[dict] = []

        for txn in self.transactions:
            txn_date = self._parse_transaction_date(txn.get("date"))
            if txn_date is None or not (week_start <= txn_date <= week_end):
                continue

            filtered.append(
                {
                    "date": txn_date.isoformat(),
                    "category": str(txn.get("category", "")),
                    "description": str(txn.get("description", "")),
                    "amount": float(txn.get("amount", 0.0)),
                }
            )

        filtered.sort(key=lambda item: item["date"])
        return filtered

    @staticmethod
    def _compute_summary_metrics(
        records: list[dict], currency: str, week_start: date, week_end: date
    ) -> dict:
        total_expenses = round(sum(record["amount"] for record in records), 2)
        record_count = len(records)
        day_span = (week_end - week_start).days + 1
        daily_average = round(total_expenses / day_span, 2) if day_span else 0.0

        return {
            "total_expenses": total_expenses,
            "record_count": record_count,
            "daily_average": daily_average,
            "currency": currency,
        }

    def _download_week(self) -> None:
        week_start, week_end = self._current_week_range()
        week_records = self._filter_week_transactions(week_start, week_end)
        summary = self._compute_summary_metrics(
            week_records, self.currency, week_start, week_end
        )

        default_name = f"BW_Week_{week_end.strftime('%Y%m%d')}.rcd"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Weekly Record",
            default_name,
            "BudgetWise Records (*.rcd)",
        )

        if not filepath:
            return

        rcd_bytes = RCDFileManager.pack_weekly_data(
            username=self.username,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            transactions=week_records,
            summary_metrics=summary,
        )

        saved_path = RCDFileManager.save_file(filepath, rcd_bytes)

        QMessageBox.information(
            self,
            "Export Complete",
            f"Weekly financial record exported successfully to:\n{saved_path}",
        )
