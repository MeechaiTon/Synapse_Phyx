"""
Ohm's Law lab — interactive simulation with analog gauges
รันด้วยคำสั่ง:  streamlit run ohms_law_lab_interactive.py

ต้องติดตั้ง:  pip install streamlit matplotlib numpy pandas

Flow ของหน้านี้ (ตาม layout ที่วางแผนไว้):
  1) พื้นที่จำลอง: วงจร + หน้าปัดแอมมิเตอร์/โวลต์มิเตอร์แบบ analog (มี animation)
  2) แผงควบคุม: เลือกแบตเตอรี่ (จำลองการเปลี่ยนแบต) + ปุ่มวัดค่า/บันทึกค่า
  3) ตารางข้อมูลที่บันทึก (แก้ไข/ลบแถวได้)
  4) พล็อตกราฟ + เลือกรูปแบบ fit (Linear / Quadratic / Power / Exponential)

หมายเหตุฟอนต์ไทย: ถ้าตัวอักษรไทยเป็นกล่องสี่เหลี่ยม ให้เปลี่ยน THAI_FONT
เป็นฟอนต์ที่มีในเครื่อง เช่น "Noto Sans Thai" หรือ "TH Sarabun New"
"""

import time
import random

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm

# ----------------------------------------------------------------------
# ฟอนต์ไทย
# ----------------------------------------------------------------------
THAI_FONT = "Tahoma"
available_fonts = {f.name for f in fm.fontManager.ttflist}
plt.rcParams["font.family"] = THAI_FONT if THAI_FONT in available_fonts else "sans-serif"
plt.rcParams["axes.unicode_minus"] = False

WIRE_COLOR = "#5F5E5A"
NEEDLE_COLOR = "#C0392B"
FACE_COLOR = "#F7F8FC"

# แถบที่ 4 (tolerance) สุ่มได้ 3 แบบ: ทอง ±5%, เงิน ±10%, ไม่มีสี ±20%
TOLERANCE_OPTIONS = [
    ("ทอง", "#C9A227", 0.05),
    ("เงิน", "#B0B0B0", 0.10),
    ("ไม่มีสี", "#D9D5C9", 0.20),
]

BATTERY_OPTIONS = [1.5, 3.0, 4.5, 6.0, 9.0, 12.0]  # โวลต์ (จำลองการสลับก้อนแบต)

# ----------------------------------------------------------------------
# ตารางสีแถบตัวต้านทานมาตรฐาน (สี, hex) ตามรหัสเลข 0-9 และตัวคูณ 10^0..10^3
# ----------------------------------------------------------------------
BAND_COLOR_TABLE = {
    0: ("ดำ", "#1A1A1A"),
    1: ("น้ำตาล", "#6F4A2A"),
    2: ("แดง", "#C0392B"),
    3: ("ส้ม", "#D2691E"),
    4: ("เหลือง", "#D4AC0D"),
    5: ("เขียว", "#2E7D32"),
    6: ("น้ำเงิน", "#1F5FA8"),
    7: ("ม่วง", "#6C3483"),
    8: ("เทา", "#7F8C8D"),
    9: ("ขาว", "#E8E6E1"),
}

# ค่าฐาน E12 (สองหลักแรกของตัวต้านทาน) — คูณด้วย 10^ทศนิยม เพื่อสุ่มค่าจริง
E12_BASES = [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82]
DECADE_CHOICES = [1, 2]  # จำกัดช่วง 100Ω–8.2kΩ ให้เหมาะกับแบตเตอรี่ 1.5–12V

st.set_page_config(page_title="Ohm's Law Lab", layout="wide")


