# Product Specification

## 1. Summary

BJP Local Hoymiles เป็น Home Assistant Custom Integration แบบ local-first
สำหรับอ่านข้อมูล Hoymiles DTU-Pro-S ผ่าน TCP ในเครือข่ายภายใน โดยไม่พึ่ง
S-Miles Cloud ตอน runtime

เอกสารนี้เป็น living specification สิ่งที่ยังไม่ยืนยันจะระบุเป็น `TBD`

## 2. Problem Statement

ผู้ดูแลระบบต้องการเห็นสถานะและประวัติการผลิตไฟฟ้าภายในสถานที่ โดยไม่ต้องพึ่งพา
cloud เป็นช่องทางหลัก และต้องสามารถตรวจสอบได้เมื่ออุปกรณ์หยุดส่งข้อมูลหรือค่า
การผลิตผิดปกติ

## 3. Target Users

- เจ้าของหรือผู้ดูแลระบบผลิตไฟฟ้าขนาดเล็ก
- ผู้ดูแลระบบ local network หรือ home server
- ช่างเทคนิคที่ต้องตรวจสอบสถานะย้อนหลัง

## 4. Goals

- อ่านค่าปัจจุบันจาก Hoymiles DTU-Pro-S ผ่าน TCP port `10081`
- สร้าง Home Assistant sensors อัตโนมัติผ่าน Config Flow
- แสดงภาพรวมกำลังผลิต พลังงานสะสม กริด โหลดบ้าน และสถานะอุปกรณ์
- ตรวจพบและแสดงปัญหาการเชื่อมต่อหรือข้อมูลขาดช่วง
- ติดตั้งผ่าน HACS ได้

## 5. Non-Goals for MVP

- ควบคุมหรือเปลี่ยนค่าของ inverter จากระบบ
- zero export control, power limit, restart, firmware update หรือ performance mode
- ทดแทนระบบ safety หรือ protection ของงานไฟฟ้า
- รองรับผู้ผลิตอุปกรณ์ทุกยี่ห้อ
- billing, trading หรือการคำนวณรายได้ที่มีผลทางกฎหมาย
- mobile application แบบ native
- การดึงกราฟย้อนหลังจาก DTU เป็นแหล่งหลัก
- การเก็บ time series database แยกจาก Home Assistant Recorder

## 6. MVP User Stories

1. ในฐานะผู้ดูแล ฉันเห็นกำลังผลิตรวมล่าสุดและเวลาที่ข้อมูลถูกอัปเดต
2. ในฐานะผู้ดูแล ฉันเห็นสถานะของอุปกรณ์แต่ละตัวและจุดที่ขาดการเชื่อมต่อ
3. ในฐานะผู้ดูแล ฉันใช้ Home Assistant Recorder/Utility Meter เพื่อดูกราฟและคำนวณย้อนหลังได้
4. ในฐานะผู้ดูแล ฉันทราบชัดเจนเมื่อข้อมูลล้าสมัยหรือเก็บข้อมูลไม่สำเร็จ
5. ในฐานะผู้ดูแล ฉัน export หรือสำรองข้อมูลของระบบได้

## 7. Functional Requirements

### Device Discovery and Configuration

- `FR-01` ระบบกำหนดอุปกรณ์เป้าหมายผ่าน Home Assistant Config Flow ได้
- `FR-02` ระบบตรวจสอบ configuration ก่อนเริ่ม polling
- `FR-03` device identifiers และ network addresses ต้องไม่ถูก commit โดยไม่ตั้งใจ

### Data Collection

- `FR-10` ระบบอ่าน telemetry ตามช่วงเวลาที่กำหนดได้ โดยค่าเริ่มต้นคือ 35 วินาที
- `FR-11` การ poll ซ้ำต้องไม่สร้างข้อมูลซ้ำอย่างไม่ควบคุม
- `FR-12` ความล้มเหลวชั่วคราวต้องไม่ทำให้ service หยุดถาวร
- `FR-13` ระบบบันทึกเวลาที่วัด เวลาที่รับข้อมูล และคุณภาพของข้อมูลเมื่อมี

### Data and Presentation

- `FR-20` ระบบสร้าง sensors สำหรับ DTU, meter, inverter และ MPPT โดยอัตโนมัติ
- `FR-21` ระบบแสดงข้อมูลย้อนหลังตามช่วงเวลาที่เลือก
- `FR-22` ระบบแยกสถานะ online, stale, unavailable และ unknown ได้
- `FR-23` ระบบแสดงหน่วยวัดและ timezone อย่างชัดเจน

### Operations

- `FR-30` diagnostics ต้องช่วยวิเคราะห์ปัญหาได้โดยไม่เปิดเผย IP หรือ serial เต็ม
- `FR-31` Integration ต้อง unload/reload ได้จาก Home Assistant

## 8. Non-Functional Requirements

- `NFR-01 Availability`: ฟังก์ชันหลักทำงานใน LAN ที่ไม่มี internet
- `NFR-02 Security`: ค่าเริ่มต้นไม่เปิด service สู่ public internet
- `NFR-03 Privacy`: ข้อมูลเฉพาะสถานที่อยู่ใน local storage ตามค่าเริ่มต้น
- `NFR-04 Reliability`: temporary network failure ต้อง recover ได้
- `NFR-05 Performance`: polling ต้องไม่ถี่กว่า 35 วินาทีตามค่า validation
- `NFR-06 Portability`: deployment ต้องทำซ้ำได้จากเอกสารและ versioned configuration
- `NFR-07 Time`: จัดเก็บเวลาหลักเป็น UTC และแปลง timezone ตอนแสดงผล

## 9. MVP Acceptance Criteria

- ระบบอ่าน telemetry จากอุปกรณ์ทดสอบผ่าน Config Flow ได้
- เมื่ออุปกรณ์หายจาก network ระบบยังทำงานและแสดงสถานะ unavailable/stale
- การ restart service ไม่ลบข้อมูลเดิมและไม่สร้าง duplicate จำนวนมาก
- ผู้ใช้เห็น current power, daily energy, device status, grid import/export,
  home load และ last update
- ผู้ใช้สร้างกราฟย้อนหลังด้วย Home Assistant Recorder/Utility Meter ได้
- การใช้งานหลักทั้งหมดผ่าน LAN ได้โดยไม่ใช้ internet

## 10. Open Questions

- `TBD` inverter models ที่อยู่หลัง DTU-Pro-S นอกเหนือจากชุดทดสอบ
- `TBD` ช่องทาง alert ที่ต้องการ

## 11. Change Policy

เมื่อ requirement เปลี่ยน:

1. แก้เอกสารนี้และ acceptance criteria ที่เกี่ยวข้อง
2. ประเมินผลกระทบใน `docs/ARCHITECTURE.md`
3. สร้าง ADR หากเป็นการตัดสินใจที่เปลี่ยนโครงสร้างหรือข้อจำกัดสำคัญ
