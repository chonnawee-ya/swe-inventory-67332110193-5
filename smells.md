# รายการ Code Smells ในโมดูล `pricing_legacy.py` - Lab 05

เอกสารระบุข้อบกพร่องด้านโครงสร้างและคุณภาพโค้ด (Code Smells) ตามหลักการของ Martin Fowler และ Kent Beck ที่ตรวจพบในไฟล์ `pricing_legacy.py` ก่อนเริ่มกระบวนการ Refactoring

---

## รายการ Code Smells ที่ตรวจพบ (อย่างน้อย 5 ข้อ)

### 1. Long Method & Single Responsibility Principle Violation
* **ตำแหน่ง:** ฟังก์ชัน `calc()`, บรรทัดที่ 12-56
* **ปัญหา:** ฟังก์ชันเดียวทำหน้าที่มากเกินไป (God Function) ได้แก่ คำนวณราคาย่อย, คิดส่วนลดตามจำนวนซื้อ, คิดส่วนลดสมาชิก, คำนวณแต้มสะสม, ตรวจสอบและลดคูปองตามปฏิทิน, คำนวณภาษี, ปัดเศษ และบันทึก Log ขาดการแบ่งแยกความรับผิดชอบ (SRP)
* **แนวทางแก้ไข (Refactoring):** Extract Function แยกตรรกะออกเป็นฟังก์ชันย่อย เช่น `apply_bulk_discount`, `apply_member_benefits`, `apply_coupon`, และ `calculate_tax`

---

### 2. Global Mutable State & Unexpected Side Effects
* **ตำแหน่ง:** บรรทัดที่ 8 (`member_points = {}`) และบรรทัดที่ 9 (`LOG = []`)
* **ปัญหา:** ใช้ตัวแปร Global ระดับโมดูลในการเก็บข้อมูลสะสม ทำให้ฟังก์ชันมีสถานะค้างข้ามการเรียกแต่ละครั้ง (Stateful / Side Effects) ส่งผลให้การทดสอบเกิด Cross-test contamination (รันเดี่ยวผ่าน แต่รันทั้งชุดไม่ผ่านเพราะข้อมูลค้าง)
* **แนวทางแก้ไข (Refactoring):** ห่อหุ้มสถานะเป็นคลาส `PricingService` หรือรับ `PointsRepository` เข้ามาแบบ Dependency Injection เพื่อให้ฟังก์ชันเป็น Pure Function และทดสอบแยกเดี่ยวได้

---

### 3. Primitive Obsession & Positional Indexing
* **ตำแหน่ง:** บรรทัดที่ 20-27 (`i[1]`, `i[2]`)
* **ปัญหา:** ใช้ข้อมูล Tuple แบบดิบ `(name, quantity, price)` และเข้าถึงข้อมูลด้วยดัชนีตัวเลข `i[1]`, `i[2]` ซึ่งอ่านยากมาก ไม่สื่อความหมาย และเสี่ยงต่อ `IndexError` หากโครงสร้างข้อมูลเปลี่ยน
* **แนวทางแก้ไข (Refactoring):** ใช้ `dataclass` หรือ `NamedTuple` เช่น `OrderItem(name: str, quantity: int, price: float)` เพื่อให้อ่านผ่าน Attribute ที่สื่อความหมาย (`item.quantity`, `item.price`)

---

### 4. Magic Numbers
* **ตำแหน่ง:** บรรทัดที่ 24-28 (`100`, `0.9`, `50`, `0.95`), บรรทัดที่ 34 (`0.95`), บรรทัดที่ 48 (`0.8`)
* **ปัญหา:** มีตัวเลขคงที่ (Hardcoded literals) ฝังอยู่ในโค้ดโดยไม่มีชื่อตัวแปรกำกับความหมาย เช่น ไม่ทราบว่า `0.9` คือส่วนลด 10% สำหรับการสั่งซื้อจำนวนมาก หรือ `0.95` คือสิทธิพิเศษสมาชิก 5%
* **แนวทางแก้ไข (Refactoring):** Replace Magic Literal with Symbolic Constant เช่น `BULK_TIER_2_QTY = 100`, `BULK_TIER_2_DISCOUNT = 0.10`, `MEMBER_DISCOUNT = 0.05`

---

### 5. Poor & Cryptic Naming
* **ตำแหน่ง:** บรรทัดที่ 17-56 (ตัวแปร `t`, `sub`, `i`)
* **ปัญหา:** ตัวแปรสั้นเกินไป ไม่สื่อความหมาย (`t` แทนยอดเงินรวม, `sub` แทนราคาย่อยของรายการสินค้า, `i` แทนสินค้าแต่ละรายการ) ทำให้อ่านทำความเข้าใจยากและเสี่ยงต่อการผิดพลาดเมื่อเข้ามาดูแลโค้ดต่อ
* **แนวทางแก้ไข (Refactoring):** Rename Variable ให้ชัดเจน เช่น เปลี่ยน `t` เป็น `total_amount`, `sub` เป็น `subtotal`, `i` เป็น `order_item`

---

### 6. Hidden Time Dependency (Non-deterministic Logic)
* **ตำแหน่ง:** บรรทัดที่ 46 (`datetime.date.today()`)
* **ปัญหา:** ฟังก์ชันผูกติดกับนาฬิกาจริงของระบบคอมพิวเตอร์ ทำให้ผลลัพธ์ของคูปอง `"NEWYEAR"` เปลี่ยนแปลงไปตามเดือนที่รันคำสั่ง (ในเดือนมกราคมได้ลด 20% แต่เดือนอื่นไม่ได้) ส่งผลให้การทดสอบไม่เสถียร (Flaky Test)
* **แนวทางแก้ไข (Refactoring):** บังคับใช้ Parameter วันที่ หรือจำลอง Date Provider ในการทดสอบ
