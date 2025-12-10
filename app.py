import streamlit as st
from openai import OpenAI
import json

# =============== 基础配置 ===============
st.set_page_config(
    page_title="DeepNovel 文本精修工坊",
    layout="wide",
    page_icon="🧐"
)

# =============== Session State 初始化 ===============
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "audit_report" not in st.session_state:
    st.session_state.audit_report = ""
if "revised_text" not in st.session_state:
    st.session_state.revised_text = ""
if "history_logs" not in st.session_state:
    st.session_state.history_logs = []  # 简单的历史记录

# =============== 侧边栏：API 设置 ===============
with st.sidebar:
    st.title("⚙️ 引擎设置")
    api_key = st.text_input("SiliconFlow API Key", type="password")
    if not api_key:
        st.warning("请输入 API Key 以启动引擎")
        st.stop()
    
    # 初始化客户端
    client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")
    
    st.markdown("---")
    st.info(
        "💡 **使用指南**：\n\n"
        "1. 将写好的章节粘贴到左侧。\n"
        "2. 选择【审核模式】。\n"
        "3. AI 会先出报告，再出修改稿。\n"
        "4. 满意后可直接下载修改稿。"
    )
    
    st.markdown("---")
    if st.button("🗑️ 清空所有内容"):
        st.session_state.input_text = ""
        st.session_state.audit_report = ""
        st.session_state.revised_text = ""
        st.rerun()

# =============== AI 调用函数 ===============
def ask_ai(system_role: str, user_prompt: str, temperature: float = 0.7, model: str = "deepseek-ai/DeepSeek-V3"):
    """
    专门针对审核优化的 AI 调用参数，
    temperature 稍微调低一点（0.7），保证逻辑严谨，不胡乱加戏。
    """
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=4096  # 保证能输出完整修改稿
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# =============== 主界面 ===============
st.title("🧐 DeepNovel · 文本精修工坊")
st.caption("资深主编视角 · 逻辑质检 · 去 AI 味 · 文笔润色")

