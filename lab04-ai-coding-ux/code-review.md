# Code Review Report: PR `inventory_service.py` - Lab 04

เอกสารรายงานการตรวจทานโค้ด (Code Review) สำหรับ Pull Request ไฟล์ `inventory_service.py` ที่สร้างโดย AI Assistant ทำการวิเคราะห์จุดบกพร่อง ความเสี่ยง และข้อเสนอแนะในการปรับปรุงตามเกณฑ์วิศวกรรมซอฟต์แวร์

---

## สรุปภาพรวมของ PR
โค้ดใน PR นี้สามารถคอมไพล์และรันผ่านในกรณีทั่วไป (Happy Path) แต่จากการตรวจสอบเชิงลึกพบว่ามี **บั๊กแฝง (Latent Bugs)** ร้ายแรงหลายจุด ทั้งในด้าน **ความถูกต้อง (Correctness)**, **ความปลอดภัยของข้อมูลพร้อมกัน (Concurrency / Race Condition)**, **ขอบเขตข้อมูล (Boundary Conditions)**, และ **การละเมิดหลัก Encapsulation**

---

## รายละเอียด Review Comments รายจุด (ครบ 4 องค์ประกอบ)

### 1. `sell_batch` (บรรทัดที่ 421-427)
* **ตำแหน่ง:** เมธอด `sell_batch()`, บรรทัดที่ 424-426
* **ทำไมถึงผิด (Problem):** ขาดคุณสมบัติ **Atomicity (All-or-Nothing)** เมธอดวนลูปเรียก `self._inv.sell(name, amount)` ทีละรายการ หากรายการแรกตัดสต็อกสำเร็จแล้ว แต่รายการถัดไปเกิดข้อผิดพลาด (เช่น สต็อกไม่พอจนเกิด `ValueError` หรือไม่พบสินค้าเกิด `KeyError`) สินค้าในรายการก่อนหน้าจะถูกหักสต็อกค้างไว้ในระบบโดยไม่มีการ Rollback
* **กรณีที่จะพัง (Failing Case & Inputs):**
  * ข้อมูลเริ่มต้น: สินค้า A มี 10 ชิ้น, สินค้า B มี 2 ชิ้น
  * คำสั่ง: `sell_batch({"A": 5, "B": 10})`
  * ผลลัพธ์: สินค้า A ถูกหักออก 5 ชิ้น (เหลือ 5) แต่เมื่อถึงสินค้า B เกิด `ValueError: สินค้า 'B' คงเหลือ 2 ชิ้น ไม่เพียงพอ...` ทำให้ฟังก์ชันหยุดทำงานกลางคัน ข้อมูลสินค้า A หายไปจากคลัง แต่คำสั่งซื้อรวมล้มเหลว
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  แบ่งการทำงานเป็น 2 ขั้นตอน (Two-Phase Execution):
  1. ตรวจสอบสต็อกของทุกรายการใน `orders` ให้ครบก่อนว่ามีสินค้าจริงและสต็อกเพียงพอ
  2. เมื่อผ่านการตรวจสอบครบทุกรายการแล้ว จึงค่อยวนลูปตัดสต็อกจริง
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `high`

---

### 2. `reserve` (บรรทัดที่ 430-437)
* **ตำแหน่ง:** เมธอด `reserve()`, บรรทัดที่ 434-436
* **ทำไมถึงผิด (Problem):**
  1. หากสินค้าไม่เคยถูกจองมาก่อน (`already = 0`) และผู้ใช้ขอจอง `amount` มากกว่าสต็อกที่มี (`amount > item.quantity`) เงื่อนไขใน `if` จะเป็นเท็จ ทำให้ `self._reserved[name]` ไม่ถูกสร้าง
  2. เมื่อโค้ดทำงานมาถึงบรรทัดที่ 436 `return item.quantity - self._reserved[name]` โปรแกรมจะแครชทันทีด้วย `KeyError: name`
  3. นอกจากนี้ หากการจองล้มเหลว เมธอดไม่ควรคืนค่าตัวเลขเสมือนสำเร็จ แต่ควรแจ้งเตือนข้อผิดพลาด
