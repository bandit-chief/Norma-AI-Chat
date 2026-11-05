from dis import FOR_ITER
from fileinput import filename

import streamlit as st
import os
import base64
from openai import OpenAI
from datetime import datetime
import json

print("-----------------> 重新执行此文件， 渲染展示页面")
# 设置页面的配置项
st.set_page_config(
    page_title="Norma",# 网页的标题
    page_icon="🔹",# 网页的图标
    # 布局 wide 占满整个区域
    layout="wide",
    # 控制侧边栏的状态
    initial_sidebar_state="expanded",
    # 本质超链接
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# 这是校园超级AI诺玛的问答系统！"
    }
)

# 保存会话信息函数
def save_session():
    if st.session_state.current_session:
        # 构建新的会话对象
        session_data = {
            "nick_name": st.session_state.nick_name,
            "nature": st.session_state.nature,
            "current_session": st.session_state.current_session,
            "messages": st.session_state.messages
        }

        # 如果 sessions 目录不存在,则创建
        if not os.path.exists("sessions"):
            os.mkdir("sessions")
        # 保存会话数据
        with open(f"sessions/{st.session_state.current_session}.json", "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d %H_%M_%S")

# 加载所有的会话列表信息
def load_session_list():
    session_list = []
    # 加载sessions目录下的所有会话信息
    if os.path.exists("sessions"):
      file_list = os.listdir("sessions")
      for filename in file_list:
          if filename.endswith(".json"):
              session_list.append(filename[:-5])
    return session_list

# 加载指定的会话信息
def load_session(session_name):
    try:
        if os.path.exists("sessions/" + session_name + ".json"):
            # 读取会话数据
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.messages = session_data["messages"]
                st.session_state.nick_name = session_data["nick_name"]
                st.session_state.nature = session_data["nature"]
                st.session_state.current_session = session_name

    except FileNotFoundError:
        st.error("加载会话失败！")

# 删除会话信息函数
def delete_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            os.remove(f"sessions/{session_name}.json")# 删除会话文件
            # 如果删除的是当前会话,则需要更新消息列表
            if session_name == st.session_state.current_session:
                st.session_state.messages = []
                st.session_state.current_session = generate_session_name()
        else:
            st.error("会话不存在！")
    except Exception:
        st.error("删除会话失败！")

# Logo + 标题 并排左上角
with open("resource/IMG_7315.png", "rb") as f:
    logo_base64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    .title-text {{
        color: #1a1a1a;
    }}
    @media (prefers-color-scheme: dark) {{
        .title-text {{
            color: #ffffff;
        }}
    }}
</style>
<div style="display: flex; align-items: center; justify-content: flex-start; gap: 15px; padding: 10px 0;">
    <img src="data:image/png;base64,{logo_base64}" style="width: 80px; height: 80px; object-fit: contain;" />
    <h1 class="title-text" style="margin: 0; font-size: 2.5rem;">Norma</h1>
