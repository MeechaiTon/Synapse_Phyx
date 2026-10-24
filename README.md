# PhyxLab

Visual Lab ทางฟิสิกส์: จำลองการทดลอง ปรับพารามิเตอร์ และดูกราฟแบบเรียลไทม์

## เริ่มใช้งาน
```bash
npm test              # เทสฟิสิกส์ + ตรวจสัญญาของทุกการทดลอง (ต้องมี Node 20+)
```
เปิดหน้าเว็บ: เปิดโฟลเดอร์นี้ใน VS Code → คลิกขวา `index.html` → **Open with Live Server**
(ต้องมีอินเทอร์เน็ตเพื่อโหลดฟอนต์ Kanit และ Chart.js จาก CDN)

## สร้างการทดลองใหม่
```bash
npm run new -- singing-ruler "ไม้บรรทัดร้องเพลง" "Singing Ruler"
```
แล้วทำตามที่สคริปต์แจ้ง และอ่าน `CLAUDE.md` + `docs/05-WORKFLOW.md`

## เอกสาร
`CLAUDE.md` (กติกาหลัก) · `docs/01-PLAN.md` (แผน/สถานะ) · `docs/02-ARCHITECTURE.md` · `docs/03-CODING-STANDARD.md` · `docs/04-FEATURE-SPEC-TEMPLATE.md` · `docs/05-WORKFLOW.md`
