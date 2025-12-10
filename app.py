import os
import json
import streamlit as st
import google.generativeai as genai

# ============ 基本配置 ============

st.set_page_config(
    page_title="小说去AI化与逻辑润色助手",
    page_icon="📖",
    layout="wide",
)

st.title("📖 小说去AI化与逻辑润色助手")
st.markdown(
    """
本工具面向**小说作者/投稿作者**，用于对初稿（包括 AI 生成稿）进行：

- 去AI化润色：弱化常见 AI 痕迹，让语言更自然、有个性；
- 逻辑与设定检查：人物动机、世界观、自洽性等问题提示。

> 请自行确认投稿平台是否允许使用 AI 辅助创作，并对最终稿件负责。
"""
)

# ============ Google Gemini 配置工具函数 ============

# 为不同“档位”准备候选模型列表：会按顺序依次尝试
MODEL_CANDIDATES = {
    # “轻量档”：先试 1.5-flash，不行就试 gemini-pro，再不行试 text-bison-001
    "gpt-4.1-mini": [
        "gemini-1.5-flash",
        "gemini-pro",
        "text-bison-001",
    ],
    # “强力档”：先试 1.5-pro，不行再降级
    "gpt-4.1": [
        "gemini-1.5-pro",
        "gemini-pro",
        "text-bison-001",
    ],
}


def configure_gemini(user_api_key: str):
    """
    优先使用用户在前端输入的 API Key。
    如未输入，可选择性地回退到环境变量/Streamlit secrets（方便你自己调试）。

    使用 GOOGLE_API_KEY 这个名字，避免和你之前的 OpenAI Key 混淆。
    """
    api_key = None

    if user_api_key and user_api_key.strip():
        api_key = user_api_key.strip()
    else:
        # 你如果不想有任何回退，可以把下面这两段删掉
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error(
            "未检测到 Google Gemini API Key。\n\n"
            "请在左侧输入你的 Gemini API Key，或在环境变量/Secrets 中设置 GOOGLE_API_KEY。"
        )
        st.stop()

    # 配置全局 Gemini
    genai.configure(api_key=api_key)


def generate_with_fallback(prompt: str, temperature: float, candidate_models):
    """
    依次尝试一组候选模型：
    - 某个模型如果报 404 / not found，就自动换下一个；
    - 一旦有一个成功，就返回 (raw_output, 使用的模型名)；
    - 如果全部失败，则抛出最后一次的异常。
    """
    last_error = None
    for model_name in candidate_models:
        try:
            gemini_model = genai.GenerativeModel(model_name)
            response = gemini_model.generate_content(
                [
                    "你是一名经验丰富的中文小说编辑和写作教练，"
                    "擅长帮助作者对稿件进行去AI化、人性化润色，并指出逻辑与设定问题。",
                    prompt,
                ],
                generation_config={
                    "temperature": float(temperature),
                    "max_output_tokens": 8192,
                },
            )
            raw_output = response.text  # 预期为 JSON 字符串（由 prompt 约束）
            if not raw_output:
                raise RuntimeError(f"模型 {model_name} 返回内容为空。")
            return raw_output, model_name

        except Exception as e:
            msg = str(e)
            # 针对“模型不存在 / 不支持”的情况，继续尝试下一个
            if "404" in msg and ("not found for API version" in msg or "not found" in msg):
                last_error = e
                continue
            # 其他错误（配额、鉴权等）直接抛出
            last_error = e
            break

    # 所有候选模型都失败了
    if last_error:
        raise last_error
    raise RuntimeError("未能找到可用的 Gemini 模型。")


# ============ 侧边栏设置 ============

with st.sidebar:
    st.header("🔑 Google Gemini 设置")

    # 前端输入 Google API Key
    user_api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="你的密钥只在本次会话中使用，不会被写死到代码里。",
    )

    st.header("⚙ 模型与风格")

    # 这里的选项名字保持不变，但内部会用它来选择候选模型列表
    model = st.selectbox(
        "模型档位（内部会自动选择可用的 Gemini 模型）",
        options=["gpt-4.1-mini", "gpt-4.1"],
        index=0,
        help="轻量档优先尝试 gemini-1.5-flash，强力档优先尝试 gemini-1.5-pro，不可用时自动降级。",
    )

    temperature = st.slider(
        "创造力（temperature）",
        min_value=0.0,
        max_value=1.2,
        value=0.5,
        step=0.1,
        help="数值越高，改写越大胆、越有创意。",
    )

    style_choice = st.selectbox(
        "风格偏好",
        options=[
            "保持原文风格为主",
            "偏商业流行风（适合杂志/实体出版）",
            "文学性偏强（语言更讲究）",
            "网文爽文风（节奏快、爽感强）",
        ],
        index=0,
    )

    st.markdown("---")

    do_humanize = st.checkbox(
        "进行去AI化润色", value=True,
        help="减少模板化表达、空洞鸡汤句、过度解释等 AI 痕迹。"
    )
    do_logic = st.checkbox(
        "进行逻辑与世界观检查", value=True,
        help="包括人物动机、时间线、设定自洽等。"
    )

    target_use = st.selectbox(
        "稿件主要用途",
        options=["杂志/出版社投稿", "网文平台连载", "征文比赛", "个人练笔/自用"],
        index=0,
    )

    st.markdown("---")
    st.caption("提示：长文建议分章节处理，可以更细致。")


# ============ 主区域输入 ============

st.subheader("✏ 粘贴你的小说文本")

