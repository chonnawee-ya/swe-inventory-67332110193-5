# Debugging Log - Lab 04

เอกสารบันทึกกระบวนการสืบหาและแก้ไขข้อผิดพลาด (Evidence-Based Debugging) ในโมดูล `discount.py` ตามระเบียบวิธี 5 ขั้นตอน (Reproduce ➔ Traceback ➔ Hypothesis ➔ Confirmation ➔ Fix & Re-run)

---

## สรุปผลการรันชุดทดสอบเริ่มต้น (Initial Run)
* **คำสั่ง:** `python -m pytest tests/ -v`
* **ผลลัพธ์:** ผ่าน 2 ข้อ, **ล้มเหลว 4 ข้อ** (`test_apply_discount_basic`, `test_bulk_total`, `test_average_price_empty`, `test_cheapest_n`)

---

## บันทึกการ Debug รายจุดตาม 5 ขั้นตอน

### จุดที่ 1: `test_apply_discount_basic` (และส่งผลต่อ `test_bulk_total`)

#### 1. Reproduce
* **คำสั่ง:** `python -m pytest tests/test_discount.py -k test_apply_discount_basic -v`
* **Assertion Failure:**
  ```text
  assert apply_discount(100.0, 10) == 90.0
  E assert 99.9 == 90.0
  E  + where 99.9 = apply_discount(100.0, 10)
  ```

#### 2. Traceback
* **ตำแหน่ง:** ไฟล์ `discount.py`, บรรทัดที่ 5 ในฟังก์ชัน `apply_discount`
  ```python
  return price - percent / 100
  ```

#### 3. สมมติฐาน (Hypothesis)
สูตรคำนวณส่วนลดผิดพลาด โดยโค้ดคำนวณ `percent / 100` แล้วนำไปลบออกจากราคาตรง ๆ (เช่น `100 - (10/100) = 100 - 0.1 = 99.9`) แทนที่จะคิดเป็นเปอร์เซ็นต์ของราคาเต็ม คือ `(price * percent) / 100` หรือ `price * (1 - percent / 100)`

#### 4. การยืนยัน (Confirmation)
ทดลองรันคำนวณใน Python Interactive Shell:
```python
price = 100.0; percent = 10
print(price - percent / 100)          # ได้ 99.9 (ตรงกับ failure)
print(price - (price * percent / 100)) # ได้ 90.0 (ตรงกับค่าที่คาดหวัง)
```
ยืนยันว่าข้อผิดพลาดเกิดจากสูตรทางคณิตศาสตร์ไม่ได้นำ `price` มาคูณกับอัตราส่วนลด

#### 5. Root Cause และการแก้ (Fix & Re-run)
* **Root Cause:** ลำดับและตัวดำเนินการทางคณิตศาสตร์ไม่ถูกต้อง ลืมนำ `price` มาคูณสัดส่วนลด
* **การแก้ไข:** แก้ไขบรรทัดที่ 5 ใน `discount.py` เป็น:
  ```python
  def apply_discount(price: float, percent: float) -> float:
      """ลดราคาตาม percent (0-100) คืนราคาหลังลด"""
      if percent < 0 or percent > 100:
          raise ValueError("ส่วนลดต้องอยู่ระหว่าง 0 ถึง 100")
      return price * (1 - percent / 100)
  ```
* **ผลกระทบ:** แก้ไขจุดนี้ทำให้ `test_apply_discount_basic` และ `test_bulk_total` ผ่านการทดสอบทันทีทั้งสองข้อ

---

### จุดที่ 2: `test_average_price_empty`

#### 1. Reproduce
* **คำสั่ง:** `python -m pytest tests/test_discount.py -k test_average_price_empty -v`
* **Assertion / Error Failure:**
  ```text
  ZeroDivisionError: division by zero
  discount.py:18: in average_price
  return sum(prices) / len(prices)
  ```

#### 2. Traceback
* **ตำแหน่ง:** ไฟล์ `discount.py`, บรรทัดที่ 18 ในฟังก์ชัน `average_price`
  ```python
  return sum(prices) / len(prices)
  ```

#### 3. สมมติฐาน (Hypothesis)
ฟังก์ชันไม่ได้ดักจับกรณีที่อาร์กิวเมนต์ `prices` เป็นลิสต์ว่าง (`[]`) ส่งผลให้ `len(prices)` คืนค่าเป็น `0` ทำให้เกิดการหารด้วยศูนย์ (`ZeroDivisionError`) เมื่อรันคำสั่ง `sum([]) / 0`

#### 4. การยืนยัน (Confirmation)
ทดลองพิมพ์ค่า `len(prices)` เมื่อส่งลิสต์ว่างเข้าไป:
```python
prices = []
print(len(prices))  # ได้ 0
# เกิด ZeroDivisionError เมื่อใช้เป็นตัวหาร
```
ยืนยันว่าโค้ดขาด Guard Clause สำหรับกรณีลิสต์ว่าง

