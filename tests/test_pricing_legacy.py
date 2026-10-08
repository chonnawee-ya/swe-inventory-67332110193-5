import datetime
import pytest
from pricing import calc, member_points, LOG


@pytest.fixture(autouse=True)
def reset_globals():
    """ล้างสถานะของตัวแปร Global ก่อนเริ่มการทดสอบแต่ละข้อเพื่อป้องกัน State Pollution"""
    member_points.clear()
    LOG.clear()
    yield
    member_points.clear()
    LOG.clear()


# ==========================================
# Characterization Tests: บันทึกพฤติกรรมจริงของ pricing_legacy
# ==========================================

def test_pricing_normal():
    # กลุ่ม 1: ราคาปกติ สินค้า 1 รายการ ไม่ใช้สิทธิ์ใดๆ
    # 1 ชิ้น * 100.0 บาท = 100.0 + ภาษี 7% = 107.0 บาท
    result = calc([("Resistor", 1, 100.0)])
    assert result == 107.0


def test_pricing_bulk_discounts():
    # กลุ่ม 2: ซื้อจำนวนมาก ตรวจสอบที่เกณฑ์ 50 ชิ้น และ 100 ชิ้น พอดี
    # เกณฑ์ 50 ชิ้น: ลด 5% -> 50 * 10.0 * 0.95 = 475.0 -> + ภาษี 7% = 508.25 บาท
    res_50 = calc([("LED", 50, 10.0)])
    assert res_50 == 508.25

    # เกณฑ์ 100 ชิ้น: ลด 10% -> 100 * 10.0 * 0.90 = 900.0 -> + ภาษี 7% = 963.0 บาท
    res_100 = calc([("LED", 100, 10.0)])
    assert res_100 == 963.0


def test_pricing_zero_quantity():
    # กลุ่ม 3: จำนวนเป็นศูนย์ -> สินค้าที่มีจำนวน <= 0 จะถูกข้าม ยอดรวมเป็น 0.0
    result = calc([("Capacitor", 0, 50.0), ("Diode", -2, 20.0)])
    assert result == 0.0


def test_pricing_member_benefits():
    # กลุ่ม 4: สมาชิก -> สมาชิกลด 5% และสะสมแต้ม 1 แต้มต่อ 100 บาท (คำนวณจากยอดหลังลดสมาชิก)
    # 10 ชิ้น * 100.0 = 1000.0 -> ลดสมาชิก 5% = 950.0 -> แต้ม = int(950/100) = 9 แต้ม
    # ยอดรวม + ภาษี 7% = 950.0 * 1.07 = 1016.5 บาท
    result = calc([("Arduino", 10, 100.0)], member="somsak")
    assert result == 1016.5
    assert member_points["somsak"] == 9


def test_pricing_coupons():
    # กลุ่ม 5: คูปองทุกรหัสที่โค้ดรู้จัก
    # คูปอง SAVE50: ลด 50 บาท -> (100 - 50) * 1.07 = 53.5 บาท
    assert calc([("Item", 1, 100.0)], coupon="SAVE50") == 53.5

    # คูปอง HALF: ลด 50% -> (100 * 0.5) * 1.07 = 53.5 บาท
    assert calc([("Item", 1, 100.0)], coupon="HALF") == 53.5

    # คูปอง NEWYEAR: ในเดือนมกราคมลด 20% -> (100 * 0.8) * 1.07 = 85.6 บาท
    d_jan = datetime.date(2026, 1, 15)
    assert calc([("Item", 1, 100.0)], coupon="NEWYEAR", today=d_jan) == 85.6

    # คูปอง NEWYEAR: นอกเดือนมกราคมไม่ได้ลด -> 100 * 1.07 = 107.0 บาท
    d_feb = datetime.date(2026, 2, 15)
    assert calc([("Item", 1, 100.0)], coupon="NEWYEAR", today=d_feb) == 107.0


def test_pricing_negative_total_floors_at_zero():
    # กลุ่ม 6: ยอดติดลบ -> ราคาสินค้า 30 บาท ใช้คูปอง SAVE50 (-50) -> ยอดติดลบจะถูกปรับเป็น 0.0
    result = calc([("Pen", 1, 30.0)], coupon="SAVE50")
    assert result == 0.0


def test_pricing_global_log_storage():
    # กลุ่ม 7: ค่าที่ฟังก์ชันบันทึกไว้ใน LOG นอกเหนือจากค่าที่คืนออกมา
    calc([("Item A", 1, 100.0)], member="bob")
    assert len(LOG) == 1
    assert LOG[0] == ("bob", 101.65)  # (100 * 0.95) * 1.07 = 101.65
