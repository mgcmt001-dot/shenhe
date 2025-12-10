import streamlit as st
from openai import OpenAI

# =============== 基础配置 ===============
st.set_page_config(
    page_title="DeepNovel 逻辑检测 & 去AI化审稿器",
    layout="wide",
    page_icon="🧐"
)

# =============== Sidebar：API & 说明 ===============
with st.sidebar:
    st.title("⚙️ 引擎设置")

    api_key = st.text_input("SiliconFlow API Key", type="password")
    if not api_key:
        st.warning("请输入 API Key 才能开始审稿。")
        st.stop()

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1"
    )

    st.markdown("---")
    st.info(
        "使用建议：\n"
        "1. 左侧粘贴【待审稿正文】（整章 / 多章均可）\n"
        "2. 可选粘贴【大纲/设定】帮助判定逻辑\n"
        "3. 点击按钮生成：逻辑审稿报告 + 去AI化修改稿\n"
        "4. 右侧可下载 TXT 文件。"
    )

# =============== 通用 AI 调用 ===============
def ask_ai(system_role: str, user_prompt: str, temperature: float = 0.8, model: str = "deepseek-ai/DeepSeek-V3"):
    """
    通用封装：调用 SiliconFlow DeepSeek-V3
    """
    high_level_rules = """
    【高阶审稿规范（系统附加约束）】
    - 不要输出“作为AI，我……”之类的废话。
    - 用具体例子+解释，比空泛评价更重要。
    - 明确区分：客观逻辑错误 vs. 风格/喜好问题。
    - 不要自说自话加剧情，只在要求的范围内修改文本。
    """
    system_full = system_role + "\n" + high_level_rules

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_full},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception as e:
        st.error(f"API 调用失败：{e}")
        return ""

