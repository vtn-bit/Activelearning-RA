import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
import time
from docx import Document
import datetime

# 🔧 ตั้งค่าธีมสีฟ้าเขียวขาว
def setup_custom_theme():
    st.markdown("""
    <style>
    /* ธีมสีฟ้าเขียวขาว */
    :root {
        --primary-color: #1E88E5;    /* ฟ้าเข้ม */
        --secondary-color: #4DB6AC;  /* เขียวฟ้า */
        --accent-color: #26C6DA;     /* ฟ้าอ่อน */
        --background-color: #F5F7FA; /* เทาอ่อน */
        --text-color: #263238;       /* เทาเข้ม */
        --card-color: #FFFFFF;       /* ขาว */
    }
    
    .main-header {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .chat-user {
        background-color: var(--primary-color) !important;
        color: white !important;
        border-radius: 15px 15px 0px 15px !important;
        padding: 12px 16px !important; 
        margin: 4px 0 !important;
        line-height: 1.5 !important;
    }
    
    .chat-assistant {
         background-color: var(--secondary-color) !important;
        color: white !important;
        border-radius: 15px 15px 15px 0px !important;
        padding: 12px 16px !important;  
        margin: 4px 0 !important;
        line-height: 1.5 !important;
    }
    
    .sidebar-content {
        background-color: var(--card-color);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid var(--accent-color);
    }
    
    .stat-card {
        background: linear-gradient(135deg, var(--card-color), #f0f4f8);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
    }
    
    .stButton button {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    .stButton button:hover {
        background: linear-gradient(135deg, var(--secondary-color), var(--primary-color));
        color: white;
    }
    
    .footer {
        text-align: center;
        padding: 1rem;
        color: var(--text-color);
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

# เรียกตั้งค่าธีม
setup_custom_theme()

# 🔑 ตั้งค่า API KEY
genai.configure(api_key="AIzaSyD-Ga-fru_mbx74ObfjxRuQsK-n3Zd3sDQ")

generation_config = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
    "response_mime_type": "text/plain",
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# ✅ ฟังก์ชันเลือกโมเดลเวอร์ชัน 2.0 (ปิดการแสดงผล)
def get_available_model():
    """ดึงรายชื่อโมเดลเวอร์ชัน 2.0 ที่ใช้งานได้"""
    try:
        available_models = genai.list_models()
        working_models = []
        
        for model in available_models:
            if "generateContent" in model.supported_generation_methods:
                working_models.append(model.name)
        
        # ✅ ลำดับความชอบของโมเดลเวอร์ชัน 2.0 (หลีกเลี่ยง 2.5)
        preferred_models = [
            # Gemini 1.5 Series
            "models/gemini-1.5-flash-001",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro-001", 
            "models/gemini-1.5-pro",
            
            # Gemini 1.0 Series
            "models/gemini-1.0-pro-001",
            "models/gemini-1.0-pro",
            "models/gemini-pro",
            
            # Fallback models
            "models/gemini-pro-vision"
        ]
        
        # ✅ กรองเอาเฉพาะโมเดลที่ไม่มี "2.5" ในชื่อ
        filtered_models = [model for model in preferred_models if "2.5" not in model]
        
        # ✅ หาโมเดลแรกที่ทำงานได้
        for model_name in filtered_models:
            if model_name in working_models:
                return model_name
        
        # ✅ ถ้าไม่เจอให้ใช้โมเดลแรกที่ทำงานได้และไม่มี 2.5
        safe_models = [model for model in working_models if "2.5" not in model]
        if safe_models:
            return safe_models[0]
        else:
            return working_models[0] if working_models else None
        
    except Exception as e:
        # Fallback to stable model
        return "models/gemini-1.0-pro"

# ✅ รับโมเดลที่ใช้งานได้
chosen_model = get_available_model()

if not chosen_model:
    st.error("❌ ไม่พบโมเดลที่ใช้งานได้")
    st.stop()

# ✅ ฟังก์ชันล้างประวัติ
def clear_history():
    st.session_state["messages"] = [
        {"role": "model", "content": "สวัสดีค่ะ ดิฉันคือครูผู้สอนวิชา Instructional Science and Classroom Management วันนี้สนใจอยากเรียนรู้เรื่องใดคะ"}
    ]
    if "chat_history" in st.session_state:
        st.session_state["chat_history"] = []
    st.rerun()

# ✅ ฟังก์ชันโหลดและประมวลผลเอกสาร
@st.cache_data(ttl=3600)
def load_document(file_path):
    """โหลดและประมวลผลเอกสาร docx"""
    try:
        doc = Document(file_path)
        file_content = ""
        for para in doc.paragraphs:
            if para.text.strip():
                file_content += para.text + "\n"
        
        paragraphs = [p.strip() for p in file_content.split('\n') if p.strip() and len(p.strip()) > 10]
        return file_content, paragraphs
    except Exception as e:
        return "", []

# ✅ ฟังก์ชันค้นหาข้อมูลที่เกี่ยวข้อง
def find_relevant_content(question, paragraphs, top_n=3):
    """ค้นหาข้อมูลที่เกี่ยวข้องกับคำถาม"""
    if not paragraphs or len(paragraphs) <= top_n:
        return "\n".join(paragraphs) if paragraphs else ""
    
    try:
        question_lower = question.lower()
        relevant_paragraphs = []
        
        keyword_groups = {
            'active_learning': ['active learning', 'การเรียนเชิงรุก', 'เรียนเชิงรุก'],
            'learning_styles': ['learning styles', 'รูปแบบการเรียนรู้', 'visual', 'auditory', 'kinesthetic'],
            'classroom_management': ['classroom management', 'การจัดการชั้นเรียน'],
            'instructional_science': ['instructional science', 'วิทยาศาสตร์การเรียนการสอน'],
            'teaching_methods': ['การสอน', 'เทคนิคการสอน', 'วิธีการสอน']
        }
        
        paragraph_scores = []
        for i, paragraph in enumerate(paragraphs):
            paragraph_lower = paragraph.lower()
            score = 0
            
            question_words = [word for word in question_lower.split() if len(word) > 2]
            for word in question_words:
                if word in paragraph_lower:
                    score += 2
            
            for group_keywords in keyword_groups.values():
                for keyword in group_keywords:
                    if keyword in paragraph_lower:
                        score += 3
                        break
            
            if score > 0:
                paragraph_scores.append((score, i, paragraph))
        
        paragraph_scores.sort(reverse=True)
        top_paragraphs = [item[2] for item in paragraph_scores[:top_n]]
        
        if top_paragraphs:
            return "\n".join(top_paragraphs)
        else:
            long_paragraphs = [p for p in paragraphs if len(p) > 50]
            return "\n".join(long_paragraphs[:top_n]) if long_paragraphs else "\n".join(paragraphs[:top_n])
            
    except Exception as e:
        return "\n".join(paragraphs[:top_n]) if paragraphs else ""

# ✅ ฟังก์ชันสร้างคำตอบ
def generate_response(prompt, file_content, paragraphs):
    """สร้างคำตอบโดยใช้ Gemini"""
    
    if prompt.lower().strip() in ['clear', 'ล้าง', 'reset', 'ใหม่']:
        clear_history()
        return "ล้างประวัติการสนทนาเรียบร้อยแล้วค่ะ ✅"
    
    relevant_content = find_relevant_content(prompt, paragraphs)
    
    context_prompt = f"""
    บทบาท: คุณเป็นผู้ช่วยอาจารย์ผู้เชี่ยวชาญด้าน Instructional Science และ Classroom Management

    ข้อมูลจากเอกสารประกอบการเรียน:
    {relevant_content}

    คำถามจากผู้ใช้: {prompt}

    คำแนะนำในการตอบ:
    1. ตอบโดยอ้างอิงจากข้อมูลในเอกสารเป็นหลัก
    2. ใช้ภาษาไทยที่ชัดเจน เข้าใจง่าย
    3. ให้คำตอบที่เป็นประโยชน์และนำไปปฏิบัติได้
    4. หากเป็นเทคนิคการสอน ให้ยกตัวอย่างประกอบ

    โปรดตอบคำถามอย่างเป็นกันเองแต่คงความถูกต้องทางวิชาการ
    """

    try:
        model = genai.GenerativeModel(
            model_name=chosen_model,
            generation_config=generation_config,
            safety_settings=SAFETY_SETTINGS,
        )
        
        response = model.generate_content(context_prompt)
        
        if response and response.text:
            reply_text = response.text.strip()
            if len(reply_text) < 10:
                reply_text = "ข้อมูลในเอกสารอาจไม่เพียงพอสำหรับคำถามนี้ โปรดลองถามคำถามในรูปแบบอื่นค่ะ"
        else:
            reply_text = "ขออภัยค่ะ ไม่สามารถสร้างคำตอบได้ในขณะนี้"
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            reply_text = "ขออภัยค่ะ โควตาการใช้งานหมดชั่วคราว โปรดลองใหม่ใน 1-2 นาทีค่ะ"
        elif "404" in error_msg:
            reply_text = "ขออภัยค่ะ เกิดข้อผิดพลาดในการเชื่อมต่อ โปรดรีเฟรชหน้าเว็บ"
        else:
            reply_text = "ขออภัยค่ะ เกิดข้อผิดพลาดในการประมวลผล"

    return reply_text

# ✅ ฟังก์ชันบันทึกประวัติการสนทนา
def log_interaction(question, answer):
    """บันทึกประวัติการสนทนา"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    st.session_state["chat_history"].append({
        "timestamp": timestamp,
        "question": question,
        "answer": answer[:500]
    })

