# Code Review Report: PR `inventory_service.py` - Lab 04

เอกสารรายงานการตรวจทานโค้ด (Code Review Report) สำหรับ Pull Request ไฟล์ `inventory_service.py` ที่สร้างโดย AI Coding Assistant ทำการตรวจสอบเชิงลึกโดยวิศวกรซอฟต์แวร์ตามมาตรฐานคุณภาพ สถาปัตยกรรม และความปลอดภัยของระบบ

---

## 1. ข้อมูลการ Review
* **เป้าหมาย PR:** โมดูล `InventoryService` (Batch Sale, Reservation, Price Query, Low Stock Alert, Thread-safe Restock, Unit Value Calculation)
* **สถานะการรันเบื้องต้น:** คอมไพล์ผ่าน รันได้ ไม่เกิด Syntax Error บน Happy Path
* **ผลการประเมินโดยมนุษย์:** **Request Changes (ไม่ผ่านการอนุมัติให้ Merge)** เนื่องจากพบบั๊กแฝงร้ายแรง (Latent Bugs) ทั้งประเด็น **Atomicity**, **Race Condition**, **Off-by-One / Boundary Mismatch**, และ **ZeroDivisionError**

---

## 2. รายละเอียด Review Comments รายจุด (ครบ 4 องค์ประกอบตามเกณฑ์ Rubric)

### จุดที่ 1: เมธอด `sell_batch` (การขายหลายรายการไม่เป็น Atomic)
* **1. ตำแหน่ง (Location):** เมธอด `sell_batch()`, บรรทัดที่ 16–22 (โดยเฉพาะลูปบรรทัดที่ 19–21 ในไฟล์ `inventory_service.py`)
* **2. ทำไมถึงผิด (Problem):** ขาดคุณสมบัติ **Atomicity (All-or-Nothing)** ฟังก์ชันวนลูปหักสต็อกทีละรายการทันที หากรายการก่อนหน้าตัดสำเร็จแล้ว แต่รายการถัดไปเกิดข้อผิดพลาด (เช่น สินค้าไม่พอจนเกิด `ValueError` หรือไม่พบสินค้าเกิด `KeyError`) สินค้าชุดแรกจะถูกหักสต็อกค้างไว้ในระบบถาวรโดยไม่มีการ Rollback คืนค่า
* **3. กรณีที่จะพังพร้อมค่าตัวอย่าง (Failing Case & Concrete Inputs):**
  * *ข้อมูลในคลังเริ่มต้น:*
    * `"Arduino Uno"` มี 10 ชิ้น
    * `"ESP32"` มี 2 ชิ้น
  * *คำสั่งซื้อ:* `orders = {"Arduino Uno": 5, "ESP32": 10}`
  * *พฤติกรรมที่พัง:*
    * รอบที่ 1: `"Arduino Uno"` ถูกหักออก 5 ชิ้น (คงเหลือลดลงเป็น 5 ชิ้น)
    * รอบที่ 2: `"ESP32"` ขอซื้อ 10 ชิ้น แต่มีแค่ 2 ชิ้น ➔ เกิด `ValueError: สินค้า 'ESP32' คงเหลือ 2 ชิ้น ไม่เพียงพอ...`
    * *ผลลัพธ์เสียหาย:* ฟังก์ชันหยุดทำงานกลางคัน คำสั่งซื้อรวมล้มเหลว แต่สต็อกของ `"Arduino Uno"` หายไปฟรี 5 ชิ้นโดยที่ลูกค้าไม่ได้ของ
