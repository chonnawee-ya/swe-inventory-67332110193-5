# discount.py  -- โมดูลคิดส่วนลดและสรุปยอด (ฉบับแก้ไขผ่านการ debug แล้ว)

def apply_discount(price: float, percent: float) -> float:
    """ลดราคาตาม percent (0-100) คืนราคาหลังลด"""
    if percent < 0 or percent > 100:
        raise ValueError("ส่วนลดต้องอยู่ระหว่าง 0 ถึง 100")
    return price * (1 - percent / 100)


def bulk_total(prices: list, discount_percent: float) -> float:
    """รวมราคาหลายรายการแล้วลดส่วนลดรวมทีเดียว"""
    total = 0.0
    for p in prices:
        total += p
    return apply_discount(total, discount_percent)


def average_price(prices: list) -> float:
    """คืนราคาเฉลี่ยของรายการสินค้า"""
    if not prices:
        return 0.0
    return sum(prices) / len(prices)


def cheapest_n(prices: list, n: int) -> list:
    """คืน n รายการที่ราคาถูกที่สุด เรียงจากถูกไปแพง"""
    if n <= 0:
        return []
    ordered = sorted(prices)
    return ordered[:n]
