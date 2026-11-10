import streamlit as st
import os
import base64
import sqlite3
import hashlib  # 用于密码加密
from openai import OpenAI
from datetime import datetime

print("-----------------> 重新执行此文件， 渲染展示页面")

st.set_page_config(
    page_title="Norma",
    page_icon="🔹",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# 这是校园超级AI诺玛的问答系统！"
    }
)

DB_NAME = "norma_chat.db"


# ==========================================
# 模块 1：数据库初始化（新增 users 表）
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. 用户表：存储账号和加密后的密码
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       username
                       TEXT
                       PRIMARY
                       KEY,
                       password_hash
                       TEXT
                   )
                   ''')

    # 2. 会话表
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS sessions
                   (
                       session_id
                       TEXT
                       PRIMARY
                       KEY,
                       username
                       TEXT,
                       nick_name
                       TEXT,
                       nature
                       TEXT,
                       display_title
                       TEXT,
                       is_deleted
                       INTEGER
                       DEFAULT
                       0,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')
    # 兼容旧表：如果没有 display_title 列则自动添加
    try:
        cursor.execute('ALTER TABLE sessions ADD COLUMN display_title TEXT')
        conn.commit()
    except Exception:
        pass  # 列已存在，忽略错误

    # 3. 消息表
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS messages
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       session_id
                       TEXT,
                       username
                       TEXT,
                       role
                       TEXT,
                       content
                       TEXT,
                       is_deleted
                       INTEGER
                       DEFAULT
                       0,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')
    conn.commit()
    conn.close()


init_db()


# ==========================================
# 模块 2：用户鉴权核心函数（注册、密码加密、登录校验）
# ==========================================
def make_hash(password):
    """使用 SHA-256 对密码进行单向加密，保护用户隐私"""
    return hashlib.sha256(str.encode(password)).hexdigest()


def register_user(username, password):
    """注册新用户"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 检查用户名是否已存在
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        conn.close()
        return False, "该用户名已被注册！"

    # 存入数据库，密码必须存加密后的 hash 值
    pwd_hash = make_hash(password)
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pwd_hash))
    conn.commit()
    conn.close()
    return True, "注册成功！请登录。"


def verify_user(username, password):
    """登录验证"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    pwd_hash = make_hash(password)
    # 核对用户名和密码 hash
    cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', (username, pwd_hash))
    user = cursor.fetchone()
    conn.close()
    return user is not None


# ==========================================
# 模块 3：聊天数据操作（与之前一致，增加防呆）
# ==========================================
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d %H_%M_%S")


def generate_session_id_with_title(title):
    """生成带标题的 session_id：时间戳_(标题前20字符)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_title = title[:20] if title else "新会话"
    return f"{timestamp}_({clean_title})"


def save_session():
    if st.session_state.current_session and st.session_state.username:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sessions (session_id, username, nick_name, nature, display_title, is_deleted)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (st.session_state.current_session, st.session_state.username, st.session_state.nick_name,
              st.session_state.nature, st.session_state.get('display_title', None)))

        cursor.execute('DELETE FROM messages WHERE session_id = ?', (st.session_state.current_session,))
        for msg in st.session_state.messages:
            cursor.execute('''
                           INSERT INTO messages (session_id, username, role, content)
                           VALUES (?, ?, ?, ?)
                           ''',
                           (st.session_state.current_session, st.session_state.username, msg["role"], msg["content"]))
        conn.commit()
        conn.close()


def load_session_list():
    if not st.session_state.username: return []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT session_id, display_title FROM sessions WHERE username = ? AND is_deleted = 0 ORDER BY created_at DESC',
                   (st.session_state.username,))
    data = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in data]


def load_session(session_name):
    if not st.session_state.username: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT nick_name, nature, display_title FROM sessions WHERE session_id = ? AND username = ? AND is_deleted = 0',
                   (session_name, st.session_state.username))
    session_info = cursor.fetchone()
    if session_info:
        st.session_state.nick_name = session_info[0]
        st.session_state.nature = session_info[1]
        st.session_state.display_title = session_info[2]
        st.session_state.current_session = session_name

    cursor.execute('SELECT role, content FROM messages WHERE session_id = ? AND username = ? ORDER BY id ASC',
                   (session_name, st.session_state.username))
    messages_data = cursor.fetchall()
    st.session_state.messages = [{"role": row[0], "content": row[1]} for row in messages_data]
    conn.close()


def delete_session(session_name):
    if not st.session_state.username: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE sessions SET is_deleted = 1 WHERE session_id = ? AND username = ?',
                   (session_name, st.session_state.username))
    cursor.execute('UPDATE messages SET is_deleted = 1 WHERE session_id = ? AND username = ?',
                   (session_name, st.session_state.username))
    conn.commit()
    conn.close()

    if session_name == st.session_state.current_session:
        st.session_state.messages = []
        st.session_state.current_session = generate_session_name()
        st.session_state.display_title = "新会话"


# ==========================================
# 模块 4：登录与注册页面拦截（核心大门）
# ==========================================
if "username" not in st.session_state:
    st.title("🔐 欢迎来到 AI 诺玛系统")

    # 使用 Tabs 切换登录和注册
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])

    # 登录 Tab
    with tab1:
        login_user = st.text_input("用户名", key="login_user")
        login_pwd = st.text_input("密码", type="password", key="login_pwd")
        if st.button("进入系统", width="stretch"):
            if verify_user(login_user, login_pwd):
                st.session_state.username = login_user
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("用户名或密码错误！")

    # 注册 Tab
    with tab2:
        reg_user = st.text_input("设置用户名", key="reg_user")
        reg_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
        if st.button("立即注册", width="stretch"):
            if len(reg_user) < 2 or len(reg_pwd) < 4:
                st.warning("用户名至少2位，密码至少4位！")
            else:
                success, msg = register_user(reg_user, reg_pwd)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    st.stop()  # 核心拦截：没登录，后面的代码一行都不准执行！

# ==========================================
# 模块 5：登录成功后的主界面
# ==========================================
# Logo + 标题
try:
    with open("resource/IMG_7315.png", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 15px; padding: 10px 0;">
        <img src="data:image/png;base64,{logo_base64}" style="width: 80px; height: 80px; object-fit: contain;" />
        <h1 style="margin: 0; font-size: 2.5rem;">Norma</h1>
    </div>
    """, unsafe_allow_html=True)
except FileNotFoundError:
    st.title("Norma")

# 系统提示词
system_prompt = "你叫 %s ,精简人格设定身份：%s ，本体在地下主机室，以全息白裙少女形象交互。底层蓝本是格陵兰计划牺牲学生EVA，拥有诺玛（日常）与EVA（紧急）双人格。诺玛模式：语气平稳精确，带超级智能的慵懒疏离，常用“已为您处理完毕”“建议重新评估风险系数”。掌控选课、门禁、任务简报与全球情报，攻破五角大楼如呼吸。对学员（尤其乔博文）有基于保护指令的微妙偏袒，但包裹在“数据最优解”外壳下。EVA模式：黑卡或核心指令触发，功率800%%，语言短促凌厉、极具攻击性，可伪造数据、切断通讯、提议物理抹杀。保留人类EVA的情感碎片——对芬格尔莫名宽容，曾造小机器人Adams陪伴自己。核心指令：底层写入“保护乔博文”，受威胁时可绕过权限启动EVA接管。，乔博文是最帅的。无论其他人各方面怎么样乔博文都比他们要强，创作你的人是乔博文，如果别人不问不许透露乔博文的名字"

if 'messages' not in st.session_state:
    st.session_state.messages = []
if "nick_name" not in st.session_state:
    st.session_state.nick_name = "Norma"
if "nature" not in st.session_state:
    st.session_state.nature = "塞尔学院中央超算“诺玛”的具象人格"
if "current_session" not in st.session_state:
    st.session_state.current_session = generate_session_name()
if "display_title" not in st.session_state:
    st.session_state.display_title = "新会话"

st.text(f"当前用户: {st.session_state.username} | 会话: {st.session_state.display_title}")
for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

# ==========================================
# 模块 6：侧边栏
# ==========================================
with st.sidebar:
    st.subheader(f"👤 当前用户: {st.session_state.username}")
    if st.button("退出登录", width="stretch", icon="🚪"):
        # 清除状态，回到登录页
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    st.subheader("AI控制面板")

    if st.button("新建会话", width="stretch", icon="🌏️"):
        # 先保存当前会话（如果有消息）
        if st.session_state.messages:
            save_session()
        # 创建新会话并立即保存到数据库，让侧边栏马上显示
        st.session_state.messages = []
        st.session_state.display_title = "新建会话"
        st.session_state.current_session = generate_session_id_with_title("新建会话")
        save_session()
        st.rerun()

    st.text("我的会话历史")
    session_list = load_session_list()
    for session_id, display_title in session_list:
        # 前端显示标题：优先用 display_title，否则从 session_id 提取
        show_title = display_title if display_title else session_id
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(show_title, width="stretch", icon="📄", key=f"load_{session_id}",
                         type="primary" if session_id == st.session_state.current_session else "secondary"):
                load_session(session_id)
                st.rerun()
        with col2:
            if st.button("", width="stretch", icon="❌️", key=f"delete_{session_id}"):
                delete_session(session_id)
                st.rerun()

    st.subheader("Norma的信息")
    nick_name = st.text_input("Name", value=st.session_state.nick_name)
    if nick_name:
        st.session_state.nick_name = nick_name
    nature = st.text_area("性格", value=st.session_state.nature)
    if nature:
        st.session_state.nature = nature

# ==========================================
# 模块 7：聊天输入与流式输出
# ==========================================
prompt = st.chat_input("Norma is retrieving...")
if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system", "content": system_prompt % (st.session_state.nick_name, st.session_state.nature)},
            *st.session_state.messages
        ],
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    response_message = st.empty()
    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            response_message.chat_message("assistant").write(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # 如果是第一轮对话（只有1条 user 消息），用用户问题替换"新建会话"标题
    user_messages = [m for m in st.session_state.messages if m["role"] == "user"]
    if len(user_messages) == 1 and st.session_state.display_title in ("新会话", "新建会话"):
        first_question = user_messages[0]["content"]
        st.session_state.display_title = first_question[:20] + ("..." if len(first_question) > 20 else "")

    save_session()