# 布局：左边输入，右边输出
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📝 待审阅原稿")
    
    # 粘贴区域
    input_text = st.text_area(
        "请粘贴你的章节正文：",
        height=500,
        placeholder="在这里粘贴第 X 章的正文...",
        value=st.session_state.input_text
    )
    st.session_state.input_text = input_text
    
    # 辅助信息（可选）
    context_info = st.text_area(
        "背景备注（可选，帮助 AI 理解前因后果）：",
        height=100,
        placeholder="例如：主角刚刚重生，这章是他第一次见到反派...",
    )

    st.markdown("---")
    st.subheader("🔍 选择精修模式")
    
    audit_mode = st.radio(
        "你想怎么修？",
        [
            "1. 毒舌逻辑质检（只找茬，不改文）",
            "2. 去 AI 味 + 沉浸感润色（重点优化文笔）",
            "3. 全面精修（逻辑修正 + 文笔润色 + 扩充细节）"
        ]
    )
    
    if st.button("🚀 开始精修任务", use_container_width=True):
        if not input_text.strip():
            st.warning("请先粘贴正文！")
        else:
            # ================== 模式 1：只找茬 ==================
            if audit_mode.startswith("1"):
                with st.spinner("正在用显微镜寻找逻辑漏洞..."):
                    prompt = f"""
                    你是一名以“毒舌、严谨”著称的网文主编。请审阅下面这章小说。
                    
                    【背景备注】：{context_info}
                    
                    【待审正文】：
                    {input_text}
                    
                    请输出一份《审稿报告》，包含：
                    1. 【逻辑漏洞】：时间线错误、因果不通、战力崩坏等。
                    2. 【人设 OOC】：人物说话做事是否符合其身份和性格？
                    3. 【节奏问题】：哪里太水？哪里太赶？
                    4. 【修改建议】：具体怎么改能救回来。
                    
                    注意：不需要重写正文，只需要输出报告。
                    """
                    report = ask_ai("资深网文主编", prompt, 0.5)
                    st.session_state.audit_report = report
                    st.session_state.revised_text = "" # 此模式无修改稿
                    st.success("审稿报告已生成！")

            # ================== 模式 2：去 AI 味 + 润色 ==================
            elif audit_mode.startswith("2"):
                with st.spinner("正在去除 AI 腔调，注入灵魂..."):
                    # 先不用报告，直接改
                    prompt = f"""
                    你是一名金牌网文改稿师，擅长将平淡的文字改成极具画面感和情绪张力的网文。
                    
                    【任务目标】：对下面这章正文进行“去 AI 化”润色。
                    
                    【原文】：
                    {input_text}
                    
                    【修改要求】：
                    1. 严禁使用“综上所述”、“总而言之”、“眼中闪过一丝”等陈旧套话。
                    2. 把“心理说明”改成“动作细节”。（例：不要写“他很生气”，要写“他捏碎了手里的茶杯，滚烫的茶水流过指缝却浑然不觉”。）
                    3. 增强代入感，多用短句，加快打斗或冲突时的节奏。
                    4. 保留原剧情走向，只提升表现力。
                    
                    请直接输出【润色后的正文】。
                    """
                    revised = ask_ai("金牌改稿师", prompt, 0.8)
                    st.session_state.audit_report = "（此模式直接输出润色稿，无详细报告）"
                    st.session_state.revised_text = revised
                    st.success("润色完成！")

            # ================== 模式 3：全面精修 ==================
            elif audit_mode.startswith("3"):
                with st.spinner("第一步：正在分析逻辑问题..."):
                    # Step 1: 先分析
                    analyze_prompt = f"""
                    请先找出这章正文的逻辑硬伤和节奏问题。
                    原文：{input_text[:3000]}...
                    """
                    report = ask_ai("资深主编", analyze_prompt, 0.6)
                    st.session_state.audit_report = report
                
                with st.spinner("第二步：根据分析结果重写正文..."):
                    # Step 2: 再重写
                    rewrite_prompt = f"""
                    这是原文：
                    {input_text}
                    
                    这是刚才分析出的问题：
                    {report}
                    
                    请根据以上问题，重写这一章。
                    要求：
                    1. 修复所有逻辑漏洞。
                    2. 极度去 AI 味，拒绝翻译腔和说明文。
                    3. 在关键情节处增加细节描写（环境、微表情、潜台词）。
                    4. 字数尽量与原文持平或略多。
                    
                    直接输出重写后的正文。
                    """
                    revised = ask_ai("大神作家", rewrite_prompt, 0.9)
                    st.session_state.revised_text = revised
                    st.success("全面精修完成！")

with col_right:
    st.subheader("📋 审阅结果")
    
    # Tab 页切换报告和正文
    tab1, tab2 = st.tabs(["📊 审稿报告", "✍️ 修改后正文"])
    
    with tab1:
        if st.session_state.audit_report:
            st.markdown(st.session_state.audit_report)
        else:
            st.info("暂无报告，请在左侧点击“开始精修”。")
            
    with tab2:
        if st.session_state.revised_text:
            # 提供编辑框供二次修改
            final_text = st.text_area(
                "修改稿（可直接编辑）：",
                value=st.session_state.revised_text,
                height=500
            )
            st.session_state.revised_text = final_text
            
            st.markdown("---")
            # 下载按钮
            st.download_button(
                label="📥 下载修改稿 (.txt)",
                data=final_text,
                file_name="revised_chapter.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("暂无修改稿。")
            if audit_mode.startswith("1"):
                st.caption("注：模式 1 仅生成报告，不生成修改稿。")

# =============== 底部小工具 ===============
st.markdown("---")
with st.expander("🛠️ 实用小工具：一键提取本章爽点/卖点"):
    if st.button("✨ 提取卖点"):
        if not st.session_state.input_text:
            st.warning("没内容提取得了个寂寞？")
        else:
            with st.spinner("提取中..."):
                p = f"提炼这章的3-5个核心爽点或悬念，用于发朋友圈宣传：\n{st.session_state.input_text[:3000]}"
                hl = ask_ai("营销鬼才", p, 0.8)
                st.markdown(hl)
