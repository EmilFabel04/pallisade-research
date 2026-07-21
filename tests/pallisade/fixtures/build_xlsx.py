"""Run once: python tests/pallisade/fixtures/build_xlsx.py"""
from pathlib import Path
from openpyxl import Workbook


def build(out: Path) -> None:
    wb = Workbook()
    s1 = wb.active
    s1.title = "Assumptions"
    s1.append(["Metric", "FY24", "FY25", "FY26"])
    s1.append(["Revenue ($M)", 42.3, 51.8, 62.4])
    s1.append(["EBITDA margin %", 21.2, 23.0, 24.5])
    s2 = wb.create_sheet("DebtSchedule")
    s2.append(["Year", "Beginning", "Paydown", "Ending"])
    s2.append([2024, 200, 20, 180])
    wb.save(out)


if __name__ == "__main__":
    out = Path(__file__).parent / "model.xlsx"
    build(out)
    print(f"wrote {out}")
