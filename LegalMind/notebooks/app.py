import os
import streamlit as st
import pandas as pd
from datetime import datetime
from rag_flow import generate_rag_answer
import time
import re
from wordcloud import WordCloud
from collections import Counter
from sqlalchemy import create_engine, text
import threading

# -------------------- PostgreSQL Setup --------------------
DB_USER = os.getenv("POSTGRES_USER", "legaluser")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "legalpass")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "legalmind")

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create table if it does not exist
with engine.connect() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        query TEXT,
        response TEXT,
        feedback CHAR(1),
        timestamp TIMESTAMP,
        latency FLOAT,
        answer_length INT
    )
    """))
    conn.commit()

# -------------------- Streamlit Page --------------------
st.set_page_config(page_title="Legal Mind", layout="wide")
st.markdown("<h1 style='text-align: center;'>⚖️ Legal Mind 📜</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# -------------------- Session State --------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "feedback_msg" not in st.session_state:
    st.session_state.feedback_msg = ""
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}
if "clear_on_next" not in st.session_state:
    st.session_state.clear_on_next = False
if "page" not in st.session_state:
    st.session_state.page = st.query_params.get("page", ["chat"])[0]

# -------------------- Page Handling --------------------
page = st.session_state.page
def set_page(new_page):
    st.session_state["page"] = new_page

# -------------------- Dashboard Button --------------------
if page != "dashboard":
    col1, col2 = st.columns([9,1])
    with col2:
        if st.button("📊 Open Dashboard"):
            set_page("dashboard")

# -------------------- Dashboard Page --------------------
if page == "dashboard":
    import nltk
    if "stop_words" not in st.session_state:
        nltk.download('stopwords', quiet=True)
        from nltk.corpus import stopwords
        st.session_state.stop_words = set(stopwords.words('english'))

    st.title("📊 Feedback Dashboard")
    stop_words = st.session_state.stop_words

    # Fetch last 500 feedback records only (fast)
    with engine.connect() as conn:
        df_feedback = pd.read_sql("SELECT * FROM feedback ORDER BY timestamp DESC LIMIT 500", conn)

    if df_feedback.empty:
        st.info("No feedback data available yet.")
    else:
        st.markdown("### 👍 vs 👎 Feedback")
        st.bar_chart(df_feedback['feedback'].value_counts())

        st.markdown("### Response Time Distribution (seconds)")
        st.bar_chart(df_feedback['latency'])

        st.markdown("### Answer Length Distribution")
        st.bar_chart(df_feedback['answer_length'])

        st.markdown("### Average Answer Length Over Time")
        df_feedback['timestamp'] = pd.to_datetime(df_feedback['timestamp'])
        avg_length = df_feedback.groupby(df_feedback['timestamp'].dt.date)['answer_length'].mean()
        st.line_chart(avg_length)

        st.markdown("### Most Frequent Keywords (Excluding Stop Words)")
        all_text = " ".join(df_feedback['response'].astype(str)).lower()
        all_text = re.sub(r'\W+', ' ', all_text)
        words = [word for word in all_text.split() if word not in stop_words]
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(" ".join(words))
        st.image(wordcloud.to_array())

        st.markdown("### Top 10 Keywords Frequency")
        word_counts = Counter(words)
        top_words = pd.DataFrame(word_counts.most_common(10), columns=['Keyword','Frequency'])
        st.bar_chart(top_words.set_index('Keyword'))

    if st.button("⬅️ Back to Chat"):
        set_page("chat")

# -------------------- Chat Page --------------------
else:
    with st.form("chat_form", clear_on_submit=True):
        query = st.text_input(
            "Ask a legal question:",
            placeholder="Type your question here...",
            disabled=st.session_state.is_generating
        )
        st.markdown("<p style='font-size:0.8em; color:gray;'>⚠️ Legal Mind can make mistakes. Please verify answers independently.</p>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Send")

    if submitted and query.strip() and not st.session_state.is_generating:
        st.session_state.is_generating = True
        st.session_state.feedback_msg = ""

        if st.session_state.clear_on_next:
            st.session_state.chat_history = []
            st.session_state.clear_on_next = False

        st.session_state.chat_history.append({
            "query": query,
            "answer": "",
            "latency": 0.0,
            "feedback": None,
            "timestamp": datetime.now()
        })

        idx = len(st.session_state.chat_history) - 1
        placeholder = st.empty()
        st.session_state.chat_history[idx]["placeholder"] = placeholder
        placeholder.markdown(f"<div style='padding:15px; margin:10px 0; border-radius:12px; background-color:#1e1e1e;'><p><strong>🧑‍💼 Q:</strong> {query}</p><div style='margin-top:5px; color:orange;'><strong>🤖 A:</strong> 🤔 Thinking for a legally correct answer...</div></div>", unsafe_allow_html=True)

        start_time = time.time()
        answer = generate_rag_answer(query, alpha=0.5)
        latency = time.time() - start_time

        # Incremental answer display
        final_answer = ""
        for char in answer:
            final_answer += char
            placeholder.markdown(f"<div style='padding:15px; margin:10px 0; border-radius:12px; background-color:#1e1e1e;'><p><strong>🧑‍💼 Q:</strong> {query}</p><div style='margin-top:5px;'><strong>🤖 A:</strong> {final_answer} ▌</div><div style='color:gray; font-size:0.85em; margin-top:6px;'>⏱ Response Time: {latency:.2f} sec</div></div>", unsafe_allow_html=True)
            time.sleep(0.01)  # faster incremental rendering

        st.session_state.chat_history[idx]["answer"] = final_answer
        st.session_state.chat_history[idx]["latency"] = latency
        st.session_state.is_generating = False

    # -------------------- Feedback Buttons --------------------
    def save_feedback(idx, chat):
        def task():
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "INSERT INTO feedback (query,response,feedback,timestamp,latency,answer_length) "
                        "VALUES (:q,:r,:f,:t,:l,:al)"
                    ),
                    {
                        "q": chat['query'],
                        "r": chat['answer'],
                        "f": chat['feedback'],
                        "t": chat['timestamp'],
                        "l": chat['latency'],
                        "al": len(chat['answer'])
                    }
                )
                conn.commit()

        threading.Thread(target=task).start()
        st.session_state.feedback_given[idx] = True
        st.session_state.feedback_msg = "✅ Feedback recorded."

    # Display chat with feedback buttons
    for idx, chat in enumerate(st.session_state.chat_history):
        placeholder = chat.get("placeholder", st.empty())
        placeholder.markdown(f"""
            <div style='padding:15px; margin:10px 0; border-radius:12px; background-color:#1e1e1e;'>
                <p><strong>🧑‍💼 Q:</strong> {chat['query']}</p>
                <div style='margin-top:5px;'>
                    <strong>🤖 A:</strong> {chat['answer']}
                </div>
                <div style='color:gray; font-size:0.85em; margin-top:6px;'>
                    ⏱ Response Time: {chat['latency']:.2f} sec
                </div>
            </div>
        """, unsafe_allow_html=True)

        if not st.session_state.feedback_given.get(idx):
            col1, col2 = st.columns([1,1])
            if col1.button("👍", key=f"up_{idx}"):
                chat['feedback'] = "👍"
                save_feedback(idx, chat)
            if col2.button("👎", key=f"down_{idx}"):
                chat['feedback'] = "👎"
                save_feedback(idx, chat)

    if st.session_state.feedback_msg:
        st.info(st.session_state.feedback_msg)
