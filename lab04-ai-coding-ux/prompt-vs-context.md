# การเปรียบเทียบ Prompt Engineering กับ Context Engineering - Lab 04

เอกสารนี้แสดงการทดลองสั่งงาน AI จำนวน 2 รอบในงานเดียวกัน เพื่อเปรียบเทียบผลลัพธ์ระหว่างการใช้ **Prompt สั้น (Prompt Engineering เพียงอย่างเดียว)** กับการใช้ **Prompt ที่แนบ Context ครบถ้วน (Context Engineering)**

---

## งานที่ต้องการให้ทำ
เพิ่มฟังก์ชันสำหรับขายสินค้าหลายรายการพร้อมกันในคลาส `Inventory` ของระบบจัดการสต็อกสินค้า

---

## การทดลองรอบที่ 1: Prompt สั้น ๆ (Prompt ที่ขาดบริบท)

### Prompt ที่ส่งให้ AI:
```text
เขียน function ภาษา Python สำหรับลด stock สินค้าหลายรายการพร้อมกันในระบบ inventory
```

### ผลลัพธ์ที่ AI สร้างให้ (Output รอบที่ 1):
```python
def sell_multiple_items(inventory, items_to_sell):
    # items_to_sell is a dictionary of {item_name: quantity}
    for item, qty in items_to_sell.items():
        if item in inventory:
            if inventory[item] >= qty:
                inventory[item] -= qty
                print(f"Sold {qty} of {item}")
            else:
                print(f"Not enough stock for {item}")
        else:
            print(f"Item {item} not found")
    return inventory
```

### ปัญหาของผลลัพธ์รอบที่ 1:
1. **ไม่ตรงตาม Interface เดิม:** คลาส `Inventory` เดิมเก็บสินค้าเป็นอ็อบเจกต์ `InventoryItem` ใน `self._items` แต่ AI กลับสมมติขึ้นมาเองว่า `inventory` เป็น dict ธรรมดา
2. **ไม่เป็น Atomic (ขาดความปลอดภัยของข้อมูล):** หากรายการที่ 1 ตัดสต็อกสำเร็จ แต่รายการที่ 2 สต็อกไม่พอ ระบบได้ตัดสต็อกรายการแรกไปแล้ว (ข้อมูลเสียหาย ไม่มี Rollback)
3. **การจัดการข้อผิดพลาดไม่ถูกต้อง:** ใช้ `print()` แทนที่จะ raise Exception ตามมาตรฐานของระบบ (`KeyError` หรือ `ValueError`)
4. **ไม่สามารถเขียน Unit Test ตรวจสอบได้ง่าย:** ฟังก์ชันคืนค่า dict ธรรมดาและไม่มี contract ที่แน่นอน

---

## การทดลองรอบที่ 2: Prompt ที่แนบ Context ครบถ้วน (Context Engineering)

### Prompt ที่ส่งให้ AI:
```text
ปรับปรุงคลาส Inventory ด้านล่างให้รองรับการขายหลายรายการพร้อมกัน

[บริบทโค้ดเดิม - inventory.py]:
class InventoryItem:
    def __init__(self, name: str, quantity: int, price: float):
        if not name or not name.strip():
            raise ValueError("ชื่อสินค้าต้องไม่ว่างเปล่า")
        if quantity < 0:
            raise ValueError("จำนวนสินค้าต้องไม่ติดลบ")
        if price <= 0:
            raise ValueError("ราคาต้องมากกว่าศูนย์")
        self.name = name.strip()
        self.quantity = quantity
        self.price = price

class Inventory:
    def __init__(self):
        self._items: dict[str, InventoryItem] = {}

    def sell(self, name: str, amount: int) -> int:
        if name not in self._items:
            raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
        if amount <= 0:
            raise ValueError("จำนวนที่ขายต้องมากกว่าศูนย์")
        if self._items[name].quantity < amount:
            raise ValueError(f"สินค้า '{name}' คงเหลือ {self._items[name].quantity} ชิ้น ไม่เพียงพอสำหรับการขาย {amount} ชิ้น")
        self._items[name].quantity -= amount
        return self._items[name].quantity

[ข้อกำหนด (Requirements)]:
1. เพิ่มเมธอด `sell_many(orders: dict[str, int]) -> dict[str, int]` ในคลาส Inventory ที่คืน {ชื่อสินค้า: จำนวนคงเหลือหลังขาย}
2. คุณสมบัติ Atomic Transaction: หากมีรายการใดรายการหนึ่งสต็อกไม่พอ หรือไม่พบสินค้า ต้อง raise Exception และต้องไม่มีการหักสต็อกของรายการใดเลย (All or Nothing)
3. ชนิด Exception ต้องตรงกับเมธอดเดิม: KeyError เมื่อไม่พบสินค้า, ValueError เมื่อสต็อกไม่พอหรือจำนวน <= 0
4. ห้ามใช้ external library ภายนอก

[เกณฑ์ Test Case ที่ต้องผ่าน]:
- ขาย 2 รายการสำเร็จ: คืนคงเหลือที่ถูกต้องทั้ง 2 รายการ
- หากรายการที่ 2 สต็อกไม่พอ: ต้อง raise ValueError และสต็อกรายการที่ 1 ต้องไม่ถูกตัด (Rollback / No State Change)
```