* **กรณีที่จะพัง (Failing Case & Inputs):**
  * ข้อมูลเริ่มต้น: สินค้า C มี 5 ชิ้น, ยังไม่มีการจองใน `_reserved`
  * คำสั่ง: `reserve("C", 10)`
  * ผลลัพธ์: เกิดข้อผิดพลาด `KeyError: 'C'` ทันทีที่บรรทัด 436 โปรแกรมหยุดทำงาน
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ใช้ `.get(name, 0)` เมื่อเข้าถึง `self._reserved` และหากจำนวนที่ขอจองเกินสต็อกคงเหลือที่จองได้ ให้ raise `ValueError("จำนวนที่ขอจองเกินสต็อกที่มี")` แทนการปล่อยให้ทำงานต่อไป
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `high`

---

### 3. `items_in_price_range` (บรรทัดที่ 439-445)
* **ตำแหน่ง:** เมธอด `items_in_price_range()`, บรรทัดที่ 443
* **ทำไมถึงผิด (Problem):** เงื่อนไขขอบเขตไม่ตรงตาม Docstring โดย Docstring ระบุว่า *"คืนรายชื่อสินค้าที่ราคาอยู่ในช่วง [low, high]"* ซึ่งเป็นช่วงปิด (Closed Interval: รวมค่าปลายทั้งสองด้าน) แต่โค้ดใช้ Strict Inequality: `low < item.price < high` (ช่วงเปิด)
* **กรณีที่จะพัง (Failing Case & Inputs):**
  * ข้อมูลเริ่มต้น: สินค้า D ราคา 100.0 บาท, สินค้า E ราคา 500.0 บาท
  * คำสั่ง: `items_in_price_range(100.0, 500.0)`
  * ผลลัพธ์: คืนค่าเป็น list ว่าง `[]` ทั้งที่สินค้า D และ E มีราคาตรงกับช่วงราคาพอดี
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  เปลี่ยนเงื่อนไขเป็น `if low <= item.price <= high:`
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `medium`

---

### 4. `low_stock_report` (บรรทัดที่ 448-454)
* **ตำแหน่ง:** เมธอด `low_stock_report()`, บรรทัดที่ 452
* **ทำไมถึงผิด (Problem):** โค้ดใช้ `item.quantity < self.LOW_STOCK_THRESHOLD` ซึ่งไม่ตรงกับ Docstring ที่ระบุว่า *"คืนรายชื่อสินค้าที่ stock ต่ำกว่าหรือเท่ากับเกณฑ์"* ทำให้สินค้าที่มีจำนวนสต็อกเท่ากับเกณฑ์พอดี (5 ชิ้น) หลุดรอดจากการแจ้งเตือน
* **กรณีที่จะพัง (Failing Case & Inputs):**
  * ข้อมูลเริ่มต้น: สินค้า F มีจำนวนคงเหลือ 5 ชิ้น (`LOW_STOCK_THRESHOLD = 5`)
  * คำสั่ง: `low_stock_report()`
  * ผลลัพธ์: ไม่แสดงสินค้า F ในรายงาน ทำให้ฝ่ายคลังไม่ทราบว่าสินค้าถึงจุดสั่งซื้อซ้ำแล้ว
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  เปลี่ยนเครื่องหมายเปรียบเทียบเป็น `if item.quantity <= self.LOW_STOCK_THRESHOLD:`
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `medium`

---