default_placeholder = (
    "在这里粘贴你想要处理的小说片段，可以是一个场景、一章或几千字的部分。\n\n"
    "建议：一次处理 2k~5k 字左右，方便精细修改和检查。"
)

raw_text = st.text_area(
    "小说原文",
    value="",
    height=320,
    placeholder=default_placeholder,
)

st.subheader("🌍 可选：补充设定 / 大纲信息（有助于逻辑检查）")
extra_info = st.text_area(
    "世界观、人物背景、大纲要点（可选）",
    value="",
    height=150,
    placeholder="例如：\n"
    "- 故事发生在近未来赛博朋克城市；\n"
    "- 男主是卧底警察，表面和黑帮是朋友；\n"
    "- 女主前期不知道男主身份；\n"
    "- 第二卷不能出现超自然元素；\n",
)

col1, col2 = st.columns([1, 2])
with col1:
    run_button = st.button("🚀 开始分析与润色", type="primary")
with col2:
    char_count = len(raw_text)
    st.write(f"当前字数（含空格）：**{char_count}** 字左右")

    if char_count > 8000:
        st.warning("文本较长，可能会略微增加处理成本，建议按章节分段处理。")


# ============ Prompt 构建 ============

def build_user_prompt(
    text: str,
    extra: str,
    style_choice: str,
    do_humanize: bool,
    do_logic: bool,
    target_use: str,
) -> str:
    """
    将页面上的参数整理成一个清晰的用户指令。
    """
    humanize_flag = "是" if do_humanize else "否"
    logic_flag = "是" if do_logic else "否"

    prompt = f"""
下面是作者提供的一段小说文本，请你作为**资深中文小说编辑+写作教练**进行专业处理。

【处理目标】：
1. 在不改变核心情节和人物性格的大前提下，对文本进行适度润色。
2. 根据需要，弱化常见 AI 写作痕迹，让文字更有“人味”和个人风格。
3. 如勾选，则检查逻辑和世界观自洽性，指出可能的问题并给出改进建议。

【参数设置】：
- 去AI化润色：{humanize_flag}
- 逻辑/设定检查：{logic_flag}
- 风格偏好：{style_choice}
- 稿件用途：{target_use}

【如果进行了去AI化润色】：
- 不要一味删减字数，允许适当扩写细节或内心戏；
- 避免：套话鸡汤、过度解释、毫无个性的“标准答案”句式；
- 鼓励：有点棱角的表达、细节描写、符合人物身份的语言；
- 保持整体叙事视角、人称、时态的一致性。

【如果进行了逻辑/设定检查】：
- 优先关注以下方面：
  - 人物行为和台词是否符合其性格和已知信息；
  - 时间线是否合理，有没有“瞬间移动”“前后矛盾”等问题；
  - 世界观/设定有没有自相矛盾或突然改变；
  - 伏笔和信息量是否合适，是否出现“作者知道但角色不可能知道”的情况。
- 请用简洁明了的条目说明问题，并给出可操作的修改建议。

【原文小说片段】：
{text}

"""
    if extra.strip():
        prompt += f"""
【作者补充的世界观/大纲信息】：
{extra}
"""
    prompt += """
【输出格式（务必严格返回 JSON）】：
请严格返回一个 JSON 对象，键包括：

- "edited_text": string，编辑和润色后的完整文本（如果没有勾选去AI化润色，也请对明显错别字/语病做轻微修正即可）。
- "ai_style_issues": array of string，列出你认为原文中带有“AI写作痕迹”的问题点（如果未勾选去AI化，可填空数组）。
- "logic_issues": array of string，列出逻辑、设定、自洽性相关的问题和简要说明（如果未勾选逻辑检查，可填空数组）。
- "suggestions": string，从“作为编辑给作者写反馈”的角度，给出整体写作建议（可以包括节奏、人物塑造、叙事角度等）。

注意：
- 只输出合法 JSON，不要包含 Markdown 代码块标记或多余说明。
"""
    return prompt.strip()


# ============ 调用 Gemini 并展示结果 ============

if run_button:
    if not raw_text.strip():
        st.warning("请先在上方粘贴要处理的小说文本。")
    else:
        # 配置 Gemini（使用前端输入的 API Key 或环境变量）
        configure_gemini(user_api_key)

        with st.spinner("正在使用 Google Gemini 分析与润色文本……"):

            user_prompt = build_user_prompt(
                text=raw_text,
                extra=extra_info,
                style_choice=style_choice,
                do_humanize=do_humanize,
                do_logic=do_logic,
                target_use=target_use,
            )

            candidate_models = MODEL_CANDIDATES.get(
                model,
                ["gemini-1.5-flash", "gemini-pro", "text-bison-001"],
            )

            try:
                # 自动在候选模型中寻找一个可用的
                raw_output, used_model = generate_with_fallback(
                    prompt=user_prompt,
                    temperature=temperature,
                    candidate_models=candidate_models,
                )

                data = json.loads(raw_output)

            except json.JSONDecodeError:
                st.error("模型返回的内容不是合法 JSON，原始输出如下（方便你排查）：")
                st.code(raw_output)
            except Exception as e:
                st.error(f"调用 Gemini 模型或解析结果时出错：{e}")
            else:
                edited_text = data.get("edited_text", "").strip()
                ai_issues = data.get("ai_style_issues", [])
                logic_issues = data.get("logic_issues", [])
                suggestions = data.get("suggestions", "").strip()

                st.markdown("---")
                st.caption(f"本次实际使用的模型：**{used_model}**")

                st.subheader("✅ 编辑后文本（可再自行微调）")

                # 显示润色后文本
                edited_area = st.text_area(
                    "编辑后文本",

            