### ผลลัพธ์ที่ AI สร้างให้ (Output รอบที่ 2):
```python
    def sell_many(self, orders: dict[str, int]) -> dict[str, int]:
        """ขายสินค้าหลายรายการพร้อมกันแบบ Atomic

        Args:
            orders: dict ของ {ชื่อสินค้า: จำนวนที่ต้องการซื้อ}

        Returns:
            dict ของ {ชื่อสินค้า: จำนวนคงเหลือหลังขาย}
        """
        # ขั้นที่ 1: ตรวจสอบความถูกต้องและสต็อกของทุกรายการก่อน (Validation Phase)
        for name, amount in orders.items():
            if name not in self._items:
                raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
            if amount <= 0:
                raise ValueError("จำนวนที่ขายต้องมากกว่าศูนย์")
            if self._items[name].quantity < amount:
                raise ValueError(
                    f"สินค้า '{name}' คงเหลือ {self._items[name].quantity} ชิ้น "
                    f"ไม่เพียงพอสำหรับการขาย {amount} ชิ้น"
                )

        # ขั้นที่ 2: ดำเนินการตัดสต็อกจริงเมื่อทุกรายการผ่านเกณฑ์ครบถ้วน (Execution Phase)
        result = {}
        for name, amount in orders.items():
            self._items[name].quantity -= amount
            result[name] = self._items[name].quantity

        return result
```

---

## บทสรุปการเปรียบเทียบ

| มิติการเปรียบเทียบ | รอบที่ 1 (Prompt สั้น) | รอบที่ 2 (Prompt + Context ครบถ้วน) |
| :--- | :--- | :--- |
| **ความเข้ากันได้กับโค้ดเดิม (Compatibility)** | ไม่เข้ากันเลย AI สุ่มโครงสร้างข้อมูลใหม่ทั้งหมด | สอดคล้องกับคลาส `Inventory` และ `InventoryItem` 100% |
| **ความถูกต้องทางตรรกะ (Logic & Atomicity)** | บกพร่องอย่างรุนแรง ตัดสต็อกบางส่วนทิ้งไว้เมื่อมี error | ปลอดภัยแบบ Atomic ตรวจสอบสต็อกครบก่อนตัดจริง |
| **Error Handling** | ใช้ `print()` ไม่สามารถดักจับ error ในโค้ดอื่นได้ | ใช้ `KeyError` และ `ValueError` ตามมาตรฐานเดิม |
| **การนำไปใช้งานจริง (Production-readiness)** | ใช้งานไม่ได้ ต้องเขียนใหม่ทั้งหมด | ใช้งานได้ทันที ผ่าน Unit Test ครบถ้วน |

### อะไรทำให้ผลลัพธ์ต่างกัน?
ความแตกต่างไม่ได้อยู่ที่ "ความฉลาดของ AI" แต่อยู่ที่ **Context Engineering**:
1. การแนบ **Interface เดิม** ทำให้ AI ทราบ Type และ Data Structure ที่แท้จริง
2. การระบุ **Constraints (ข้อจำกัดเรื่อง Atomic)** ป้องกันไม่ให้ AI เขียนโค้ดที่รันได้แต่นำพาบั๊กซ่อนเร้นมาสู่ระบบ
3. การระบุ **Test criteria** ทำให้ AI คิดย้อนกลับ (Reverse Engineering) ว่าโค้ดต้องรองรับ Edge Case ใดบ้าง