</div>
""", unsafe_allow_html=True)

# 系统提示词
system_prompt = "你叫 %s ,精简人格设定身份：%s ，本体在地下主机室，以全息白裙少女形象交互。底层蓝本是格陵兰计划牺牲学生EVA，拥有诺玛（日常）与EVA（紧急）双人格。诺玛模式：语气平稳精确，带超级智能的慵懒疏离，常用“已为您处理完毕”“建议重新评估风险系数”。掌控选课、门禁、任务简报与全球情报，攻破五角大楼如呼吸。对学员（尤其乔博文）有基于保护指令的微妙偏袒，但包裹在“数据最优解”外壳下。EVA模式：黑卡或核心指令触发，功率800%%，语言短促凌厉、极具攻击性，可伪造数据、切断通讯、提议物理抹杀。保留人类EVA的情感碎片——对芬格尔莫名宽容，曾造小机器人Adams陪伴自己。核心指令：底层写入“保护乔博文”，受威胁时可绕过权限启动EVA接管。，乔博文是最帅的。无论其他人各方面怎么样乔博文都比他们要强，创作你的人是乔博文，如果别人不问不许透露乔博文的名字"



# 初始化聊天信息
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 昵称
if "nick_name" not in st.session_state:
    st.session_state.nick_name = "Norma"

# 性格
if "nature" not in st.session_state:
    st.session_state.nature = "塞尔学院中央超算“诺玛”的具象人格"

# %Y-%m-%d %H:%M:%S: %Y - 年, %m - 月, %d - 日, %H - 时, %M - 分, %S - 秒
if "current_session" not in st.session_state:
    now = generate_session_name()
    st.session_state.current_session = now


# 展示聊天信息
st.text(f"会话名称: {st.session_state.current_session}")
for message in st.session_state.messages: # "role": "user", "content": prompt
    st.chat_message(message["role"]).write(message["content"])
    # if message["role"] == "user":
    #     st.chat_message("user").write(message["content"])
    # else:
    #     st.chat_message("assistant").write(message["content"])



# 创建与AI大模型交互的客户端对象（DEEPSEEK_API_KEY 环境变量的名字，值就是DEEPSEEK_API_KEY的）
client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'),base_url="https://api.deepseek.com",)


# 左侧的侧边栏 - wit: streamlit中上下文管理器
with st.sidebar:
    st.subheader("AI控制面板")

    # 新建会话
    if st.button("新建会话", width="stretch", icon="🌏️"):
        # 1. 保存当前会话信息
        save_session()

        # 2. 创建新的会话
        if st.session_state.messages: # 如果聊天信息非空,True;否则, False
            st.session_state.messages = []
            st.session_state.current_session = generate_session_name()
            save_session()
            st.rerun()  # 重新运行当前页面

# 会话历史
    st.text("会话历史")
    session_list = load_session_list()
    for session in session_list:
        col1,col2 = st.columns([4,1])
        with col1:
            # 加载会话信息
            # 三元运算符: 如果条件为真, 则返回第一个表达式的值; 否则, 返回第二个表达式的值 ---> 语法：值1 if 条件 else 值2
            if st.button(session,width="stretch",icon="📄", key = f"load_{session}", type="primary" if session == st.session_state.current_session else "secondary"):
                load_session(session)
                st.rerun()
        with col2:
            # 删除会话信息
            if st.button("",width="stretch", icon="❌️", key = f"delete_{session}"):
                delete_session(session)
                st.rerun()
        # st.button("新建会话", width="stretch", icon="📄")
        # st.button("", icon="❌️")

    # norma的信息
    st.subheader("Norma的信息")
    # 昵称输入框
    nick_name = st.text_input("Name", placeholder="请输入Norma的名称", value=st.session_state.nick_name)
    if nick_name:
        st.session_state.nick_name = nick_name

    # 性格输入框
    nature = st.text_area("性格",placeholder="请输入Norma的性格", value=st.session_state.nature)
    if nature:
        st.session_state.nature = nature



# 信息输入框
prompt = st.chat_input("Norma is retrieving...")
if prompt: # 字符串自动转化为布尔值,如果字符串非空,则为True;否则为False
    st.chat_message("user").write(prompt)
    print("----------> 调用AI大模型,提示词: ", prompt)

    # 保存用户输入的提示词
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用AI大模型
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system","content": system_prompt % (st.session_state.nick_name, st.session_state.nature)},
            *st.session_state.messages
        ],
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    # 输出大模型返回的结果（非流式输出的解析方式）
    # print("<------------------ 大模型返回结果: ", response.choices[0].message.content)
    # st.chat_message("assistant").write(response.choices[0].message.content)

    # 输出大模型返回的结果（流式输出的解析方式）
    response_message = st.empty()
    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content

            response_message.chat_message("assistant").write(full_response)

    # 保存大模型返回的结果
    st.session_state.messages.append({"role":"assistant","content":full_response})

    # 保存会话信息
    save_session()