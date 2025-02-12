import streamlit as st
import requests

# Set page title
st.set_page_config(page_title="FAFSA Chatbot 🤖", layout="wide")

st.title("🎓 New Aidan 🤖")
st.write("Ask me anything about student aid, FAFSA, and financial aid options!")

# Initialize session state for chat history
if "history" not in st.session_state:
    st.session_state["history"] = []

# User input field
user_query = st.text_input("Type your question here:", key="user_input", on_change=lambda: st.session_state.update({"ask_trigger": True}))

# If Enter is pressed, send the request
if st.session_state.get("ask_trigger"):
    st.session_state["ask_trigger"] = False  # Reset trigger

    if user_query:
        try:
            # ✅ Send request to FastAPI & check for errors
            response = requests.get(f"https://fsa-chatbot.onrender.com/chat?q={user_query}")

            if response.status_code == 200:  # ✅ Ensure valid response
                data = response.json()
                st.session_state["history"].append({
                    "user": user_query,
                    "bot": data.get("response", "I couldn't retrieve an answer."),
                    "source": data.get("source", "No source available.")
                })
            else:
                st.warning(f"⚠️ Error: Received status code {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            st.error(f"⚠️ API request failed: {e}")

        except requests.exceptions.JSONDecodeError:
            st.error("⚠️ API response was not valid JSON. The server may have encountered an issue.")

# Display chat history (most recent first)
st.write("### 📜 Chat History")
if st.session_state["history"]:  # ✅ Make sure history is not empty
    for msg in reversed(st.session_state["history"]):  # 🔹 Reverse order
        st.markdown(f"For the best info head [here]({msg['source']})" if msg["source"] else "No source available.")
        st.markdown(f"**🧑‍💻 You:** {msg['user']}")
        st.markdown(f"**🤖 Bot:** {msg['bot']}")
        st.write("---")  # Separator

st.write("💡 _Powered by AI. Please consult your counselor or financial aid administrator for more detailed questions._")
