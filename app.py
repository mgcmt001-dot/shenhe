import streamlit as st
import json
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ============ 页面基本配置 ============

st.set_page_config(
    page_title="小说去AI化助手 (Gemini 调试版)",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ 小说去AI化与逻辑润色助手 (Gemini 调试版)")

# ============ 侧边栏设置 ============

with st.sidebar:
    st.header("🔑 鉴权设置")
    
    user_api_key = st.text_input(
        "Google API Key",
        type="password",
        placeholder="AIzaSy...",
        help="请确保 Key 有效且开通了 Generative Language API。"
    )

    st.header("⚙ 模型选择")

    # 预设一些常见的模型名称
    # 注意：有时候 API 需要完整的版本号，比如 gemini-1.5-flash-001
    model_options = [
        "gemini-1.5-flash", 
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-pro",
    ]
    
    # 允许用户手动输入（如果检测出的名字不在列表里）
    model_name_input = st.selectbox(
        "选择或输入模型名称",
        options=model_options,
        index=0,
    )

    st.divider()
    
    # === 新增：调试按钮 ===
    check_btn = st.button("🔍 检测可用模型 (Debug)", use_container_width=True)
    
    if check_btn:
        if not user_api_key:
            st.error("请先填入 API Key")
        else:
            try:
                genai.configure(api_key=user_api_key)
                # 列出所有模型
                models = list(genai.list_models())
                valid_names = [m.name.replace("models/", "") for m in models if "generateContent" in m.supported_generation_methods]
                
                if valid_names:
                    st.success("✅ 连接成功！你的 Key 支持以下模型：")
                    st.code("\n".join(valid_names))
                    st.info("请将上方列表中显示的名字（如 gemini-1.5-flash-001）复制，如果下拉框里没有，请手动打字输入。")
                else:
                    st.warning("连接成功，但这把 Key 似乎没有权限访问任何聊天模型。")
            except Exception as e:
                st.error(f"❌ 连接失败：{e}")
                st.caption("如果你在国内，请确保开启了全局代理，或终端已配置 HTTP_PROXY。")

    st.markdown("---")
    
    temperature = st.slider("创造力", 0.0, 1.5, 0.7)
    style_choice = st.selectbox("目标文风", ["保持原文", "商业流行", "纯文学", "网文爽文"])
    do_humanize = st.checkbox("去AI化润色", True)
    do_logic = st.checkbox("逻辑检查", True)


# ============ 主区域 ============

col_input, col_tips = st.columns([3, 1])
with col_input:
    raw_text = st.text_area("📄 粘贴小说片段", height=300)
with col_tips:
    extra_info = st.text_area("🌍 补充设定", height=300)

run_button = st.button("🚀 开始润色与分析", type="primary", use_container_width=True)


# ============ 核心逻辑 ============

def process_text_gemini(api_key, text, extra, style, humanize, logic, temp, model_ver):
    genai.configure(api_key=api_key)

    system_instruction = "你是一名资深的文学编辑。请务必以 JSON 格式输出结果。"
    
    user_prompt = f"""
任务：小说润色与检查
1. 去AI化: {'是' if humanize else '否'}
2. 逻辑检查: {'是' if logic else '否'}
3. 风格: {style}

原文：
{text}
补充：
{extra}

输出格式 (JSON Only):
{{
  "edited_text": "...",
  "ai_issues": ["..."],
  "logic_issues": ["..."],
  "editor_comments": "..."
}}
"""
    # 尝试配置 JSON 模式
    generation_config = {
        "temperature": temp,
        "response_mime_type": "application/json",
    }
    
    # 宽松的安全设置
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    try:
        model = genai.GenerativeModel(
            model_name=model_ver,
            system_instruction=system_instruction,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        response = model.generate_content(user_prompt)
        return response.text
    except Exception as e:
        # 如果 JSON 模式报错（有些旧模型不支持），回退到普通模式
        if "response_mime_type" in str(e) or "mode" in str(e):
            st.warning("当前模型不支持 JSON 模式，正在尝试普通文本模式...")
            del generation_config["response_mime_type"]
            model = genai.GenerativeModel(
                model_name=model_ver,
                system_instruction=system_instruction,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            response = model.generate_content(user_prompt)
            return response.text
        else:
            raise e

if run_button:
    if not user_api_key or not raw_text.strip():
        st.warning("请填写信息")
        st.stop()

    with st.spinner("🤖 处理中..."):
        try:
            result_str = process_text_gemini(
                user_api_key, raw_text, extra_info, style_choice, 
                do_humanize, do_logic, temperature, model_name_input
            )
            
            # 尝试清洗 JSON（Gemini 有时会在首尾加 ```json）
            clean_str = result_str.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(clean_str)
            
            st.divider()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📝 结果")
                st.text_area("正文", data.get("edited_text", ""), height=600)
                st.download_button("💾 下载", data.get("edited_text", ""), "revised.txt")
            with c2:
                st.subheader("🔍 分析")
                st.write(data.get("ai_issues", []))
                st.write(data.get("logic_issues", []))
                st.info(data.get("editor_comments", ""))

        except Exception as e:
            st.error(f"出错: {e}")
