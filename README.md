# BJP Local Hoymiles

Home Assistant Custom Integration สำหรับอ่านข้อมูล Hoymiles DTU-Pro-S ผ่าน
Local Network โดยตรง ไม่พึ่ง S-Miles Cloud และไม่ต้องใช้อินเทอร์เน็ตตอน runtime

Integration นี้เป็น read-only เท่านั้น ไม่มี service, button, number, select,
switch หรือคำสั่งใดที่เขียนค่ากลับไปยัง DTU/Inverter

## Supported Test Setup

- Hoymiles DTU-Pro-S firmware `V00.06.05`
- TCP port `10081`
- Meter DDSU666
- Inverter 2 ตัว รวม 8 MPPT
- Data source: `hoymiles-wifi==0.5.6` และคำสั่ง read-only real-time data

## Installation via HACS

1. เปิด HACS ใน Home Assistant
2. ไปที่ Custom repositories
3. เพิ่ม repository นี้เป็น category `Integration`
4. ติดตั้ง `BJP Local Hoymiles`
5. Restart Home Assistant
6. ไปที่ Settings > Devices & services > Add integration
7. เลือก `BJP Local Hoymiles`
8. ใส่ IP/hostname, port และ scan interval

ค่าเริ่มต้น:

- Port: `10081`
- Scan interval: `35` วินาที
- ช่วง scan interval ที่อนุญาต: `35-300` วินาที

## Sensors

Integration จะสร้าง sensors อัตโนมัติจากอุปกรณ์ที่ DTU รายงาน:

- DTU: Solar power, daily solar energy, lifetime solar energy, home load, last update
- Meter: grid import/export power, net grid power, voltage, current, power factor,
  lifetime imported/exported energy
- Inverter: active power, daily/lifetime energy, voltage, current, power factor,
  temperature, link status
- MPPT: power, voltage, current
- Diagnostic sensors เช่น firmware raw, warning number, signal strength, MPPT error
  code และ fault code จะถูกสร้างแบบ disabled by default

ค่า daily energy ที่ DTU ส่งมาโดยตรงจะถูก expose เป็น sensor แต่ข้อมูลย้อนหลังและ
กราฟระยะยาวควรใช้ Recorder, Utility Meter และ Integration Sensor ของ Home Assistant

## Read-Only Safety

Integration อนุญาตเฉพาะ read-only adapter methods:

- `async_get_snapshot()`
- `async_get_network_info()`
- `async_get_app_information()`

ไม่มีการเรียกคำสั่งควบคุม เช่น set power limit, zero export, restart DTU,
firmware update, turn inverter on/off, performance mode หรือ energy-storage setter

## Development

โปรเจกต์ใช้ Miniconda environment ชื่อ `hoymiles` เป็นหลัก หากมี environment
นี้อยู่แล้ว:

```bash
conda activate hoymiles
python tools/run_checks.py
```

หรือสั่งจาก environment อื่นโดยไม่ต้อง activate:

```bash
conda run -n hoymiles python tools/run_checks.py
```

สร้างหรืออัปเดต environment จากไฟล์ของโปรเจกต์:

```bash
conda env create -f environment.yml
conda env update -n hoymiles -f environment.yml --prune
```

ตรวจ parser, safety, version และไฟล์ทั้งหมดโดยไม่ต้องติดตั้ง Home Assistant
หรือ pytest:

```bash
conda run -n hoymiles python tools/run_checks.py
```

ทดลองแสดงผลจาก fixture:

```bash
conda run -n hoymiles python tools/dtu_monitor.py \
  --fixture tests/fixtures/real_data_new.json
```

ทดลองกับ DTU จริง:

```bash
conda run -n hoymiles python tools/dtu_monitor.py \
  --host 192.168.30.213
```

ดูค่าต่อเนื่องทุก 35 วินาที กด `Ctrl+C` เพื่อหยุด:

```bash
conda run -n hoymiles python tools/dtu_monitor.py \
  --host 192.168.30.213 --watch
```

ดู normalized snapshot แบบ JSON:

```bash
conda run -n hoymiles python tools/dtu_monitor.py \
  --host 192.168.30.213 --json
```

เครื่องมือนี้เรียกเฉพาะ `async_get_real_data_new()` และไม่ต้องเปิด Home
Assistant ส่วนการทดสอบ Config Flow, Entity Registry และ HACS installation
ยังต้องตรวจใน Home Assistant ก่อน release จริงหนึ่งรอบ

ใน VSCode ให้เลือก Python Interpreter เป็น:

```text
/Users/bordin/miniconda3/envs/hoymiles/bin/python
```

## Version and Releases

- Version ปัจจุบัน: `0.2.2`
- ใช้ version จาก `custom_components/bjp_local_hoymiles/manifest.json`
- ทุกการเปลี่ยนแปลงต้องเพิ่ม version และอัปเดต `CHANGELOG.md`
- ตอนเผยแพร่ ให้สร้าง GitHub Release จาก tag รูปแบบ `vX.Y.Z` และใช้เนื้อหาของ
  version นั้นจาก `CHANGELOG.md` เป็น Release description เพื่อให้ HACS แสดง
  release notes ได้
- การสร้าง tag อย่างเดียวไม่ถือว่าเป็น release สำหรับ HACS

## เอกสารสำคัญ

| File | Purpose |
| --- | --- |
| `AGENTS.md` | กติกาและบริบทสำหรับ coding agents |
| `docs/SPEC.md` | เป้าหมาย ขอบเขต และ acceptance criteria |
| `docs/ARCHITECTURE.md` | components, data flow และข้อจำกัดทางเทคนิค |
| `docs/DEVELOPMENT.md` | workflow สำหรับพัฒนา ทดสอบ และส่งมอบ |
| `docs/decisions/` | Architecture Decision Records (ADRs) |
| `CHANGELOG.md` | Version history และ GitHub/HACS release notes |
| `environment.yml` | Miniconda development environment |

## เริ่มต้นพัฒนาเอกสาร

1. อ่าน `AGENTS.md`, `docs/SPEC.md` และ `docs/ARCHITECTURE.md`
2. บันทึกการตัดสินใจสำคัญเป็น ADR
3. เพิ่ม fixture ที่ลบข้อมูลลับแล้วสำหรับ payload รุ่นใหม่
4. พัฒนาเป็นชิ้นงานเล็กที่ตรวจสอบ acceptance criteria ได้

## หลักการ

- Local-first: ฟังก์ชันหลักไม่ควรพึ่งพา internet
- Read-only first: เริ่มจากการอ่านข้อมูลก่อนสั่งงานอุปกรณ์
- Observable: ปัญหาการเชื่อมต่อและข้อมูลผิดปกติต้องตรวจสอบย้อนหลังได้
- Secure by default: secrets ไม่อยู่ใน source control
- Document decisions: การตัดสินใจสำคัญต้องมีเหตุผลและผลกระทบ