### 5. `concurrent_restock` (บรรทัดที่ 457-463)
* **ตำแหน่ง:** เมธอด `concurrent_restock()`, บรรทัดที่ 459-461
* **ทำไมถึงผิด (Problem):** เกิดปัญหา **Race Condition (Lost Update Anomaly)** เนื่องจากบรรทัดที่ 459 อ่านค่า `current` ไว้นอก Lock (`with self._lock:`) หากมี 2 เธรดเข้ามาอ่านค่าพร้อมกัน ทั้งสองเธรดจะได้ค่า `current` ตัวเดิม แล้วเข้าไปบวกค่าทับกันในล็อก ส่งผลให้ยอดการเติมสต็อกของเธรดหนึ่งสูญหายไป
* **กรณีที่จะพัง (Failing Case & Inputs):**
  * ข้อมูลเริ่มต้น: สินค้า G มีสต็อก 10 ชิ้น
  * สองเธรดเรียกพร้อมกัน: Thread 1 เรียก `concurrent_restock("G", 5)` และ Thread 2 เรียก `concurrent_restock("G", 5)`
  * ผลลัพธ์: ทั้งคู่เห็น `current = 10` เมื่อเขียนค่าลงไป สต็อกสุดท้ายกลายเป็น 15 แทนที่จะเป็น 20 ชิ้น (หายไป 5 ชิ้น)
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ย้ายการอ่านค่า `current` เข้าไปอยู่ในบล็อก `with self._lock:` หรือเรียกใช้เมธอด `self._inv.restock(name, amount)` ภายในบล็อกล็อก
* **หมวดหมู่ / ระดับความรุนแรง:** `concurrency` (หรือ `correctness`) / `high`

---

### 6. `average_unit_value` (บรรทัดที่ 465-470)
* **ตำแหน่ง:** เมธอด `average_unit_value()`, บรรทัดที่ 468-469
* **ทำไมถึงผิด (Problem):**
  1. **ZeroDivisionError:** หากคลังสินค้ายังไม่มีสินค้าเลย (`len(self._inv._items) == 0`) จะเกิด Error การหารด้วยศูนย์
  2. **Semantic Error:** Docstring ระบุว่า *"มูลค่าเฉลี่ยต่อชิ้น"* (Per-unit value) แต่ตัวหารกลับใช้ `len(self._inv._items)` ซึ่งเป็นจำนวนรายการชนิดสินค้า (SKU Count) ไม่ใช่จำนวนชิ้นสินค้าทั้งหมด (Total Quantity)
* **กรณีที่จะพัง (Failing Case & Inputs):**
  * กรณีที่ 1: คลังสินค้าว่างเปล่า `Inventory()` ➔ เรียก `average_unit_value()` ➔ เกิด `ZeroDivisionError: division by zero`
  * กรณีที่ 2: สินค้า H มี 10 ชิ้น ชิ้นละ 100 บาท (มูลค่ารวม 1,000) มี 1 ชนิดสินค้า ➔ โค้ดคำนวณ `1000 / 1 = 1000 บาท/ชิ้น` ทั้งที่ความจริงเฉลี่ยชิ้นละ 100 บาท
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  คำนวณจำนวนชิ้นรวม `total_quantity = sum(item.quantity for item in self._inv._items.values())` หาก `total_quantity == 0` ให้คืนค่า `0.0` ทันที และคืนค่า `total_value / total_quantity` เมื่อมีสินค้า
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `high`

---

### 7. ภาพรวมของคลาส: การเข้าถึงข้อมูลภายในข้ามชั้น (Encapsulation Violation)
* **ตำแหน่ง:** หลายเมธอดแตะต้อง `self._inv._items` โดยตรง
* **ทำไมถึงผิด (Problem):** ตัวแปร `_items` มีเครื่องหมาย `_` นำหน้า แสดงว่าเป็นตัวแปร Private/Internal State ของคลาส `Inventory` การที่ `InventoryService` เข้าถึงโดยตรงทำให้เกิด Tight Coupling หากภายใน `Inventory` เปลี่ยนวิธีเก็บข้อมูล โค้ดของ Service จะพังทั้งหมด
* **ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  เพิ่ม Public Method เช่น `get_item(name)` หรือ `list_items()` บนคลาส `Inventory` แทนการเข้าถึง `_items` ข้ามคลาส
* **หมวดหมู่ / ระดับความรุนแรง:** `style` / `low`

---

