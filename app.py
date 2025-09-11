import os
import google.generativeai as genai
import streamlit as st
import docx
import time
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ⚠️ Import ไฟล์ prompt.py
from prompt import PROMPT_CED

# 🔐 ตั้งค่า API Key จาก Streamlit Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("API Key not found. Please add 'GEMINI_API_KEY' to your Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)

# ⚙️ การตั้งค่า Model
generation_config = {
    "temperature": 0.01,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
    "response_mime_type": "text/plain",
}

# 🔐 ตั้งค่าความปลอดภัยของเนื้อหา
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# 🔍 เลือกโมเดล Gemini
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    safety_settings=SAFETY_SETTINGS,
    generation_config=generation_config,
)

# ฟังก์ชันอ่านไฟล์ Word (.docx)
def read_docx(file_path):
    """Reads text from a .docx file."""
    doc = docx.Document(file_path)
    full_text = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    return '\n'.join(full_text)

@st.cache_data
def load_dataset():
    """Loads and caches data only from the .docx dataset."""
    file_path = "DatasetEPW.docx"
    if os.path.exists(file_path):
        try:
            text = read_docx(file_path)
            return text, True, None
        except Exception as e:
            return "", False, str(e)
    else:
        return "", False, "File not found."

# 🔧 Sidebar: ปุ่ม Clear และ Restore
def clear_history():
    st.session_state["full_history"] = st.session_state["messages"][:]
    st.session_state["messages"] = [
        {"role": "model", "content": "ท่านสนใจสอบถามข้อมูลเกี่ยวกับเนื้อหาของรายวิชา เช่น ความหมาย ความเป็นมา หรือประโยชน์ของจิตวิทยาสำหรับครู"}
    ]
    st.rerun()

def restore_history():
    if "full_history" in st.session_state:
        st.session_state["messages"] = st.session_state["full_history"][:]
    st.rerun()

with st.sidebar:
    st.header("ตัวเลือกแชทบอท")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 ล้างประวัติ", use_container_width=True):
            clear_history()
    with col2:
        if st.button("↩️ เรียกคืนประวัติ", use_container_width=True):
            restore_history()

    # โหลด dataset
    dataset_text, dataset_loaded, dataset_error = load_dataset()
    st.subheader("สถานะการโหลดไฟล์")
    if dataset_loaded:
        st.success("✅ Dataset (.docx) loaded successfully")
    else:
        st.error(f"❌ Could not load dataset: {dataset_error}")

# 🧾 ชื่อแอป
st.title("💬 ยินดีต้อนรับเข้าสู่ Chatbot รายวิชาจิตวิทยาสำหรับครู")

# เริ่มต้น session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "model", "content": "ท่านสนใจสอบถามข้อมูลเกี่ยวกับเนื้อหาของรายวิชา เช่น ความหมาย ความเป็นมา หรือประโยชน์ของจิตวิทยาสำหรับครู"}
    ]
if "full_history" not in st.session_state:
    st.session_state["full_history"] = []

# แสดงประวัติการสนทนา
for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).markdown(msg["content"])

# เมื่อผู้ใช้ถาม
if prompt := st.chat_input():
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    if not dataset_loaded:
        error_msg = "ขออภัยค่ะ ไม่พบ dataset ไม่สามารถให้คำตอบได้ในขณะนี้"
        st.chat_message("model").markdown(error_msg)
        st.session_state["messages"].append({"role": "model", "content": error_msg})
    else:
        # ใส่ PROMPT + Dataset + คำถาม ลงไปพร้อมกัน
        messages_for_gemini = [
            {"role": "user", "parts": [
                {"text": PROMPT_CED},
                {"text": f"--- Dataset ---\n{dataset_text}"},
                {"text": f"--- User Question ---\n{prompt}"}
            ]}
        ]

        # เพิ่มประวัติสนทนา
        for msg in st.session_state["messages"]:
            messages_for_gemini.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

        # ส่งให้โมเดล
        with st.chat_message("model"):
            try:
                message_placeholder = st.empty()
                dots = ["", ".", "..", "..."]
                for i in range(5):
                    message_placeholder.markdown(f"กำลังคิด... {dots[i % 4]}")
                    time.sleep(0.3)

                response = model.generate_content(messages_for_gemini, stream=True)

                full_response = ""
                for chunk in response:
                    full_response += chunk.text
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

                st.session_state["messages"].append({"role": "model", "content": full_response})
            except Exception as e:
                error_msg = f"ขออภัยค่ะ มีข้อผิดพลาด: {e}"
                st.error(error_msg)
                st.session_state["messages"].append({"role": "model", "content": error_msg})
