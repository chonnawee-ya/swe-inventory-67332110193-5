"""โมดูลคำนวณราคาและส่วนลด (Refactored Pricing Module)

ได้รับการปรับปรุงโครงสร้าง (Refactored) จาก pricing_legacy.py
โดยแก้ Code Smells ครบทุกจุด แยกฟังก์ชันตามความรับผิดชอบ (SRP),
ใช้ค่าคงที่สื่อความหมาย (Named Constants) และคงพฤติกรรมเดิมไว้ 100%
"""

from __future__ import annotations

import datetime
from typing import Sequence, Tuple, Union

# ค่าคงที่อัตราภาษีและส่วนลด (Named Constants)
TAX_RATE: float = 0.07
BULK_TIER_1_THRESHOLD: int = 50
BULK_TIER_1_MULTIPLIER: float = 0.95  # ส่วนลด 5%
BULK_TIER_2_THRESHOLD: int = 100
BULK_TIER_2_MULTIPLIER: float = 0.90  # ส่วนลด 10%
MEMBER_DISCOUNT_MULTIPLIER: float = 0.95  # สมาชิกลด 5%
MEMBER_POINTS_PER_BAHT: int = 100  # 1 แต้มต่อ 100 บาท

# สถานะประวัติและคะแนนสะสม (รักษาความเข้ากันได้กับระบบเดิม)
member_points: dict[str, int] = {}
LOG: list[tuple[str | None, float]] = []

ItemTuple = Union[Tuple[str, int, float], Sequence]


def calculate_item_subtotal(quantity: int, unit_price: float) -> float:
    """คำนวณราคาย่อยของสินค้าแต่ละรายการพร้อมส่วนลดตามปริมาณ (Bulk Discount)"""
    if quantity <= 0:
        return 0.0

    raw_total = quantity * unit_price
    if quantity >= BULK_TIER_2_THRESHOLD:
        return raw_total * BULK_TIER_2_MULTIPLIER
    if quantity >= BULK_TIER_1_THRESHOLD:
        return raw_total * BULK_TIER_1_MULTIPLIER
    return raw_total


def calculate_items_subtotal(items: Sequence[ItemTuple]) -> float:
    """คำนวณราคารวมของสินค้าทั้งหมดในคำสั่งซื้อ"""
    total = 0.0
    for item in items:
        name, quantity, unit_price = item[0], item[1], item[2]
        total += calculate_item_subtotal(quantity, unit_price)
    return total


def apply_member_benefits(total: float, member: str | None) -> float:
    """คำนวณส่วนลดสมาชิกและบันทึกแต้มสะสม"""
    if member is None:
        return total

    if member not in member_points:
        member_points[member] = 0

    discounted_total = total * MEMBER_DISCOUNT_MULTIPLIER
    earned_points = int(discounted_total / MEMBER_POINTS_PER_BAHT)
    member_points[member] += earned_points
    return discounted_total


def apply_coupon_discount(total: float, coupon: str | None, current_date: datetime.date | None) -> float:
    """คำนวณส่วนลดจากรหัสคูปองตามเงื่อนไข"""
    if coupon is None:
        return total

    if coupon == "SAVE50":
        return total - 50.0
    if coupon == "HALF":
        return total * 0.5
    if coupon == "NEWYEAR":
        check_date = current_date if current_date is not None else datetime.date.today()
        if check_date.month == 1:
            return total * 0.8
    return total


def apply_tax_and_rounding(total: float) -> float:
    """คำนวณภาษีมูลค่าเพิ่มและปัดเศษทศนิยม 2 ตำแหน่ง"""
    non_negative_total = max(0.0, total)
    total_with_tax = non_negative_total + (non_negative_total * TAX_RATE)
    return round(total_with_tax, 2)


def calc(
    items: Sequence[ItemTuple],
    member: str | None = None,
    coupon: str | None = None,
    today: datetime.date | None = None,
) -> float:
    """ฟังก์ชันหลักสำหรับคำนวณราคาสุทธิ (Main Orchestration)

    รักษา Signature และ Behavior ให้ตรงกับ pricing_legacy.calc 100%
    """
    subtotal = calculate_items_subtotal(items)
    after_member = apply_member_benefits(subtotal, member)
    after_coupon = apply_coupon_discount(after_member, coupon, today)
    final_price = apply_tax_and_rounding(after_coupon)

    LOG.append((member, final_price))
    return final_price