## ตารางสรุปการจัดหมวดหมู่และระดับความรุนแรงของข้อบกพร่อง

| # | เมธอด | หมวด (Category) | ระดับ (Severity) | สรุปปัญหา | กรณีที่ทำให้พัง |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `sell_batch` | `correctness` | `high` | ไม่เป็น Atomic หากรายการหลังสต็อกไม่พอ รายการแรกถูกหักค้างไว้ | สั่งซื้อ 2 รายการ ชิ้นที่สองสต็อกไม่พอ ชิ้นแรกถูกหักฟรี |
| 2 | `reserve` | `correctness` | `high` | เกิด `KeyError` เมื่อจำนวนจองเกินสต็อก และไม่เคยจองมาก่อน | จองเกินสต็อกที่มีในครั้งแรก เช่น `reserve("X", 10)` ขณะมีของ 5 ชิ้น |
| 3 | `items_in_price_range` | `correctness` | `medium` | ใช้ `<` แทน `<=` ไม่นับสินค้าที่มีราคาตรงกับขอบพอดี | สินค้าราคา 100 บาท ไม่อยู่ในผลลัพธ์ของช่วง `[100, 200]` |
| 4 | `low_stock_report` | `correctness` | `medium` | ใช้ `<` แทน `<=` ข้ามสินค้าที่มีสต็อกเท่ากับเกณฑ์พอดี (5 ชิ้น) | สินค้าคงเหลือ 5 ชิ้น ไม่ถูกแจ้งเตือนสต็อกต่ำ |
| 5 | `concurrent_restock` | `concurrency` | `high` | อ่านค่านอกล็อก เกิด Lost Update เมื่อมีหลายเธรดทำงานพร้อมกัน | สองเธรดเติมของพร้อมกัน ยอดบวกของเธรดหนึ่งสูญหาย |
| 6 | `average_unit_value` | `correctness` | `high` | เกิด ZeroDivisionError เมื่อคลังว่าง และใช้ตัวหารเป็นชนิดสินค้าไม่ใช่จำนวนชิ้น | คลังสินค้าว่างเปล่า หรือมีสินค้า 1 ชนิดแต่มีหลายชิ้น |
| 7 | ภาพรวมคลาส | `style` | `low` | ละเมิด Encapsulation เข้าถึง `_items` ข้ามคลาสโดยตรง | เมื่อคลาส Inventory ปรับปรุงโครงสร้างภายใน |

---

## การเปรียบเทียบกับ AI Reviewer
* **การทดสอบเทียบกับ AI Reviewer (เช่น Copilot / LLM):**
  * สิ่งที่ AI ตรวจพบ: AI มักตรวจพบจุดที่เห็นได้ง่าย เช่น การหารด้วยศูนย์ (`ZeroDivisionError`) ใน `average_unit_value` และการสะกดตัวแปร
  * สิ่งที่ AI มักมองข้าม:
    1. AI มองข้ามประเด็น **Concurrency / Race Condition** ใน `concurrent_restock` เพราะมองเห็นบล็อก `with self._lock:` แล้วเข้าใจผิดว่าครอบคลุมแล้วโดยไม่ได้ดูว่าการอ่านค่าอยู่นอกล็อก
    2. AI มักมองข้าม **Atomicity / Rollback** ใน `sell_batch` เพราะโค้ดรันได้ปกติหากทุกรายการผ่าน
* **ข้อสรุป:** การตรวจทานโค้ด (Code Review) โดยวิศวกรซอฟต์แวร์ที่เป็นมนุษย์ยังคงมีความสำคัญสูงสุด เพราะต้องเข้าใจ Runtime Behavior, ขอบเขตของระบบ และความเสี่ยงทางธุรกิจ

---

## ตอบแบบฝึกหัดส่งท้าย (Post-Lab Exercises)

