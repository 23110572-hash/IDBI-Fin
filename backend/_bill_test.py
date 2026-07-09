import os
os.environ["MSME_DATABASE_URL"] = "sqlite:///./_billtest.db"
from fastapi.testclient import TestClient
from app.main import app

BILL = ("STATE ELECTRICITY BOARD - TAX INVOICE\nConsumer No: 1234567\n"
        "Sanctioned Load: 25.0 kW\nUnits Consumed: 8200 kWh\n"
        "Bill Amount: Rs. 72,500.00\nDue Date: 2026-07-15\n")

with TestClient(app) as c:
    tok = c.post("/auth/login", data={"username": "rm", "password": "rm123!"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    ids = {"urn": "UDYAM-MH-03-1234567", "pan": "ABCDE1234F", "gstin": "27ABCDE1234F1Z5"}
    s = c.post("/score", json={"identifiers": ids}, headers=h).json()
    print("origination score:", s["health_card"]["composite_score"],
          "electricity_available:", s["health_card"]["available_sources"]["electricity"])

    r = c.post("/bill/upload",
               data={"urn": ids["urn"], "pan": ids["pan"], "gstin": ids["gstin"]},
               files={"file": ("bill.txt", BILL, "text/plain")}, headers=h)
    print("upload status:", r.status_code)
    b = r.json()
    print("OCR:", b["ocr"])
    enr = b["enrichment"]
    print("enriched score:", enr.get("composite_score"),
          "electricity_available:", enr.get("health_card", {}).get("available_sources", {}).get("electricity"))
    print("OK bill upload + enrichment works")