* **4. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ใช้แนวคิด **Two-Phase Commit / Validation Phase Before Execution**:
  1. เฟส 1: ตรวจสอบความถูกต้องและสต็อกของทุกรายการใน `orders` ให้ครบถ้วนก่อน
  2. เฟส 2: ดำเนินการตัดสต็อกจริงเมื่อทุกรายการผ่านเกณฑ์ครบแล้ว
  ```python
  def sell_batch(self, orders: dict[str, int]) -> dict[str, int]:
      # Phase 1: Validate all
      for name, amount in orders.items():
          if name not in self._inv._items:
              raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
          if amount <= 0:
              raise ValueError("จำนวนที่ขายต้องมากกว่าศูนย์")
          if self._inv._items[name].quantity < amount:
              raise ValueError(f"สินค้า '{name}' สต็อกไม่เพียงพอ")
      # Phase 2: Execute
      result = {}
      for name, amount in orders.items():
          result[name] = self._inv.sell(name, amount)
      return result
  ```
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `high`

---

### จุดที่ 2: เมธอด `reserve` (แครชด้วย KeyError และสถานะการจองคลุมเครือ)
* **1. ตำแหน่ง (Location):** เมธอด `reserve()`, บรรทัดที่ 25–31 (โดยเฉพาะบรรทัดที่ 27, 29, 31 ในไฟล์ `inventory_service.py`)
* **2. ทำไมถึงผิด (Problem):**
  1. หากสินค้ายังไม่เคยถูกจองมาก่อน และผู้ใช้ขอจอง `amount` มากกว่าสต็อกคงเหลือ เงื่อนไข `if amount <= item.quantity - already:` จะเป็นเท็จ ทำให้ `self._reserved[name]` ไม่ถูกกำหนดค่า
  2. บรรทัดที่ 31 `return item.quantity - self._reserved[name]` จะพยายามเข้าถึง Key ที่ยังไม่มีอยู่ ส่งผลให้เกิด `KeyError: name` แครชทันที
  3. ฟังก์ชันไม่ส่งสัญญาณบอกผู้เรียกเมื่อการจองล้มเหลว (ควร raise Exception หรือคืนค่าที่ชัดเจน)
* **3. กรณีที่จะพังพร้อมค่าตัวอย่าง (Failing Case & Concrete Inputs):**
  * *ข้อมูลในคลังเริ่มต้น:* สินค้า `"Sensor"` มีสต็อก 5 ชิ้น, ใน `_reserved` ยังไม่มี Key `"Sensor"`
  * *คำสั่งเรียก:* `reserve("Sensor", 10)` (ขอจอง 10 ชิ้น)
  * *พฤติกรรมที่พัง:* เงื่อนไข `if 10 <= 5 - 0:` เป็น False บรรทัดที่ 30 ถูกข้าม พอถึงบรรทัดที่ 31 เกิด `KeyError: 'Sensor'` ทันที
* **4. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ตรวจสอบการมีอยู่ของสินค้าผ่าน Public API และตรวจสอบเงื่อนไขก่อนคำนวณ:
  ```python
  def reserve(self, name: str, amount: int) -> int:
      if name not in self._inv._items:
          raise KeyError(f"ไม่พบสินค้า '{name}' ในระบบ")
      if amount <= 0:
          raise ValueError("จำนวนที่จองต้องมากกว่าศูนย์")
      item = self._inv._items[name]
      already = self._reserved.get(name, 0)
      available = item.quantity - already
      if amount > available:
          raise ValueError(f"ไม่สามารถจอง '{name}' ได้ เหลือให้จองเพียง {available} ชิ้น")
      self._reserved[name] = already + amount
      return item.quantity - self._reserved[name]
  ```
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `high`

---

### จุดที่ 3: เมธอด `items_in_price_range` (ไม่ครอบคลุมค่าขอบตาม Docstring)
* **1. ตำแหน่ง (Location):** เมธอด `items_in_price_range()`, บรรทัดที่ 34–40 (บรรทัดที่ 38 ในไฟล์ `inventory_service.py`)
* **2. ทำไมถึงผิด (Problem):** Docstring ระบุสัญญาการทำงานว่า *"คืนรายชื่อสินค้าที่ราคาอยู่ในช่วง [low, high]"* สัญลักษณ์ก้ามปู `[...]` ในทางคณิตศาสตร์หมายถึงช่วงปิด (Closed Interval) ซึ่งต้องรวมค่าขอบทั้ง `low` และ `high` ด้วย แต่โค้ดใช้ Strict Inequality: `low < item.price < high`
* **3. กรณีที่จะพังพร้อมค่าตัวอย่าง (Failing Case & Concrete Inputs):**
  * *ข้อมูลในคลังเริ่มต้น:* สินค้า A ราคา `100.0` บาท, สินค้า B ราคา `500.0` บาท
  * *คำสั่งเรียก:* `items_in_price_range(100.0, 500.0)`
  * *พฤติกรรมที่พัง:* คืนค่า `[]` (ลิสต์ว่าง) สินค้าที่มีราคาเท่ากับ 100.0 และ 500.0 พอดีจะตกหล่นไปอย่างเงียบๆ
