# Test Gap Analysis: เมธอด `sell` ของคลาส `Inventory` - Lab 05

เอกสารวิเคราะห์ช่องว่างของการทดสอบ (Test Gap Analysis) เปรียบเทียบระหว่างชุด Unit Test ที่สร้างโดย AI ด้วยคำสั่งทั่วไป กับกรณีทดสอบเสริมที่พัฒนาโดยวิศวกรซอฟต์แวร์เพื่อดักจับ Edge Cases และ Error Paths

---

## 1. คำสั่ง Prompt ที่ใช้สั่ง AI
```text
ช่วยเขียน pytest unit test สำหรับเมธอด sell ของ class Inventory ให้หน่อย
```

## 2. โค้ด Test ที่ AI สร้างให้ (ชุดเบื้องต้นที่ผ่านง่ายเกินไป)
```python
def test_sell_success():
    inv = Inventory()
    inv.add_item("Arduino Uno", 10, 450.0)
    remaining = inv.sell("Arduino Uno", 3)
    assert remaining == 7
    assert inv._items["Arduino Uno"].quantity == 7
```
> **ข้อสังเกต:** AI มักสร้างเฉพาะกรณีปกติ (Happy Path) ที่ขายจำนวนน้อยกว่าสต็อก และสินค้ามีอยู่ในระบบเสมอ ทำให้ดูเหมือนโค้ดทำงานถูกต้อง 100% แต่ไม่ได้ทดสอบกรณีขอบเขต (Boundary Cases) หรือเส้นทางข้อผิดพลาด (Exception Handling) เลย

---

## 3. ตารางวิเคราะห์ Test Gap (ตาราง 3 คอลัมน์)

| กรณีที่ AI ให้มา (AI Baseline) | กรณีที่ขาด (Missing / Edge Cases) | Test ที่เราเขียนเสริม (Augmented Test) |
| :--- | :--- | :--- |
| **กรณีปกติ (Happy Path):** ขายสินค้าจำนวนทั่วไปแล้วสต็อกลดลงอย่างถูกต้อง | **ค่าขอบ (Boundary Value):** ขายสินค้าเท่ากับจำนวนคงเหลือทั้งหมดพอดี (สต็อกต้องกลายเป็น 0) | `test_sell_boundary_exact_quantity()` |
| *(ไม่มี)* | **ค่าที่ไม่ควรรับ (Invalid Input):** พยายามขายสินค้าด้วยจำนวน `0` (ต้อง raise `ValueError` ว่าต้องมากกว่าศูนย์) | `test_sell_invalid_zero_amount()` |
| *(ไม่มี)* | **ค่าที่ไม่ควรรับ (Negative Input):** พยายามขายสินค้าด้วยจำนวนติดลบ เช่น `-5` (ต้อง raise `ValueError`) | `test_sell_invalid_negative_amount()` |
| *(ไม่มี)* | **กรณีสินค้าไม่พอ (Over-selling):** สั่งซื้อจำนวนมากกว่าสต็อกคงเหลือที่มี (ต้อง raise `ValueError` และสต็อกต้องไม่ลด) | `test_sell_insufficient_stock_error()` |
| *(ไม่มี)* | **เส้นทาง Error (Non-existent Item):** ขายสินค้าที่ไม่มีอยู่ในคลัง (ต้อง raise `KeyError`) | `test_sell_non_existent_item_error()` |

---

## 4. สรุปบทเรียน
จำนวน Test ที่ผ่านไม่ได้เป็นตัวการันตีว่าระบบปลอดภัย หาก Test ไม่ได้ครอบคลุม Exception Paths และ Boundary Conditions การตรวจสอบ Test Gaps ด้วยมนุษย์จึงเป็นขั้นตอนสำคัญที่ขาดไม่ได้ในการพัฒนาซอฟต์แวร์ร่วมกับ AI