### 1. วิเคราะห์ bug ที่รันได้ปกติในกรณีทั่วไป แต่พังเฉพาะใน edge case หรือเมื่อหลาย thread ทำงานพร้อมกัน (2 ข้อ)
1. **`concurrent_restock` (Race Condition):**
   * *เหตุผลที่พังเฉพาะกรณีพิเศษ:* เมื่อรันแบบ Single Thread หรือรัน Unit Test ธรรมดาทีละฟังก์ชัน โค้ดจะอ่านค่าและบวกค่าได้ถูกต้องเสมอ 100% แต่เมื่อมี 2 Thread เข้ามาทำงานในช่วงเวลาคาบเกี่ยวกัน (Concurrent Execution) การอ่านค่านอก Lock จะทำให้เกิดปรากฏการณ์ **Lost Update** ข้อมูลบวกของ Thread หนึ่งจะถูกทับหายไปทันที
   * *ทำไม Test ธรรมดาจึงจับไม่เจอ:* Test ทั่วไปรันแบบเรียงลำดับทีละคำสั่ง (Sequential Execution) ไม่มีการจำลอง Thread Contention จึงไม่เกิด Race Condition
2. **`sell_batch` (Atomicity Violation):**
   * *เหตุผลที่พังเฉพาะกรณีพิเศษ:* หากรายการสินค้าทุกชิ้นในออร์เดอร์มีสต็อกเพียงพอ โค้ดจะทำงานสำเร็จลุล่วงอย่างราบรื่น แต่จะพังก็ต่อเมื่อเกิด Edge Case ที่รายการใดรายการหนึ่งตรงกลางหรือท้ายออร์เดอร์มีสต็อกไม่พอ ทำให้เกิด Partial Failure สต็อกถูกหักไปแล้วครึ่งหนึ่งแต่คำสั่งซื้อไม่สำเร็จ
   * *ทำไม Test ธรรมดาจึงจับไม่เจอ:* หาก Test ออกแบบมาเฉพาะ Happy Path (ออร์เดอร์ที่สต็อกพอเสมอ) จะไม่มีทางพบปัญหานี้ เว้นแต่จะจงใจเขียน Failure Scenario เพื่อตรวจสอบ State Rollback

### 2. ออกแบบ Test Case สำหรับตรวจจับ Bug Concurrency ใน `concurrent_restock`
ใช้ `threading` หรือ `concurrent.futures` ใน `pytest` เพื่อจำลองการเติมสต็อกพร้อมกัน 10 Threads:

```python
import threading
import pytest
from inventory import Inventory
from inventory_service import InventoryService


def test_concurrent_restock_race_condition():
    # Setup
    inv = Inventory()
    inv.add_item("TEST-ITEM", quantity=0, price=100.0)
    service = InventoryService(inv)

    num_threads = 10
    amount_per_thread = 5
    threads = []

    def worker():
        for _ in range(100):
            service.concurrent_restock("TEST-ITEM", amount_per_thread)

    # รัน 10 threads พร้อมกันเพื่อสร้างการแย่งชิงทรัพยากร (Contention)
    for _ in range(num_threads):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # สต็อกสุดท้ายที่คาดหวัง: 10 threads * 100 loops * 5 units = 5,000 units
    expected_quantity = num_threads * 100 * amount_per_thread
    actual_quantity = inv._items["TEST-ITEM"].quantity

    # โค้ดเดิมที่อ่านค่านอก Lock จะ fail ที่ assertion นี้ เพราะ actual < expected
    assert actual_quantity == expected_quantity, (
        f"เกิด Lost Update! คาดหวัง {expected_quantity} แต่ได้ {actual_quantity}"
    )
```
* **คำอธิบาย:** การจำลองใช้ Thread จำนวนหลายตัววนลูปเติมสต็อกซ้ำ ๆ ในจังหวะเวลาเดียวกัน เพื่อเพิ่มความน่าจะเป็นในการเกิด Context Switching ระหว่างบรรทัดที่อ่านค่า `current` กับบรรทัดที่เขียนค่าลงใน Lock โค้ดที่มีบั๊กจะไม่ผ่าน Assertion นี้อย่างแน่นอน