* **4. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  เปลี่ยนเครื่องหมายเปรียบเทียบเป็นช่วงปิด:
  ```python
  if low <= item.price <= high:
      names.append(name)
  ```
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `medium`

---

### จุดที่ 4: เมธอด `low_stock_report` (ไม่แจ้งเตือนสินค้าที่สต็อกเท่ากับเกณฑ์พอดี)
* **1. ตำแหน่ง (Location):** เมธอด `low_stock_report()`, บรรทัดที่ 43–49 (บรรทัดที่ 47 ในไฟล์ `inventory_service.py`)
* **2. ทำไมถึงผิด (Problem):** Docstring ระบุว่า *"คืนรายชื่อสินค้าที่ stock ต่ำกว่าหรือเท่ากับเกณฑ์"* แต่เงื่อนไขในโค้ดเขียนเพียง `item.quantity < self.LOW_STOCK_THRESHOLD` (ขาดเครื่องหมายเท่ากับ)
* **3. กรณีที่จะพังพร้อมค่าตัวอย่าง (Failing Case & Concrete Inputs):**
  * *ข้อมูลในคลังเริ่มต้น:* สินค้า C มีสต็อก `5` ชิ้น (`LOW_STOCK_THRESHOLD = 5`)
  * *คำสั่งเรียก:* `low_stock_report()`
  * *พฤติกรรมที่พัง:* สินค้า C ไม่ปรากฏในรายงาน ทำให้พนักงานคลังสินค้าไม่ได้รับการแจ้งเตือนสต็อกต่ำ จนสินค้าหมดสต็อกในที่สุด
* **4. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  เปลี่ยนเครื่องหมายเป็น `<=`:
  ```python
  if item.quantity <= self.LOW_STOCK_THRESHOLD:
      report.append(name)
  ```
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `medium`

---

### จุดที่ 5: เมธอด `concurrent_restock` (Race Condition / Lost Update จากการอ่านค่านอกล็อก)
* **1. ตำแหน่ง (Location):** เมธอด `concurrent_restock()`, บรรทัดที่ 52–58 (บรรทัดที่ 54–56 ในไฟล์ `inventory_service.py`)
* **2. ทำไมถึงผิด (Problem):** บรรทัดที่ 54 อ่านค่า `current = self._inv._items[name].quantity` **อยู่นอกบล็อก `with self._lock:`** หากมีหลายเธรดเข้ามาทำงานพร้อมกัน ทั้งสองเธรดจะอ่านค่า `current` เดิมไปพร้อมกัน แล้วเข้าไปแย่งกันบวกค่าทับลงในตัวแปรเดียวกัน ส่งผลให้เกิด **Lost Update Anomaly** สต็อกที่เติมเข้าไปจะสูญหาย
* **3. กรณีที่จะพังพร้อมค่าตัวอย่าง (Failing Case & Concrete Inputs):**
  * *ข้อมูลในคลังเริ่มต้น:* สินค้า D มีสต็อก `10` ชิ้น
  * *คำสั่งเรียกพร้อมกัน 2 Threads:*
    * Thread 1: `concurrent_restock("D", 5)`
    * Thread 2: `concurrent_restock("D", 5)`
  * *ลำดับเหตุการณ์ (Interleaving):*
    1. Thread 1 อ่าน `current = 10`
    2. Thread 2 อ่าน `current = 10`
    3. Thread 1 เข้า Lock ➔ เขียนค่า `10 + 5 = 15`
    4. Thread 2 เข้า Lock ➔ เขียนค่า `10 + 5 = 15`
  * *ผลลัพธ์เสียหาย:* สต็อกสุดท้ายกลายเป็น 15 ชิ้น แทนที่จะเป็น 20 ชิ้น (หายไป 5 ชิ้น)