def randomize_resistor():
    """สุ่มตัวต้านทานปริศนาใหม่ พร้อมคำนวณแถบสีให้ตรงกับค่าที่สุ่มได้"""
    base = random.choice(E12_BASES)
    decade = random.choice(DECADE_CHOICES)
    nominal = base * (10 ** decade)  # ค่าที่ระบุจากแถบสี (โอห์ม)
    d1, d2 = base // 10, base % 10
    tol_name, tol_color, tol_pct = random.choice(TOLERANCE_OPTIONS)
    bands = [BAND_COLOR_TABLE[d1][1], BAND_COLOR_TABLE[d2][1], BAND_COLOR_TABLE[decade][1], tol_color]
    band_names = [BAND_COLOR_TABLE[d1][0], BAND_COLOR_TABLE[d2][0], BAND_COLOR_TABLE[decade][0], tol_name]
    st.session_state.nominal_R = nominal
    st.session_state.bands = bands
    st.session_state.band_names = band_names
    st.session_state.tolerance_pct = tol_pct
    # ค่าความต้านทานจริง คลาดเคลื่อนจากค่าที่พิมพ์ได้ไม่เกิน ±tolerance ของแถบที่ 4 ที่สุ่มได้
    st.session_state.R_true = nominal * (1 + random.uniform(-tol_pct, tol_pct))
    # สเกลเครื่องวัดต้องปรับตามค่า R ที่สุ่มได้ในรอบนี้เสมอ
    st.session_state.max_I_gauge = (max(BATTERY_OPTIONS) / nominal * 1000) * 1.3  # mA, เผื่อ 30%
    st.session_state.data = pd.DataFrame(columns=["V (โวลต์)", "I (mA)"])
    st.session_state.last_I = 0.0
    st.session_state.last_V = 0.0
    st.session_state.measured = False


# ----------------------------------------------------------------------
# state เริ่มต้น
# ----------------------------------------------------------------------
if "R_true" not in st.session_state:
    randomize_resistor()

MAX_V_GAUGE = max(BATTERY_OPTIONS) * 1.15
MAX_I_GAUGE = st.session_state.max_I_gauge  # ปรับตามค่าตัวต้านทานที่สุ่มได้ในรอบนี้


# ----------------------------------------------------------------------
# วาดวงจร (คงที่ ไม่ต้อง animate)
# ----------------------------------------------------------------------
def draw_circuit():
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    ax.set_xlim(0, 460)
    ax.set_ylim(320, 0)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    def wire(x1, y1, x2, y2, lw=2.0):
        ax.plot([x1, x2], [y1, y2], color=WIRE_COLOR, linewidth=lw, solid_capstyle="round")

    wire(80, 60, 320, 60)
    wire(80, 60, 80, 260)
    wire(320, 60, 320, 110)
    wire(320, 190, 320, 260)
    wire(320, 260, 220, 260)
    wire(180, 260, 80, 260)

    # แบตเตอรี่
    wire(62, 165, 98, 165, lw=2.0)
    wire(71, 185, 89, 185, lw=5.0)
    ax.text(105, 160, "+", ha="left", va="center", fontsize=11)
    ax.text(105, 190, "-", ha="left", va="center", fontsize=11)
    ax.text(10, 155, "แบตเตอรี่", ha="left", va="center", fontsize=11)
    ax.text(10, 173, "(เปลี่ยนได้)", ha="left", va="center", fontsize=9, color="#5B6478")

    # ตัวต้านทาน (สีแถบสุ่มตามค่าที่สุ่มได้ในรอบนี้)
    ax.add_patch(patches.FancyBboxPatch((305, 110), 30, 80, boxstyle="round,pad=0,rounding_size=4",
                                         linewidth=1, edgecolor=WIRE_COLOR, facecolor="#E8D9B0"))
    for y, color, name in zip([116, 130, 144, 172], st.session_state.bands, st.session_state.band_names):
        if name == "ไม่มีสี":
            continue
        ax.add_patch(patches.Rectangle((305, y), 30, 7, facecolor=color, edgecolor="none"))
    ax.text(345, 110, "ตัวต้านทาน\nปริศนา", ha="left", va="center", fontsize=9)

    # แอมมิเตอร์
    ax.add_patch(patches.Circle((200, 260), 18, facecolor="white", edgecolor=WIRE_COLOR, linewidth=1.5))
    ax.text(200, 260, "A", ha="center", va="center", fontsize=11, fontweight="bold")

    # โวลต์มิเตอร์ (ขนาน)
    ax.plot([320, 385, 385, 320], [110, 110, 190, 190], color=WIRE_COLOR, linewidth=1.2, linestyle=(0, (4, 4)))
    ax.add_patch(patches.Circle((385, 150), 16, facecolor="white", edgecolor=WIRE_COLOR, linewidth=1.5))
    ax.text(385, 150, "V", ha="center", va="center", fontsize=11, fontweight="bold")

    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------
