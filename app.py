import streamlit as st
import openai
import os
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(
    page_title="NovelRefiner - 小说去AI化与逻辑质检",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 自定义CSS (增加文学质感) ---
st.markdown("""
<style>
    .main {
        background-color: #f9f9f9;
    }
    .stTextArea textarea {
        font-family: 'Georgia', serif; /* 衬线体更适合阅读小说 */
        font-size: 16px;
        line-height: 1.6;
        color: #333;
    }
    .report-box {
        background-color: #fff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .rewrite-box {
        background-color: #fff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        font-family: 'Georgia', serif;
    }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("🛠️ 工作台设置")
    
    # API 设置
    api_key = st.text_input("输入 API Key (OpenAI/DeepSeek)", type="password", help="推荐使用兼容OpenAI格式的API")
    base_url = st.text_input("API Base URL (可选)", value="https://api.openai.com/v1", help="如果使用DeepSeek或国内中转，请修改此处")
    model_name = st.selectbox("选择模型", ["gpt-4o", "gpt-4-turbo", "deepseek-chat", "gpt-3.5-turbo"], index=0)
    
    st.divider()
    
    # 润色参数
    st.subheader("🎨 润色风格")
    style_option = st.selectbox(
        "文风选择",
        ["海明威式 (简洁有力)", "马尔克斯式 (魔幻细腻)", "金庸式 (侠气流畅)", "纯正网文 (爽点密集)", "写实主义 (沉稳扎实)"]
    )
    humanize_level = st.slider("去AI化强度", 1, 5, 3, help="等级越高，对原句结构的打散重组程度越大")
    
    st.divider()
    st.markdown("Designed by **AI Novelist Assistant**")

# --- 核心函数：调用LLM ---
def call_llm(system_prompt, user_prompt, key, url, model):
    if not key:
        st.error("请先在侧边栏输入 API Key 🔑")
        return None
    
    client = openai.OpenAI(api_key=key, base_url=url)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"API 调用出错: {e}")
        return None

# --- Prompt 设计 (核心资产) ---
PROMPTS = {
    "logic_check": """
    你是一位经验极其丰富、眼光毒辣的小说主编。请对用户提供的文本进行严苛的“逻辑体检”。
    
    请重点检查以下问题：
    1. **事实/常识错误**：例如古代出现手机，或者不符合物理常识的动作。
    2. **前后矛盾**：前文说A死了，后文A又出现了；或者时间线混乱。
    3. **人设崩塌**：角色的言行与之前的性格设定严重不符。
    4. **动机缺失**：角色的行为缺乏合理的心理或环境动因，显得是为了推剧情而强行降智。
    
    请输出一份简洁的【体检报告】，列出具体段落和问题所在，不要废话。
    格式：
    - [❌ 严重逻辑错误]: ...
    - [⚠️ 疑似不合理]: ...
    - [💡 修改建议]: ...
    """,

    "de_ai": lambda style, level: f"""
    你是一位顶级小说家，擅长将平庸、僵硬的文字点石成金。你需要对用户提供的AI生成文本进行“彻底重写”。
    
    当前目标风格：【{style}】
    重写强度（1-5）：{level} (5代表可以大幅改动句式，只保留核心剧情)
    
    **必须遵守的“去AI化”原则**：
    1. **禁止AI惯用语**：严禁出现“不得不说”、“作为...”、“这一刻”、“心中涌起一股暖流”、“某种意义上”、“仿佛”等AI高频词。
    2. **Show, Don't Tell**：不要说“他很生气”，要描写他“眼角的肌肉抽搐了一下，手中的茶杯捏得咯吱作响”。
    3. **感官细节**：加入气味、触感、光影的描写，增加颗粒感。
    4. **断句节奏**：打破AI那种匀速的长难句，使用长短句结合，营造呼吸感。
    5. **拒绝说教**：删除所有试图总结人生道理的升华段落。
    
    请直接输出重写后的正文，不需要任何前言后语。
    """
}

# --- 主界面 ---
st.title("🖊️ 小说去AI化 & 逻辑手术台")
st.markdown("把AI写的“行活儿”变成真正的**文学作品**。")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📄 原稿录入")
    source_text = st.text_area("在此粘贴AI生成的章节内容...", height=600, placeholder="例：他感到一种前所未有的恐惧，这恐惧如同潮水般将他淹没...")
    
    # 两个主要按钮
    btn_col_1, btn_col_2 = st.columns(2)
    with btn_col_1:
        do_logic_check = st.button("🔍 逻辑体检", type="secondary", use_container_width=True)
    with btn_col_2:
        do_rewrite = st.button("✨ 去AI化重写", type="primary", use_container_width=True)

with col2:
    # 逻辑检查结果区域
    if do_logic_check and source_text:
        with st.spinner("正在像拿着显微镜一样检查逻辑漏洞..."):
            report = call_llm(PROMPTS["logic_check"], source_text, api_key, base_url, model_name)
            if report:
                st.subheader("🔍 逻辑体检报告")
                st.markdown(f'<div class="report-box">{report}</div>', unsafe_allow_html=True)
    
    # 重写结果区域
    if do_rewrite and source_text:
        with st.spinner(f"正在以【{style_option}】风格重塑文字..."):
            system_prompt = PROMPTS["de_ai"](style_option, humanize_level)
            new_text = call_llm(system_prompt, source_text, api_key, base_url, model_name)
            if new_text:
                st.subheader("✨ 重写预览")
                st.markdown(f'<div class="rewrite-box">{new_text}</div>', unsafe_allow_html=True)
                st.download_button("下载修订稿", new_text, file_name=f"revised_chapter_{datetime.now().strftime('%H%M')}.txt")

# --- 底部说明 ---
if not source_text:
    with col2:
        st.info("👈 请在左侧输入文本以开始工作。")
        st.markdown("""
        ### 为什么AI写的小说一眼假？
        1. **过度解释**：AI总喜欢在动作后解释角色的心理，生怕读者看不懂。
        2. **滥用形容词**：喜欢堆砌华丽但无效的形容词。
        3. **逻辑平滑但无聊**：为了安全，AI往往会避免极端的冲突，导致剧情像白开水。
        
        **本工具将帮你打破这些桎梏。**
        """)