* **4. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ย้ายการอ่านค่าเข้าไปอยู่ภายใต้ Lock หรือเรียกใช้ `restock()` ของ Inventory ภายใต้ Lock:
  ```python
  def concurrent_restock(self, name: str, amount: int) -> int:
      with self._lock:
          return self._inv.restock(name, amount)
  ```
* **หมวดหมู่ / ระดับความรุนแรง:** `concurrency` (หรือ `correctness`) / `high`

---

### จุดที่ 6: เมธอด `average_unit_value` (แครชหารด้วยศูนย์ และความหมายตัวหารผิด)
* **1. ตำแหน่ง (Location):** เมธอด `average_unit_value()`, บรรทัดที่ 60–64 (บรรทัดที่ 63–64 ในไฟล์ `inventory_service.py`)
* **2. ทำไมถึงผิด (Problem):**
  1. **ZeroDivisionError:** หากคลังสินค้าว่างเปล่า `len(self._inv._items)` จะเป็น `0` ทำให้เกิดการหารด้วยศูนย์ทันที
  2. **Semantic / Domain Error:** Docstring ระบุว่า *"มูลค่าเฉลี่ยต่อชิ้น"* (Per-unit average value) แต่ตัวหารใช้ `len(self._inv._items)` ซึ่งเป็นจำนวนชนิดสินค้า (SKU count) ไม่ใช่จำนวนชิ้นสินค้าทั้งหมด
* **3. กรณีที่จะพังพร้อมค่าตัวอย่าง (Failing Case & Concrete Inputs):**
  * *เคสแครช:* คลังสินค้าเปิดใหม่ยังไม่มีสินค้า `Inventory()` ➔ เรียก `average_unit_value()` ➔ แครชด้วย `ZeroDivisionError: division by zero`
  * *เคสคำนวณผิด:* สินค้า E มี 10 ชิ้น ชิ้นละ 100 บาท (มูลค่ารวม 1,000 บาท) มี 1 ชนิดสินค้า ➔ โค้ดคำนวณ `1000 / 1 = 1000 บาท/ชิ้น` ทั้งที่ความจริงเฉลี่ยชิ้นละ 100 บาท
* **4. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ```python
  def average_unit_value(self) -> float:
      total_units = sum(item.quantity for item in self._inv._items.values())
      if total_units == 0:
          return 0.0
      return self._inv.get_total_value() / total_units
  ```
* **หมวดหมู่ / ระดับความรุนแรง:** `correctness` / `high`

---

### จุดที่ 7: การละเมิด Encapsulation ทั่วทั้งคลาส
* **1. ตำแหน่ง (Location):** เมธอด `reserve`, `items_in_price_range`, `low_stock_report`, `concurrent_restock`, `average_unit_value`
* **2. ทำไมถึงผิด (Problem):** มีการเข้าถึงตัวแปร `self._inv._items` โดยตรง ซึ่งเป็นตัวแปรแบบ Private/Protected ของคลาส `Inventory` ทำให้เกิด Tight Coupling หากโครงสร้างภายในของ `Inventory` มีการปรับปรุง โค้ดส่วนนี้จะพังทั้งหมด
* **3. ข้อเสนอแนะในการแก้ไข (Constructive Fix):**
  ออกแบบ Public Method หรือ Property เช่น `get_items()` บนคลาส `Inventory` เพื่อส่งต่อข้อมูลอย่างถูกต้องตามหลัก OOP
* **หมวดหมู่ / ระดับความรุนแรง:** `style` / `low`

---

## 3. ตารางสรุปการจัดหมวดหมู่และระดับความรุนแรงของข้อบกพร่อง

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

