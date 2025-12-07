# expenses/services/importers.py
import csv
import io
import re
from datetime import datetime
from decimal import Decimal

import pdfplumber

from ..models import Expense, ExpenseCategory


def _normalize_amount(raw: str) -> Decimal:
    cleaned = (
        raw.replace("\xa0", "")
        .replace(" ", "")
        .replace("+", "")
        .replace("−", "-")
        .replace(",", ".")
    )
    return Decimal(cleaned)


# ---------- T-Bank CSV ----------

def import_tbank_csv(file_obj, user):
    """
    Import expenses from T-Bank (Tinkoff) CSV export.
    Only rows with negative 'Сумма операции' are treated as expenses.
    Returns (created_count, total_amount).
    """
    content = file_obj.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content), delimiter=";")

    created = 0
    total = Decimal("0")

    for row in reader:
        status = row.get("Статус")
        if status != "OK":
            continue

        amount_raw = row.get("Сумма операции") or row.get("Сумма платежа") or ""
        if not amount_raw:
            continue

        amount = _normalize_amount(amount_raw)
        if amount >= 0:
            # пополнения / возвраты не считаем расходами
            continue
        amount = -amount  # храним как положительную сумму расхода

        currency = (row.get("Валюта операции") or "RUB").strip()
        date_str = (row.get("Дата операции") or "").split()[0]
        try:
            date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            continue

        category_name = (row.get("Категория") or "Uncategorized").strip()
        description = (row.get("Описание") or "").strip()

        category, _ = ExpenseCategory.objects.get_or_create(
            user=user,
            name=category_name,
        )

        Expense.objects.create(
            user=user,
            category=category,
            date=date,
            description=description[:255] or category_name,
            amount=amount,
            bank="T-Bank",
            currency=currency,
        )
        created += 1
        total += amount

    return created, total


# ---------- Sber PDF ----------

DATE_LINE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\s+\d{6}\s+")


def import_sber_pdf(file_obj, user):
    """
    Import expenses from Sber PDF statement.
    Very simple heuristic parser tailored to the sample format.
    Returns (created_count, total_amount).
    """
    lines: list[str] = []

    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if line:
                    lines.append(line)

    entries: list[dict] = []
    current = None

    for line in lines:
        # operations block is formatted like:
        # 05.12.2025 20:08 809711 Коммунальные платежи, связь, интернет. 580,64 4 925,69
        if DATE_LINE_RE.match(line):
            if current is not None:
                entries.append(current)

            parts = line.split()
            date_str = parts[0]
            amount_raw = parts[-2]
            category = " ".join(parts[3:-2])

            current = {
                "date": datetime.strptime(date_str, "%d.%m.%Y").date(),
                "category": category,
                "amount_raw": amount_raw,
                "description_lines": [],
            }
        else:
            if current is not None:
                current["description_lines"].append(line)

    if current is not None:
        entries.append(current)

    created = 0
    total = Decimal("0")

    for entry in entries:
        raw = entry["amount_raw"]

        # пополнения помечены знаком "+" перед суммой
        if "+" in raw:
            continue

        amount = _normalize_amount(raw)
        # Сбер выдаёт списания положительными числами — считаем их расходами как есть

        category_text = entry["category"].strip()
        if not category_text:
            category_text = "Uncategorized"

        # пропустим явные переводы/перемещения денег
        lowered = category_text.lower()
        if "перевод" in lowered:
            continue

        category, _ = ExpenseCategory.objects.get_or_create(
            user=user,
            name=category_text,
        )

        description = " ".join(entry["description_lines"]).strip()
        if not description:
            description = category_text

        Expense.objects.create(
            user=user,
            category=category,
            date=entry["date"],
            description=description[:255],
            amount=amount,
            bank="Sberbank",
            currency="RUB",
        )
        created += 1
        total += amount

    return created, total