# วาดหน้าปัด analog gauge หนึ่งอัน
# ----------------------------------------------------------------------
def draw_gauge_face(ax, value, max_value, label, unit, n_ticks=6):
    """วาดหน้าปัดครึ่งวงกลม เข็มชี้ตามค่า value (0..max_value)"""
    ax.clear()
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.3, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")

    # หน้าปัด
    ax.add_patch(patches.Wedge((0, 0), 1.0, 0, 180, facecolor=FACE_COLOR, edgecolor=WIRE_COLOR, linewidth=1.2))

    # ขีดสเกล
    for i in range(n_ticks + 1):
        frac = i / n_ticks
        theta = np.radians(180 * (1 - frac))
        x1, y1 = 0.86 * np.cos(theta), 0.86 * np.sin(theta)
        x2, y2 = 1.0 * np.cos(theta), 1.0 * np.sin(theta)
        ax.plot([x1, x2], [y1, y2], color=WIRE_COLOR, linewidth=1.2)
        lx, ly = 0.72 * np.cos(theta), 0.72 * np.sin(theta)
        ax.text(lx, ly, f"{max_value * frac:.1f}", ha="center", va="center", fontsize=7)

    # เข็ม
    frac = 0 if max_value == 0 else min(max(value / max_value, 0), 1)
    theta = np.radians(180 * (1 - frac))
    nx, ny = 0.82 * np.cos(theta), 0.82 * np.sin(theta)
    ax.plot([0, nx], [0, ny], color=NEEDLE_COLOR, linewidth=2.5, solid_capstyle="round")
    ax.add_patch(patches.Circle((0, 0), 0.05, facecolor=NEEDLE_COLOR, edgecolor="none"))

    ax.text(0, -0.22, f"{value:.2f} {unit}", ha="center", va="center", fontsize=13, fontweight="bold")
    ax.text(0, 1.12, label, ha="center", va="center", fontsize=11)


def animate_gauges(placeholder, old_I, new_I, old_V, new_V, frames=14):
    fig, (axA, axV) = plt.subplots(1, 2, figsize=(6, 3.4))
    fig.patch.set_facecolor("white")
    for f in range(1, frames + 1):
        t = f / frames
        eased = 1 - (1 - t) ** 2  # ease-out
        cur_I = old_I + (new_I - old_I) * eased
        cur_V = old_V + (new_V - old_V) * eased
        draw_gauge_face(axA, cur_I, MAX_I_GAUGE, "แอมมิเตอร์ (I)", "mA")
        draw_gauge_face(axV, cur_V, MAX_V_GAUGE, "โวลต์มิเตอร์ (V)", "V")
        fig.tight_layout()
        placeholder.pyplot(fig)
        time.sleep(0.02)
    plt.close(fig)


def static_gauges(placeholder, I_val, V_val):
    fig, (axA, axV) = plt.subplots(1, 2, figsize=(6, 3.4))
    fig.patch.set_facecolor("white")
    draw_gauge_face(axA, I_val, MAX_I_GAUGE, "แอมมิเตอร์ (I)", "mA")
    draw_gauge_face(axV, V_val, MAX_V_GAUGE, "โวลต์มิเตอร์ (V)", "V")
    fig.tight_layout()
    placeholder.pyplot(fig)
    plt.close(fig)


# ----------------------------------------------------------------------
# ฟิสิกส์: จำลองการวัดค่า (มี noise เล็กน้อยให้สมจริง)
# ----------------------------------------------------------------------
def measure(battery_voltage, R_true, r_internal=8.0):
    V_measured_ideal = battery_voltage * (R_true / (R_true + r_internal))
    V_measured = V_measured_ideal * (1 + random.uniform(-0.01, 0.01))
    I_measured = (V_measured / R_true) * 1000 * (1 + random.uniform(-0.015, 0.015))  # mA
    return round(V_measured, 3), round(I_measured, 3)