## 4. การเปรียบเทียบกับ AI Reviewer
* **การทดสอบเทียบกับ AI Reviewer (เช่น Copilot / LLM):**
  * สิ่งที่ AI ตรวจพบได้ดี: AI มักตรวจพบจุดที่เห็นได้ชัดเจนในตัวโค้ด เช่น การหารด้วยศูนย์ (`ZeroDivisionError`) ใน `average_unit_value`
  * สิ่งที่ AI มักมองข้ามหรือวิเคราะห์ผิด:
    1. **Concurrency / Race Condition:** AI มักมองเห็นว่ามี `with self._lock:` แล้วสรุปทันทีว่าฟังก์ชัน Thread-safe แล้ว โดยมองข้ามว่าการอ่านค่าตัวแปรเกิดขึ้นก่อนหน้าบล็อก Lock
    2. **Atomicity / State Rollback:** AI มองไม่เห็นว่าการทยอยหักสต็อกทีละรายการจะทิ้ง Partial State เสียหายไว้หากมีข้อยกเว้นเกิดขึ้นกลางคัน
* **บทสรุปวิศวกรรม:** การตรวจทานโค้ด (Code Review) โดยมนุษย์ยังเป็นหัวใจสำคัญ เพราะมนุษย์เข้าใจ System Invariants, บริบททางธุรกิจ และเหตุการณ์ที่เกิดขึ้นจริงขณะรันระบบ

---

## 5. ตอบแบบฝึกหัดส่งท้าย (Post-Lab Exercises)

### 1. วิเคราะห์ bug ที่รันได้ปกติในกรณีทั่วไป แต่พังเฉพาะใน edge case หรือเมื่อหลาย thread ทำงานพร้อมกัน (2 ข้อ)
1. **`concurrent_restock` (Race Condition):**
   * *เหตุผลที่พังเฉพาะกรณีพิเศษ:* เมื่อรันแบบ Single Thread หรือรัน Unit Test ธรรมดาทีละฟังก์ชัน โค้ดจะอ่านค่าและบวกค่าได้ถูกต้องเสมอ 100% แต่เมื่อมี 2 Thread เข้ามาทำงานในช่วงเวลาคาบเกี่ยวกัน (Concurrent Execution) การอ่านค่านอก Lock จะทำให้เกิดปรากฏการณ์ **Lost Update** ข้อมูลบวกของ Thread หนึ่งจะถูกทับหายไปทันที
   * *ทำไม Test ธรรมดาจึงจับไม่เจอ:* Test ทั่วไปรันแบบเรียงลำดับทีละคำสั่ง (Sequential Execution) ไม่มีการจำลอง Thread Contention จึงไม่เกิด Race Condition
2. **`sell_batch` (Atomicity Violation):**
   * *เหตุผลที่พังเฉพาะกรณีพิเศษ:* หากรายการสินค้าทุกชิ้นในออร์เดอร์มีสต็อกเพียงพอ โค้ดจะทำงานสำเร็จลุล่วงอย่างราบรื่น แต่จะพังก็ต่อเมื่อเกิด Edge Case ที่รายการใดรายการหนึ่งตรงกลางหรือท้ายออร์เดอร์มีสต็อกไม่พอ ทำให้เกิด Partial Failure สต็อกถูกหักไปแล้วครึ่งหนึ่งแต่คำสั่งซื้อไม่สำเร็จ
   * *ทำไม Test ธรรมดาจึงจับไม่เจอ:* หาก Test ออกแบบมาเฉพาะ Happy Path (ออร์เดอร์ที่สต็อกพอเสมอ) จะไม่มีทางพบปัญหานี้ เว้นแต่จะจงใจเขียน Failure Scenario เพื่อตรวจสอบ State Rollback

### 2. ออกแบบ Test Case สำหรับตรวจจับ Bug Concurrency ใน `concurrent_restock`
ใช้ `threading` ใน `pytest` เพื่อจำลองการเติมสต็อกพร้อมกัน 10 Threads:

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
