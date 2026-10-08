import pytest
from inventory import Inventory


# ==========================================
# Phase 1: TDD for low_stock_items(threshold)
# ==========================================

def test_low_stock_items_all_above_threshold():
    # กรณี 1: สินค้าทุกรายการมีจำนวนมากกว่า threshold -> คืน list ว่าง
    inv = Inventory()
    inv.add_item("Arduino Uno", 20, 450.0)
    inv.add_item("Raspberry Pi", 15, 1500.0)
    assert inv.low_stock_items(10) == []


def test_low_stock_items_exact_threshold():
    # กรณี 2: มีสินค้าที่จำนวนเท่ากับ threshold พอดี -> ต้องถูกนับรวมด้วย (<=)
    inv = Inventory()
    inv.add_item("NodeMCU", 5, 120.0)
    inv.add_item("ESP32", 10, 250.0)
    assert inv.low_stock_items(5) == ["NodeMCU"]


def test_low_stock_items_multiple_sorted_by_name():
    # กรณี 3: มีสินค้าเข้าเกณฑ์หลายรายการ -> ผลลัพธ์เรียงตามชื่อ ไม่ใช่ตามลำดับที่เพิ่ม
    inv = Inventory()
    inv.add_item("Sensor Z", 3, 50.0)
    inv.add_item("Arduino Nano", 2, 180.0)
    inv.add_item("Cable Micro USB", 4, 35.0)
    inv.add_item("Big Motor", 50, 400.0)  # เกินเกณฑ์

    # สินค้าที่เข้าเกณฑ์คือ Sensor Z, Arduino Nano, Cable Micro USB
    # ผลลัพธ์ต้องเรียงตามตัวอักษร: "Arduino Nano", "Cable Micro USB", "Sensor Z"
    assert inv.low_stock_items(5) == ["Arduino Nano", "Cable Micro USB", "Sensor Z"]


def test_low_stock_items_empty_inventory():
    # กรณี 4: คลังว่าง -> คืน list ว่าง ไม่ใช่ error
    inv = Inventory()
    assert inv.low_stock_items(10) == []


def test_low_stock_items_threshold_zero():
    # กรณี 5: threshold เป็น 0 -> คืนเฉพาะสินค้าที่เหลือ 0
    inv = Inventory()
    inv.add_item("Out of Stock Item", 0, 99.0)
    inv.add_item("In Stock Item", 1, 199.0)
    assert inv.low_stock_items(0) == ["Out of Stock Item"]


def test_low_stock_items_negative_threshold():
    # กรณี 6: threshold ติดลบ -> คืน list ว่าง
    inv = Inventory()
    inv.add_item("Item A", 0, 100.0)
    inv.add_item("Item B", 5, 200.0)
    assert inv.low_stock_items(-1) == []