# ----------------------------------------------------------------------
# fit ฟังก์ชันต่างๆ (ไม่พึ่ง scipy — ใช้ np.polyfit บนข้อมูลที่ทำ log แล้ว)
# ----------------------------------------------------------------------
def r_squared(y, y_pred):
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot != 0 else 0.0


def fit_curve(x, y, kind):
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    if kind == "Linear":
        m, c = np.polyfit(x, y, 1)
        y_pred = m * x + c
        eq = f"y = {m:.4f}x + {c:.4f}"
        return x, y_pred_line(x, m, c), eq, r_squared(y, y_pred)
    if kind == "Quadratic":
        a, b, c = np.polyfit(x, y, 2)
        y_pred = a * x**2 + b * x + c
        xs = np.linspace(x.min(), x.max(), 100)
        ys = a * xs**2 + b * xs + c
        eq = f"y = {a:.4f}x² + {b:.4f}x + {c:.4f}"
        return xs, ys, eq, r_squared(y, y_pred)
    if kind == "Power":
        mask = (x > 0) & (y > 0)
        b, loga = np.polyfit(np.log(x[mask]), np.log(y[mask]), 1)
        a = np.exp(loga)
        y_pred = a * x**b
        xs = np.linspace(max(x.min(), 1e-6), x.max(), 100)
        ys = a * xs**b
        eq = f"y = {a:.4f}·x^{b:.4f}"
        return xs, ys, eq, r_squared(y, y_pred)
    if kind == "Exponential":
        mask = y > 0
        b, loga = np.polyfit(x[mask], np.log(y[mask]), 1)
        a = np.exp(loga)
        y_pred = a * np.exp(b * x)
        xs = np.linspace(x.min(), x.max(), 100)
        ys = a * np.exp(b * xs)
        eq = f"y = {a:.4f}·e^({b:.4f}x)"
        return xs, ys, eq, r_squared(y, y_pred)
    return x, y, "", None


def y_pred_line(x, m, c):
    return m * x + c


# ========================================================================
# UI
# ========================================================================
st.title("แลปกฎของโอห์ม — วงจรทดลองแบบ interactive")
st.caption("เปลี่ยนแบตเตอรี่ → วัดค่า I และ V → บันทึกลงตาราง → พล็อตกราฟหาความต้านทานปริศนา")

col_canvas, col_controls = st.columns([1.3, 1])

with col_canvas:
    st.subheader("พื้นที่จำลอง")
    st.pyplot(draw_circuit())
    gauge_placeholder = st.empty()
    if not st.session_state.measured:
        static_gauges(gauge_placeholder, 0.0, 0.0)
    else:
        static_gauges(gauge_placeholder, st.session_state.last_I, st.session_state.last_V)

with col_controls:
    st.subheader("แผงควบคุม")
    battery_v = st.select_slider(
        "เลือกแบตเตอรี่ (โวลต์)", options=BATTERY_OPTIONS, value=BATTERY_OPTIONS[2]
    )
    teacher_mode = st.checkbox("แสดงค่าจริง (สำหรับครู)")
    if teacher_mode:
        names = " - ".join(st.session_state.band_names)
        st.info(
            f"แถบสี: {names}\n\n"
            f"ค่าที่พิมพ์ตามแถบสี: {st.session_state.nominal_R:.0f} Ω "
            f"±{st.session_state.tolerance_pct*100:.0f}%\n\n"
            f"(ค่าความต้านทานจริงจะแสดงในส่วนตรวจคำตอบท้ายหน้า)"
        )

    if st.button("🔄 สุ่มตัวต้านทานใหม่", use_container_width=True):
        randomize_resistor()
        st.rerun()

    if st.button("▶ วัดค่า", use_container_width=True):
        new_V, new_I = measure(battery_v, st.session_state.R_true)
        animate_gauges(gauge_placeholder, st.session_state.last_I, new_I, st.session_state.last_V, new_V)
        st.session_state.last_I = new_I
        st.session_state.last_V = new_V
        st.session_state.measured = True
        st.rerun()

    if st.session_state.measured:
        st.metric("ความต่างศักย์ (V)", f"{st.session_state.last_V:.2f} V")
        st.metric("กระแสไฟฟ้า (I)", f"{st.session_state.last_I:.2f} mA")

    if st.button("＋ บันทึกค่า", use_container_width=True, disabled=not st.session_state.measured):
        new_row = pd.DataFrame(
            [{"V (โวลต์)": st.session_state.last_V, "I (mA)": st.session_state.last_I}]
        )
        st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
        st.success("บันทึกค่าแล้ว")

