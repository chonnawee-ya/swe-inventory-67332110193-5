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


# ==========================================
# Phase 2: Tests for sell() method (AI + Augmented Edge Cases)
# ==========================================

def test_sell_success_ai_baseline():
    # กรณี AI ให้มา: ขายปกติ
    inv = Inventory()
    inv.add_item("Arduino Uno", 10, 450.0)
    remaining = inv.sell("Arduino Uno", 3)
    assert remaining == 7
    assert inv._items["Arduino Uno"].quantity == 7


def test_sell_boundary_exact_quantity():
    # เสริม 1: ขายเท่ากับจำนวนที่เหลือทั้งหมดพอดี -> ต้องเหลือ 0
    inv = Inventory()
    inv.add_item("ESP32", 5, 250.0)
    remaining = inv.sell("ESP32", 5)
    assert remaining == 0
    assert inv._items["ESP32"].quantity == 0


def test_sell_invalid_zero_amount():
    # เสริม 2: ขายจำนวน 0 -> ต้อง raise ValueError
    inv = Inventory()
    inv.add_item("Sensor", 10, 50.0)
    with pytest.raises(ValueError, match="จำนวนที่ขายต้องมากกว่าศูนย์"):
        inv.sell("Sensor", 0)
    assert inv._items["Sensor"].quantity == 10


def test_sell_invalid_negative_amount():
    # เสริม 3: ขายจำนวนติดลบ -> ต้อง raise ValueError
    inv = Inventory()
    inv.add_item("Sensor", 10, 50.0)
    with pytest.raises(ValueError, match="จำนวนที่ขายต้องมากกว่าศูนย์"):
        inv.sell("Sensor", -3)
    assert inv._items["Sensor"].quantity == 10


def test_sell_insufficient_stock_error():
    # เสริม 4: ขายเกินสต็อกคงเหลือ -> ต้อง raise ValueError และสต็อกคงเดิม
    inv = Inventory()
    inv.add_item("Raspberry Pi", 2, 1500.0)
    with pytest.raises(ValueError, match="ไม่เพียงพอสำหรับการขาย"):
        inv.sell("Raspberry Pi", 3)
    assert inv._items["Raspberry Pi"].quantity == 2


def test_sell_non_existent_item_error():
    # เสริม 5: ขายสินค้าที่ไม่มีในคลัง -> ต้อง raise KeyError
    inv = Inventory()
    with pytest.raises(KeyError, match="ไม่พบสินค้า 'Ghost Item' ในระบบ"):
        inv.sell("Ghost Item", 1)


# ==========================================
# Phase 3: Comprehensive Coverage for Inventory
# ==========================================

def test_add_item_duplicate_name_error():
    inv = Inventory()
    inv.add_item("Relay Module", 10, 45.0)
    with pytest.raises(ValueError, match="มีอยู่ในระบบแล้ว"):
        inv.add_item("Relay Module", 5, 45.0)


def test_restock_success():
    inv = Inventory()
    inv.add_item("Relay Module", 10, 45.0)
    new_qty = inv.restock("Relay Module", 15)
    assert new_qty == 25
    assert inv._items["Relay Module"].quantity == 25


def test_restock_non_existent_item_error():
    inv = Inventory()
    with pytest.raises(KeyError, match="ไม่พบสินค้า"):
        inv.restock("Missing Item", 5)


def test_restock_invalid_amount_error():
    inv = Inventory()
    inv.add_item("Relay Module", 10, 45.0)
    with pytest.raises(ValueError, match="จำนวนที่เติมต้องมากกว่าศูนย์"):
        inv.restock("Relay Module", 0)


def test_get_total_value():
    inv = Inventory()
    assert inv.get_total_value() == 0.0
    inv.add_item("Item 1", 2, 100.0)
    inv.add_item("Item 2", 3, 50.0)
    assert inv.get_total_value() == 350.0


def test_inventory_item_validations():
    with pytest.raises(ValueError, match="ชื่อสินค้าต้องไม่ว่างเปล่า"):
        Inventory().add_item("   ", 1, 10.0)
    with pytest.raises(ValueError, match="จำนวนสินค้าต้องไม่ติดลบ"):
        Inventory().add_item("Item", -1, 10.0)
    with pytest.raises(ValueError, match="ราคาต้องมากกว่าศูนย์"):
        Inventory().add_item("Item", 1, 0.0)
