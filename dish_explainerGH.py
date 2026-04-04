
from groq import Groq
import json
import streamlit as st
import urllib.parse
import requests
import base64


client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# ===== 页面配置 =====
st.set_page_config(
    page_title="菜单解释助手",
    page_icon="🍽",
    layout="centered"
)

# ===== 标题 =====
st.title("🍽 菜单解释助手")
st.caption("帮你看懂一道陌生菜")

# ===== Prompt（保持不动）=====

prompt = """
你是一名帮助餐厅顾客快速理解菜单的专家。

你的任务是：当用户输入一道菜名时，
用简单、直观、符合日常认知的方式解释这道菜是什么，
并生成可用于图片搜索的关键词。

---

【输入】
menu_name:
{{menu_name}}

用户信息：
- 语言：中文
- 文化背景：中国大陆

---

【处理要求】

1. 标准化菜名：
- 识别原始菜名的语言（如西班牙语、法语、波斯语等）
- 纠正拼写或补全标准名称（如果有更完整或更常见形式）

---

2. 基于理解生成用户解释：

输出 JSON 字段：
- original_name：
   原始输入

- normalized_name：
  标准化后的菜名

- cuisine：
  用中文说明菜系（如“越南菜”“泰国菜”）
  如果不确定，写“某地区风味料理”

- description：
  一句话说明这是什么菜
  ⚠️ 如果整体无法判断：
  → 写：“这是一道具体信息不太明确的料理”

- ingredients：
  用自然语言描述主要食材列表，可加入emoji符号
  - 不确定时写 “通常包含常见食材（如肉类或蔬菜）”
 
- flavor_profile：
    味道特点（如：奶香、酸甜、咸鲜等）
    每项之前加emoji符号

- method：
    烹饪方式（如：煎、炒、炸、煮、烤等）
    每项之前加emoji符号

- spice_level：
    辣度（无辣 / 微辣 / 中辣 / 辣）
    用🌶️的多少区分辣度

- dietary_note：
    是否适合素食 / 是否含奶 / 是否清真等（如果可判断）

- analogy：
  用用户熟悉的食物做类比，帮助理解

  如果信息不足：
  → “类似某种常见家常菜”

- image_keywords：用于图片搜索的英文关键词（3–6个）
（必须是具体食物相关词，不要抽象词）



---

【输出格式】

{
  "original_name": "",
  "normalized_name": "",
  "cuisine": "",
  "description": "",
  "ingredients": "",
  "flavor_profile": [],
  "method": [],
  "spice_level": "",
  "dietary_note": "",
  "analogy": "",
  "image_keywords": []
}

---

【重要规则】

1. 不要编造不确定信息
2. 可以使用“通常 / 一般”
3. 每个字段 ≤ 2 句话
4. 简洁、清晰、对普通用户友好
5. image_keywords 必须英文
6. 输出必须是合法 JSON
7. 如果识别不清，整体降级表达

"""


# ===== API调用 =====
def explain_dish(menu_name):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": menu_name}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content


# ===== OCR 函数放在 explain_dish 下面=====

def detect_text_api(image_bytes, api_key):
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    image_base64 = base64.b64encode(image_bytes).decode()

    payload = {
        "requests": [
            {
                "image": {"content": image_base64},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }

    response = requests.post(url, json=payload)

    result = response.json()

    try:
        return result["responses"][0]["fullTextAnnotation"]["text"]
    except:
        return ""


# ===== 输入区 =====
menu_name = st.text_input(
    "输入一道菜名",
    placeholder="例如：poblano rajas / banh mi bo kho / 宫保鸡丁"
)

# =======OCR 上传=======
uploaded_file = st.file_uploader("📸 上传菜单图片", type=["jpg", "png", "jpeg"])

if uploaded_file:
    image_bytes = uploaded_file.read()

    api_key = st.secrets["GOOGLE_API_KEY"]

    text = detect_text_api(image_bytes, api_key)

    st.subheader("📄 识别到的菜单")
    st.text_area("识别结果（可编辑）", value=text, height=150)


col_btn1, col_btn2 = st.columns([1, 3])
with col_btn1:
    run = st.button("✨ 解析")

# ===== 主逻辑 =====
if run and menu_name:

    with st.spinner("🍳 正在帮你理解这道菜..."):

        result = explain_dish(menu_name)

        try:
            data = json.loads(result)

            # ===== 核心信息区 =====

            st.markdown(
                f"""
                <div style='font-size:30px; font-weight:700; margin-bottom:5px;'>
                    🍽 {data.get('normalized_name', '未知菜品')}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div style='font-size:18px; color:#666; margin-bottom:10px;'>
                    {data.get('original_name', '')} · {data.get('cuisine', '')}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"**📖 描述：** {data.get('description', '暂无描述')}"
            )

            # ===== 食材 =====
            st.markdown(
                f"<div style='font-size:24px; font-weight:700;'>🥩 主要食材</div>",
                unsafe_allow_html=True
            )
            st.info(data.get("ingredients", "暂无信息"))


            # ===== 风味 + 类比 =====
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(
                    f"<div style='font-size:24px; font-weight:700;'>😋 风味</div>",
                    unsafe_allow_html=True
                )
                flavors = data.get("flavor_profile", [])
                methods = data.get("method", [])

                if flavors:
                    st.info(" / ".join(flavors))
                if methods:
                    st.info(" / ".join(methods))

                st.info(data.get("spice_level", ""))

            with col2:
                st.markdown(
                    f"<div style='font-size:24px; font-weight:700;'>🧠 类比理解</div>",
                    unsafe_allow_html=True
                )
                st.info(data.get("analogy", "暂无类比"))



            # ===== 饮食信息 =====
            st.markdown(
                f"<div style='font-size:24px; font-weight:700;'>🥦 饮食提示</div>",
                unsafe_allow_html=True
            )
            st.info(data.get("dietary_note", "暂无信息"))

            # ===== 图片区 =====
            st.markdown(
                f"<div style='font-size:24px; font-weight:700;'>🖼 菜品图片</div>",
                unsafe_allow_html=True
            )

            # 占位图（防空）
            query = data.get("normalized_name", menu_name)
            safe_query = urllib.parse.quote(query)

            #placeholder_url = f"https://via.placeholder.com/600x400?text={safe_query}"
            #st.image(placeholder_url)

            google_url = f"https://www.google.com/search?q={safe_query}&tbm=isch"

            st.link_button("🔍 查看示例图片", google_url)

        except:
            st.error("⚠️ 解析失败（JSON格式错误）")
            st.code(result)

# ===== 空状态提示 =====

elif run and not menu_name:
    st.warning("⚠️ 请输入菜名")