st.divider()

# ----------------------------------------------------------------------
# ตารางข้อมูล
# ----------------------------------------------------------------------
st.subheader("ตารางข้อมูลที่บันทึก")
edited = st.data_editor(
    st.session_state.data, num_rows="dynamic", use_container_width=True, key="data_editor"
)
st.session_state.data = edited

st.divider()

# ----------------------------------------------------------------------
# พล็อตกราฟ + fit
# ----------------------------------------------------------------------
st.subheader("พล็อตกราฟ + Fit เส้นโค้ง")

df = st.session_state.data.dropna()
if len(df) < 2:
    st.info("บันทึกข้อมูลอย่างน้อย 2 จุดเพื่อพล็อตกราฟ")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        x_col = st.selectbox("แกน X", df.columns, index=0)
    with c2:
        y_col = st.selectbox("แกน Y", df.columns, index=1)
    with c3:
        fit_kind = st.selectbox("รูปแบบ Fit", ["ไม่ fit", "Linear", "Quadratic", "Power", "Exponential"])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(df[x_col], df[y_col], color="#3B4FD6", zorder=3, label="ข้อมูลที่วัดได้")
    eq_text, r2_text = "", ""

    if fit_kind != "ไม่ fit":
        try:
            xs, ys, eq, r2 = fit_curve(df[x_col].values, df[y_col].values, fit_kind)
            ax.plot(xs, ys, color="#D85A30", linewidth=2, label="เส้น fit", zorder=2)
            eq_text, r2_text = eq, f"R² = {r2:.4f}"
        except Exception as e:
            st.warning(f"ไม่สามารถ fit ได้กับข้อมูลนี้: {e}")

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.legend()
    ax.grid(alpha=0.25)
    st.pyplot(fig)

    if eq_text:
        st.markdown(f"**สมการ fit:** `{eq_text}`  |  **{r2_text}**")
        if fit_kind == "Linear" and "I" in x_col and "V" in y_col:
            slope = float(eq_text.split("x")[0].replace("y = ", ""))
            st.caption(f"หมายเหตุ: ความชัน ≈ ความต้านทาน R ≈ {slope*1000:.1f} Ω (จาก V = IR, I หน่วย mA)")

st.divider()

# ----------------------------------------------------------------------
# ตรวจคำตอบ + วิเคราะห์ % ความคลาดเคลื่อน (เปิดหลังคำนวณ R จากกราฟด้วยตนเอง)
# ----------------------------------------------------------------------
st.subheader("ตรวจคำตอบ: วิเคราะห์ % ความคลาดเคลื่อน")
with st.expander("เปิดเมื่อคำนวณค่า R จากกราฟด้วยตนเองแล้ว"):
    student_R = st.number_input("ค่า R ที่คำนวณได้จากกราฟ (Ω)", min_value=0.0, step=1.0, value=0.0)
    if student_R > 0:
        st.write(f"ค่าความต้านทานจริงของตัวต้านทานปริศนา: **{st.session_state.R_true:.1f} Ω**")
        pct_error = abs(student_R - st.session_state.R_true) / st.session_state.R_true * 100
        st.metric("% ความคลาดเคลื่อน", f"{pct_error:.2f}%")
        tol_pct = st.session_state.tolerance_pct * 100
        if pct_error <= tol_pct:
            st.success(f"อยู่ในช่วงความคลาดเคลื่อนที่ยอมรับได้ของตัวต้านทาน (±{tol_pct:.0f}%) ✅")
        else:
            st.warning(f"เกินช่วงความคลาดเคลื่อนที่ยอมรับได้ (±{tol_pct:.0f}%) ลองตรวจสอบข้อมูลหรือวิธี fit อีกครั้ง")

