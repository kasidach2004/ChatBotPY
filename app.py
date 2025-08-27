import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
import docx
import PyPDF2
import time # เพิ่มการนำเข้าไลบรารี time
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ⚠️ Import ไฟล์ prompt.py
from prompt import PROMPT_CED

# 🔐 ตั้งค่า API Key จาก Streamlit Secrets
# The API key is securely retrieved from Streamlit's secrets management.
# You must set 'GEMINI_API_KEY' in your Streamlit Cloud secrets.
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("API Key not found. Please add 'GEMINI_API_KEY' to your Streamlit secrets.")
    st.stop()

genai.configure(api_key=api_key)

# ⚙️ การตั้งค่า Model
generation_config = {
    "temperature": 0.1,
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

# 🔁 ฟังก์ชันล้างแชท
def clear_history():
    """Clears the chat history and stores it in full_history."""
    st.session_state["full_history"] = st.session_state["messages"][:]
    st.session_state["messages"] = [
        {"role": "model", "content": "ท่านสนใจสอบถามข้อมูลเกี่ยวกับเนื้อหาเกี่ยวกับรายวิชา เช่น ความหมายของจิตวิทยาการศึกษา ความเป็นมาของจิตวิทยาการศึกษา ประโยชน์ของการศึกษาจิตวิทยา"}
    ]
    st.rerun()

# 🔄 ฟังก์ชันเรียกคืนประวัติ
def restore_history():
    """Restores the chat history from the full_history state."""
    if "full_history" in st.session_state:
        st.session_state["messages"] = st.session_state["full_history"][:]
    st.rerun()

#  ฟังก์ชันอ่านไฟล์ Word (.docx)
def read_docx(file_path):
    """Reads text from a .docx file."""
    doc = docx.Document(file_path)
    full_text = [para.text for para in doc.paragraphs]
    return '\n'.join(full_text)

# 📄 ฟังก์ชันอ่านไฟล์ PDF (.pdf)
def read_pdf(file_path):
    """Reads text from a .pdf file."""
    try:
        reader = PyPDF2.PdfReader(file_path)
        full_text = "".join(page.extract_text() or "" for page in reader.pages)
        return full_text
    except Exception as e:
        st.error(f"Could not read PDF file: {e}")
        return ""

@st.cache_data
def load_files():
    """Loads and caches data from specified files."""
    full_corpus = ""
    file_status = {
        "excel": {"path": "Psychology.xlsx", "loaded": False, "error": None},
        "word": {"path": "Education_Psychology_for_Teacher1.docx", "loaded": False, "error": None},
        "pdf": {"path": "Education_Psychology_for_Teacher2.pdf", "loaded": False, "error": None},
    }

    # อ่านไฟล์ Excel
    try:
        if os.path.exists(file_status["excel"]["path"]):
            df = pd.read_excel(file_status["excel"]["path"])
            full_corpus += df.to_string(index=False) + "\n\n"
            file_status["excel"]["loaded"] = True
        else:
            file_status["excel"]["error"] = "File not found."
    except Exception as e:
        file_status["excel"]["error"] = str(e)
    
    # อ่านไฟล์ Word
    try:
        if os.path.exists(file_status["word"]["path"]):
            full_corpus += read_docx(file_status["word"]["path"]) + "\n\n"
            file_status["word"]["loaded"] = True
        else:
            file_status["word"]["error"] = "File not found."
    except Exception as e:
        file_status["word"]["error"] = str(e)

    # อ่านไฟล์ PDF
    try:
        if os.path.exists(file_status["pdf"]["path"]):
            full_corpus += read_pdf(file_status["pdf"]["path"]) + "\n\n"
            file_status["pdf"]["loaded"] = True
        else:
            file_status["pdf"]["error"] = "File not found."
    except Exception as e:
        file_status["pdf"]["error"] = str(e)
    
    return full_corpus, file_status

# 🔧 Sidebar: ปุ่ม Clear และ Restore
with st.sidebar:
    st.header("ตัวเลือกแชทบอท")
    
    st.subheader("การจัดการแชท")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 ล้างประวัติ", use_container_width=True):
            clear_history()
    with col2:
        if st.button("↩️ เรียกคืนประวัติ", use_container_width=True):
            restore_history()

    # 📂 โหลดข้อมูลจากไฟล์
    full_corpus, file_status = load_files()

    # ฟังก์ชันแสดงสถานะการโหลดไฟล์ใน Sidebar
    def show_file_status():
        st.subheader("สถานะการโหลดไฟล์")
        for file_type, status in file_status.items():
            if status["loaded"]:
                st.success(f"✅ {file_type.capitalize()} file loaded successfully from: {status['path']}")
            else:
                st.error(f"❌ {file_type.capitalize()} file could not be loaded: {status['error']}")

    # เพิ่มปุ่มแสดงสถานะการโหลดไฟล์
    st.subheader("สถานะการโหลด")
    if st.button("📁 ดูสถานะการโหลดไฟล์", use_container_width=True):
        show_file_status()


# 🧾 ชื่อแอปบนหน้า
st.title("💬 ยินดีต้อนรับเข้าสู่ Chatbot รายวิชาจิตวิทยาสำหรับครู")

# 🔃 เริ่มต้น session state ถ้ายังไม่มี
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "model",
            "content": "ท่านสนใจสอบถามข้อมูลเกี่ยวกับเนื้อหาเกี่ยวกับรายวิชา เช่น ความหมายของจิตวิทยาการศึกษา ความเป็นมาของจิตวิทยาการศึกษา ประโยชน์ของการศึกษาจิตวิทยา",
        }
    ]