# =============== Session State 初始化 ===============
def init_state():
    defaults = {
        "logic_report": "",
        "rewritten_text": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =============== 页面主体 ===============
st.title("🧐 DeepNovel 逻辑检测 & 去AI化审稿器")

left, right = st.columns([1.1, 0.9])

# ------------------------------------------------------
# 左侧：输入区
# ------------------------------------------------------
with left:
    st.subheader("✏️ 输入区")

    outline_text = st.text_area(
        "可选：大纲 / 世界观设定 / 人物小传（可留空，但有会更准）",
        height=150,
        placeholder=(
            "示例：\n"
            "- 整体故事大纲 / 章节目录\n"
            "- 世界观设定、能力体系规则\n"
            "- 主要人物设定和性格走向\n"
        )
    )

    raw_text = st.text_area(
        "待审稿正文（建议一章或数章，尽量不要太碎）",
        height=400,
        placeholder=(
            "在这里粘贴你想审稿 / 去AI味的小说正文。\n"
            "可以是一整章，也可以是几万字的大段内容。"
        )
    )

    st.markdown("---")
    st.subheader("🔧 审稿选项")

    focus_logic = st.checkbox("优先抓【硬逻辑错误】（时间线/因果/设定自相矛盾）", value=True)
    focus_style = st.checkbox("优先弱化【AI味道】（流水账、模板句、机翻感）", value=True)
    keep_author_voice = st.checkbox("尽量保留原作者的用词习惯和语气", value=True)

    if st.button("🚀 开始逻辑检测 & 去AI化润色", use_container_width=True):
        if not raw_text.strip():
            st.warning("正文为空，没法审稿噢。")
        else:
            with st.spinner("正在认真审稿中……"):

                # ---------------- 1. 生成逻辑审稿报告 ----------------
                logic_emphasis = []
                if focus_logic:
                    logic_emphasis.append("硬逻辑（时间线/因果/设定/人物动机）")
                if focus_style:
                    logic_emphasis.append("AI味/流水账问题")
                if not logic_emphasis:
                    logic_emphasis.append("整体质量")

                logic_prompt = f"""
你是一个毒舌但非常专业负责的网络小说主编，现在要对一段正文进行【逻辑审稿 + 去AI味诊断】。

【可参考的大纲 / 设定 / 人物信息】（可能为空）：
{outline_text or "（作者未提供额外大纲/设定信息）"}

【待审稿正文】：
{raw_text}

请输出一份结构清晰的《编辑审稿报告》，务必包含以下部分：

一、整体评价（简要）
- 用 3~5 句，概括本段文字在：剧情推进、人物张力、文风完成度上的整体情况。

二、硬逻辑问题（时间线 / 因果 / 设定自洽性）
- 针对每一个你认为有问题的地方：
  · 用【原文片段】引用（不必太长，能定位即可）；
  · 说明：具体哪里逻辑不通？时间、地点、因果、力量体系、人物动机哪个出了问题？
  · 给出 1~2 种可行的修改方向（不是帮改文，而是告诉作者该如何处理）。
- 如果几乎没有硬逻辑问题，也请明确说明“未发现明显硬逻辑错误”，而不是空着。

三、人物行为与人设（一致性 / OOC）
- 结合你从文本中读到的人设预期，指出：
  · 哪些行为、对话非常贴合人设（可点名 1~3 处表扬）；
  · 哪些地方存在“性格忽然转弯”“动机不足以支撑行为”的情况，属于轻微或严重 OOC。
- 给出修改建议：是补动机？补铺垫？还是调弱/调整行为强度？

四、节奏与信息量
- 按照【段落/场景】来评价：
  · 哪些段落明显“水”或者重复信息，可以删减或合并？
  · 哪些地方推进过快、跳太多，引发理解断层？需要补桥段或补描述。
- 给出调整建议：可以具体到“在 A 与 B 之间补一个 xx 互动”这种层级。

五、AI味 / 流水账问题诊断
- 指出 5~10 句你认为“最有AI味道”的句子或段落，逐条列出：
  · 【原句】：……
  · 【问题】：模板化 / 空泛 / 机翻感 / 无效感慨 / 无意义的流水描述……
  · 【建议重写思路】：（不必全文改写，但说明可以怎样改得更生活化、更有画面感/性格感）
- 如果整体 AI 味不重，也请给出 2~3 条“可以锦上添花优化”的建议。

六、可执行修改清单（给作者看的 To-Do）
- 用项目符号列出 8~15 条“可以直接照着改”的建议，例如：
  · “第X段某句台词太直白，可以改成 xx 这种更带性格的说法”
  · “在XX场景之前补一小段主角的犹豫/挣扎内心”
  · “将XX段中的‘旁白总结句’削减为 1 句，重心放到人物动作上”
- 别给空洞话（如“注意文笔”“多写细节”），要具体、可执行。

审稿重点方向：
- 当前作者特别希望你重点关注：{ "、".join(logic_emphasis) }。
- 记住：你是站在“帮作者变得更好”的角度，不是简单喷人。
"""
                logic_report = ask_ai(
                    "你是一名从业十年以上的网络小说主编，毒舌但非常负责。",
                    logic_prompt,
                    temperature=0.7
                )

                # ---------------- 2. 生成去AI化修改稿 ----------------
                style_clause = "尽量保留原作者的用词习惯和语气。" if keep_author_voice else (
                    "在保证故事方向不变的前提下，可以适度优化语气和用词，让整体更有个性。"
                )

                rewrite_prompt = f"""
你现在是一个职业小说作家，手上拿到一段【原始正文】和一份【编辑审稿报告】。

【原始正文】：
{raw_text}

【编辑审稿报告】：
{logic_report}

请根据审稿报告，对原始正文进行一次【去AI化+增强逻辑】的重写，规则如下：

一、必须保留的东西
1. 故事情节的大方向、关键事件顺序不能改变（谁对谁做了什么、结果大体如何，要一致）。
2. 重要信息点和伏笔不能删，只能用更自然的方式表达。
3. 主要人物的基本人设和立场不能乱改。

二、可以修改的东西
1. 调整存在硬逻辑问题的地方（时间线/因果关系/设定自洽），做必要的补铺垫或微调剧情。
2. 弱化或重写“AI味”句子：去掉模板化、空洞、机翻感、无意义的感慨和流水账。
3. 优化台词和心理描写，让人物说话更有“人味”和个性，有必要时可少量增减台词。

三、文风要求
1. {style_clause}
2. 不要写成“作文腔”或“议论文”，保持小说叙事感和画面感。
3. 不要在正文中解释“这是伏笔”“这是象征”等幕后信息，让读者自然感受到就好。

四、篇幅要求
1. 修改稿的整体篇幅可以比原文略短或略长，但不要缩减到只有原文的一半以下。
2. 如需补铺垫或补场景，可以适当多写一点细节和对话。

请直接输出【修改后的完整正文】，不要再额外附加评论或解释。
"""
                rewritten = ask_ai(
                    "你是一名擅长修文和去AI味的职业小说作者。",
                    rewrite_prompt,
                    temperature=0.9
                )

                st.session_state.logic_report = logic_report or ""
                st.session_state.rewritten_text = rewritten or ""

                st.success("✅ 审稿报告 & 去AI化修改稿 已生成，右侧可查看并下载。")

# ------------------------------------------------------
# 右侧：输出区
# ------------------------------------------------------
with right:
    st.subheader("📑 输出区")

    report = st.session_state.logic_report
    rewritten = st.session_state.rewritten_text

    tabs = st.tabs(["审稿报告", "修改稿对比"])

    with tabs[0]:
        st.subheader("📋 编辑审稿报告")

        if report:
            st.markdown(report)
            st.markdown("---")
            st.download_button(
                "💾 下载审稿报告 TXT",
                data=report,
                file_name="logic_review_report.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("👈 左侧填写内容并点击【开始逻辑检测 & 去AI化润色】后，这里会显示详细审稿报告。")

    with tabs[1]:
        st.subheader("📝 原文 vs 去AI化修改稿")

        if rewritten:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**原始正文（只读）**")
                st.text_area(
                    "原文",
                    value=raw_text,
                    height=360
                )
            with col2:
                st.markdown("**去AI化修改稿（可复制）**")
                st.text_area(
                    "修改稿",
                    value=rewritten,
                    height=360
                )

            st.markdown("---")
            st.download_button(
                "💾 下载修改稿 TXT",
                data=rewritten,
                file_name="rewritten_text_deai.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("👈 生成审稿后，这里会展示原文与去AI化修改稿的对比，并支持下载。")
