import streamlit as st
import yt_dlp
from faster_whisper import WhisperModel
import google.generativeai as genai
import os
import re

# 1. CẤU HÌNH TRANG (Dòng đầu tiên)
st.set_page_config(page_title="AI Video Translator", page_icon="🎬", layout="wide")

# 2. CẤU HÌNH GEMINI AI (Lấy từ Secrets)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model_gemini = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
except:
    st.error("Chưa cấu hình API Key trong phần Secrets!")

# 3. CÁC HÀM HỖ TRỢ (Định nghĩa trước khi dùng)
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def translate_smart(text_ja):
    prompt = f"Dịch câu tiếng Nhật sau sang tiếng Việt giao tiếp tự nhiên: {text_ja}. Chỉ trả về nội dung dịch."
    try:
        response = model_gemini.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Lỗi Gemini: {e}")
        return "Lỗi dịch thuật"

def split_by_punctuation(text, start_time, end_time):
    sentences = re.split(r'([.?!])', text)
    temp_sentences = []
    for i in range(0, len(sentences)-1, 2):
        temp_sentences.append((sentences[i] + sentences[i+1]).strip())
    if len(sentences) % 2 != 0 and sentences[-1].strip():
        temp_sentences.append(sentences[-1].strip())
    if not temp_sentences: return []
    duration = end_time - start_time
    time_per_sentence = duration / len(temp_sentences)
    return [(start_time + i*time_per_sentence, start_time + (i+1)*time_per_sentence, s) for i, s in enumerate(temp_sentences)]

# 4. GIAO DIỆN CSS
st.markdown("""
    <style>
    .main-title { font-size: 40px; font-weight: 800; color: #FF4B4B; text-align: center; }
    .stVideo { border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    div.stButton > button:first-child { background-color: #FF4B4B; color: white; border-radius: 10px; width: 100%; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #0E1117; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 5. BỐ CỤC SIDEBAR
with st.sidebar:
    st.header("⚙️ Nhập Video")
    url = st.text_input("🔗 Link YouTube:", placeholder="Dán link tại đây...")
    model_size = st.selectbox("🧠 Model Whisper:", ["tiny", "base", "small"], index=1)
    delay = st.slider("⏱️ Độ trễ Sub (giây):", 0.0, 1.0, 0.4)
    st.warning("⚠️ Lưu ý: Model lớn có thể làm sập server Cloud (1GB RAM).")

# 6. GIAO DIỆN CHÍNH
st.markdown('<p class="main-title">🎬 AI VIDEO TRANSLATOR</p>', unsafe_allow_html=True)
col_l, col_mid, col_r = st.columns([1, 6, 1])

with col_mid:
    if st.button("🚀 BẮT ĐẦU DỊCH VIDEO"):
        if not url:
            st.error("Ngọc ơi, chưa dán link kìa!")
        else:
            with st.status("Đang thực hiện phép thuật...", expanded=True) as status:
                # BƯỚC 1: TẢI VIDEO (Nằm trong try-except)
                st.write("📥 Đang tải video...")
                if os.path.exists("video.mp4"): os.remove("video.mp4")
                
                ydl_opts = {
                    'format': 'best[ext=mp4]',
                    'outtmpl': 'video.mp4',
                    'quiet': True,
                    'nocheckcertificate': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                except Exception as e:
                    st.error(f"YouTube chặn rồi Ngọc ơi! 🛑 Lỗi: {e}")
                    st.stop()

                if not os.path.exists("video.mp4"):
                    st.error("Không tìm thấy file video sau khi tải!")
                    st.stop()

                # BƯỚC 2: WHISPER
                st.write("🧠 AI đang nghe tiếng Nhật...")
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segments, _ = model.transcribe("video.mp4", beam_size=5, language="ja", vad_filter=True)

                # BƯỚC 3: GEMINI
                st.write("🌐 Gemini đang dịch sang tiếng Việt...")
                with open("phude_vi.srt", "w", encoding="utf-8") as f:
                    idx = 1
                    for seg in segments:
                        text_vi = translate_smart(seg.text) 
                        parts = split_by_punctuation(text_vi, seg.start + delay, seg.end)
                        for p_s, p_e, p_t in parts:
                            f.write(f"{idx}\n{format_time(p_s)} --> {format_time(p_e)}\n{p_t}\n\n")
                            idx += 1

                # BƯỚC 4: GHÉP SUB
                st.write("🎬 Đang đóng gói video...")
                style = "Fontname=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2"
                os.system(f'ffmpeg -i video.mp4 -vf "subtitles=phude_vi.srt:force_style=\'{style}\'" result.mp4 -y -loglevel error')
                
                status.update(label="Xong rồi nè Ngọc!", state="complete")

            st.success("Đã hoàn thành!")
            st.video("result.mp4")
            with open("result.mp4", "rb") as file:
                st.download_button(label="💾 Tải video về máy", data=file, file_name="video_dich.mp4", mime="video/mp4")