#### 5. Root Cause และการแก้ (Fix & Re-run)
* **Root Cause:** ขาดการตรวจสอบความยาวของลิสต์ก่อนดำเนินการหาร ทำให้โปรแกรมแครชเมื่อคลังสินค้าว่างเปล่า
* **การแก้ไข:** เพิ่มเงื่อนไขตรวจสอบว่าลิสต์ว่างหรือไม่ หากว่างให้คืนค่า `0.0` ทันที:
  ```python
  def average_price(prices: list) -> float:
      """คืนราคาเฉลี่ยของรายการสินค้า"""
      if not prices:
          return 0.0
      return sum(prices) / len(prices)
  ```

---

### จุดที่ 3: `test_cheapest_n`

#### 1. Reproduce
* **คำสั่ง:** `python -m pytest tests/test_discount.py -k test_cheapest_n -v`
* **Assertion Failure:**
  ```text
  assert cheapest_n([50.0, 10.0, 30.0, 20.0], 2) == [10.0, 20.0]
  E assert [20.0] == [10.0, 20.0]
  E   At index 0 diff: 20.0 != 10.0
  E   Right contains one more item: 20.0
  ```

#### 2. Traceback
* **ตำแหน่ง:** ไฟล์ `discount.py`, บรรทัดที่ 24 ในฟังก์ชัน `cheapest_n`
  ```python
  ordered = sorted(prices)
  return ordered[1:n]
  ```

#### 3. สมมติฐาน (Hypothesis)
การตัดช่วงข้อมูล (List Slicing) เริ่มต้นที่ดัชนีผิด โดยโค้ดใช้ `[1:n]` ทำให้ข้ามสมาชิกตัวแรกที่ดัชนี `0` (ซึ่งเป็นตัวที่ถูกที่สุดคือ `10.0`) ไป และการตัดช่วงถึง `n` ใน Python จะไม่รวมตัวที่ `n` ส่งผลให้กรณี `n = 2` คืนค่าเพียง `ordered[1:2]` ซึ่งได้แค่ `[20.0]`

#### 4. การยืนยัน (Confirmation)
ทดลอง Slice ใน Python:
```python
prices = [50.0, 10.0, 30.0, 20.0]
ordered = sorted(prices) # ได้ [10.0, 20.0, 30.0, 50.0]
print(ordered[1:2]) # ได้ [20.0] (ขาดตัวแรกและได้ไม่ครบ n ตัว)
print(ordered[:2])  # ได้ [10.0, 20.0] (ถูกต้องครบ 2 ตัว)
```
ยืนยันว่า Slice ต้องเริ่มจากดัชนี 0 คือ `[:n]`

#### 5. Root Cause และการแก้ (Fix & Re-run)
* **Root Cause:** การตัดช่วงผิดขอบเขต (Off-by-one / Wrong Start Index) สับสนระหว่าง 1-based indexing กับ 0-based indexing ใน Python
* **การแก้ไข:** แก้ไขเป็น `ordered[:max(0, n)]` (เริ่มจากตัวแรกสุดและตัดมา `n` ตัว พร้อมป้องกันกรณี `n <= 0`):
  ```python
  def cheapest_n(prices: list, n: int) -> list:
      """คืน n รายการที่ราคาถูกที่สุด เรียงจากถูกไปแพง"""
      if n <= 0:
          return []
      ordered = sorted(prices)
      return ordered[:n]
  ```

---

## ตารางสรุปการ Debug

| Test ที่ไม่ผ่าน | Traceback / Assertion ที่เห็น | สมมติฐาน Root Cause | วิธียืนยัน | การแก้ |
| :--- | :--- | :--- | :--- | :--- |
| `test_apply_discount_basic` | `assert 99.9 == 90.0` | สูตรลืมคูณ `price` คิดผิดเป็นลบ 0.1 | คำนวณสูตรใน interactive shell | เปลี่ยนเป็น `price * (1 - percent / 100)` |
| `test_bulk_total` | `assert 299.9 == 270.0` | ผลพวงมาจาก `apply_discount` สูตรผิด | ตรวจสอบ flow การเรียก `bulk_total` | ได้รับการแก้ไขทันทีเมื่อแก้ `apply_discount` |
| `test_average_price_empty` | `ZeroDivisionError: division by zero` | ไม่ดักจับลิสต์ว่าง ทำให้ `len([]) == 0` | พิมพ์ `len([])` แล้วทดลองหาร | เพิ่ม Guard clause `if not prices: return 0.0` |
| `test_cheapest_n` | `assert [20.0] == [10.0, 20.0]` | Slice `[1:n]` ข้าม index 0 | ทดลอง slice ลิสต์ที่เรียงแล้ว | เปลี่ยนเป็น `ordered[:n]` (เริ่มจาก index 0) |

---

## กับดักที่ตั้งใจวางไว้ (Edge Case Trap)
* **ข้อสังเกต:** `test_apply_discount_zero` ผ่านตั้งแต่แรกทั้งที่สูตรผิด เพราะเมื่อ `percent = 0` คำนวณ `price - 0/100 = price` ค่าตรงกันโดยบังเอิญ
* **บทเรียน:** Test ที่ผ่านไม่ได้แปลว่าฟังก์ชันทำงานถูกต้องเสมอไป ต้องตรวจสอบ Business Logic และ Edge Cases ประกอบด้วย