if "full_history" not in st.session_state:
    st.session_state["full_history"] = []

# 💬 แสดงข้อความสนทนาเดิม
for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).markdown(msg["content"])

# 💡 ถ้ามี prompt ใหม่เข้ามา
if prompt := st.chat_input():
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)
    
    if not full_corpus:
        st.chat_message("model").markdown("ขออภัยค่ะ ไม่พบไฟล์ข้อมูลใดๆ เลย ไม่สามารถให้คำตอบได้ในขณะนี้")
        st.session_state["messages"].append({"role": "model", "content": "ขออภัยค่ะ ไม่พบไฟล์ข้อมูลใดๆ เลย ไม่สามารถให้คำตอบได้ในขณะนี้"})
    else:
        # สร้างรายการข้อความที่จะส่งให้โมเดล โดยรวมบริบทจากเอกสาร
        messages_for_gemini = [
            {"role": "user", "parts": [
                {"text": PROMPT_CED},
                {"text": f"--- Documents ---\n{full_corpus}"}
            ]}
        ]
        # เพิ่มประวัติการสนทนาทั้งหมดจาก session_state
        for msg in st.session_state["messages"]:
            messages_for_gemini.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

        # 🔍 ส่งข้อมูลไปให้โมเดลประมวลผล
        with st.chat_message("model"):
            try:
                message_placeholder = st.empty()
                # แสดงการขยับของจุดสามจุด
                dots = ["", ".", "..", "..."]
                for i in range(5): # แสดงการโหลด 5 ครั้ง
                    message_placeholder.markdown(f"กำลังคิด... {dots[i % 4]}")
                    time.sleep(0.3)
                
                response = model.generate_content(messages_for_gemini, stream=True)
                
                # จำลองการพิมพ์ทีละตัวอักษร
                full_response = ""
                for chunk in response:
                    full_response += chunk.text
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
                st.session_state["messages"].append({"role": "model", "content": full_response})
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการเรียกใช้ API: {e}")
                st.session_state["messages"].append({"role": "model", "content": "ขออภัยค่ะ มีข้อผิดพลาดเกิดขึ้น ไม่สามารถให้คำตอบได้ในขณะนี้"})
                st.chat_message("model").write("ขออภัยค่ะ มีข้อผิดพลาดเกิดขึ้น ไม่สามารถให้คำตอบได้ในขณะนี้")