# ✅ ตั้งค่า Streamlit UI
st.markdown('<div class="main-header"><h1>👩‍🏫 วิชา Instructional Science & Classroom Management</h1><p>แชทบอทอัจฉริยะสำหรับการเรียนการสอน</p></div>', unsafe_allow_html=True)

# ✅ โหลดเอกสาร
file_path = r"dataset3.docx"
file_content, paragraphs = load_document(file_path)

# ✅ ตั้งค่า messages เริ่มต้น
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "model",
            "content": "สวัสดีค่ะ! ดิฉันคือผู้ช่วยอาจารย์ด้าน Instructional Science และ Classroom Management มีอะไรให้ดิฉันช่วยเหลือเกี่ยวกับการเรียนการสอนไหมคะ?"
        }
    ]

# ✅ Sidebar - ควบคุมระบบ
with st.sidebar:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    
    st.markdown("### 🎛️ ควบคุมระบบ")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 ล้างประวัติ", use_container_width=True):
            clear_history()
    with col2:
        if st.button("🔄 รีเฟรช", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # ✅ แสดงสถิติในการ์ดสวยงาม
    st.markdown("### 📊 สถิติระบบ")
    
    st.markdown('<div class="stat-card">', unsafe_allow_html=True)
    if file_content:
        st.metric("📄 จำนวนย่อหน้า", len(paragraphs))
        st.metric("🔤 จำนวนตัวอักษร", f"{len(file_content):,}")
    else:
        st.warning("ไม่พบไฟล์เอกสาร")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="stat-card">', unsafe_allow_html=True)
    if "chat_history" in st.session_state:
        st.metric("💬 การสนทนา", len(st.session_state["chat_history"]))
    else:
        st.metric("💬 การสนทนา", 0)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ✅ ข้อมูลโมเดล
    st.markdown("### 🤖 ข้อมูลโมเดล")
    st.markdown('<div class="stat-card">', unsafe_allow_html=True)
    st.success(f"**โมเดล:** {chosen_model.split('/')[-1]}")
    
    model_type = "🚀 Flash" if "flash" in chosen_model.lower() else "💎 Pro"
    st.info(f"**ประเภท:** {model_type}")
    
    st.success("**สถานะ:** 🟢 ใช้งานได้")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ✅ คำแนะนำการใช้งาน
    st.markdown("### 💡 คำแนะนำ")
    st.markdown("""
    - 🎯 **Active Learning** - เทคนิคการเรียนเชิงรุก
    - 🎨 **Learning Styles** - รูปแบบการเรียนรู้  
    - 🏫 **Classroom Management** - การจัดการชั้นเรียน
    - 👩‍🏫 **Teaching Methods** - วิธีการสอน
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ✅ แสดงประวัติสนทนาแบบสวยงาม
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="👩‍🏫"):
            st.markdown(f'<div class="chat-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

# ✅ ส่วนหลัก chatbot
st.markdown("---")
if prompt := st.chat_input("💬 พิมพ์คำถามเกี่ยวกับการเรียนการสอน..."):
    if prompt.strip():
        # เพิ่มคำถามผู้ใช้
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(f'<div class="chat-user">{prompt}</div>', unsafe_allow_html=True)
        
        # สร้างและแสดงคำตอบ
        with st.spinner("🔍 กำลังค้นหาข้อมูลและสร้างคำตอบ..."):
            response = generate_response(prompt, file_content, paragraphs)
            
        st.session_state["messages"].append({"role": "model", "content": response})
        with st.chat_message("assistant", avatar="👩‍🏫"):
            st.markdown(f'<div class="chat-assistant">{response}</div>', unsafe_allow_html=True)
        
        # บันทึกประวัติ
        log_interaction(prompt, response)

# ✅ Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <p>🤖 แชทบอทสำหรับวิชา Instructional Science and Classroom Management</p>
    <p>Powered by Google Gemini AI | Theme: Blue-Green-White</p>
</div>
""", unsafe_allow_html=True)