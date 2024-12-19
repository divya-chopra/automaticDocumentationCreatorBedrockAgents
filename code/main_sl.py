import os 
import boto3
import streamlit as st
import uuid

# Sample questions to guide users
SAMPLE_QUESTIONS = [
    "What are the best practices for cloud security?",
    "Fetch infrastructure components of my application with app_id=100",
    "Create infrastructure documentation of my application with app_id=100",
    "Suggest cost optimization strategies for my cloud application with app_id=100",
]

st.title("AUTOMATED APP DOCUMENTATION USING AWS BEDROCK AGENTS - POC")
st.sidebar.markdown('''
# **Automated App Documentation Using AWS Bedrock Agents - POC**

Welcome to the **Automated App Documentation POC**! This app showcases a Gen AI-powered **Agentic Chatbot** built with **Amazon Bedrock**. The chatbot automates infrastructure documentation and helps you analyze your applications based on cloud best practices.

## **Features:**
- **Current Infrastructure Query**: Ask for the infrastructure of any application (e.g., app_id:100) and get the details instantly.
- **Documentation Creation & Upload**: Create and upload documentation directly to S3 for secure storage.
- **Best Practices Analysis**: Query cloud best practices across various pillars: security, cost, performance, operations, sustainability, and reliability.
- **Infrastructure Analysis**: Analyze your application's infrastructure against cloud best practices for improved governance.

## **How it Works:**
1. Type your queries in the chat window.
2. The chatbot fetches the current infrastructure and generates documentation.
3. Receive instant feedback and suggestions based on cloud best practices.

---
This app is designed to simplify the tedious process of maintaining and updating cloud infrastructure documentation, making it faster and more efficient.
''')

# Initialize session states
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "waiting_for_answer" not in st.session_state:
    st.session_state.waiting_for_answer = True

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# Function to invoke the Bedrock agent
def invoke_agent(agent_id, agent_alias_id, session_id, prompt):
    try:
        bedrock_agent_runtime = boto3.client(
            "bedrock-agent-runtime", region_name="us-east-1"
        )
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=prompt,
        )
        completion = ""
        for event in response.get("completion", []):
            chunk = event["chunk"]
            completion += chunk["bytes"].decode()
    except Exception as e:
        st.error(f"Error invoking agent: {e}")
        completion = "Sorry, an error occurred while processing your query."
    return completion

# Function to process user query and update history
def process_query(query):
    if query.strip():  # Only process if query is not empty
        agent_id = "ABCDEFGHIJ"  # Replace with your Bedrock agent ID
        agent_alias_id = "HIJKLMNOPQR"  # Replace with your Bedrock agent alias ID
        session_id = st.session_state.session_id
        response = invoke_agent(agent_id, agent_alias_id, session_id, query)
        
        # Add to chat history
        st.session_state.chat_history.append({"query": query, "response": response})
        st.session_state.waiting_for_answer = True
        st.session_state.user_input = ""  # Clear the input after processing
        return response
    return None

# Display chat history
def display_chat_history():
    for item in st.session_state.chat_history:
        with st.container():
            st.markdown("**🔵 Query:**")
            st.write(item["query"])
            st.markdown("**🤖 Response:**")
            st.write(item["response"])
            st.markdown("---")

# Sample questions section
with st.expander("Sample Questions", expanded=True):
    col1, col2 = st.columns(2)
    # First row
    if col1.button(SAMPLE_QUESTIONS[0], key="q1", use_container_width=True):
        st.session_state.user_input = SAMPLE_QUESTIONS[0]
    if col2.button(SAMPLE_QUESTIONS[1], key="q2", use_container_width=True):
        st.session_state.user_input = SAMPLE_QUESTIONS[1]
    # Second row
    if col1.button(SAMPLE_QUESTIONS[2], key="q3", use_container_width=True):
        st.session_state.user_input = SAMPLE_QUESTIONS[2]
    if col2.button(SAMPLE_QUESTIONS[3], key="q4", use_container_width=True):
        st.session_state.user_input = SAMPLE_QUESTIONS[3]

# Display chat history if it exists
if st.session_state.chat_history:
    st.markdown("### Conversation History")
    display_chat_history()

# Create a form for input and submit button
with st.form(key='query_form', clear_on_submit=False):
    user_input = st.text_input("Submit your infra related query:", 
                              value=st.session_state.user_input,
                              key=f"user_input_{len(st.session_state.chat_history)}")
    submit_button = st.form_submit_button("Submit")
    
    if submit_button and user_input:
        process_query(user_input)
        st.rerun()

# Add clear history button in sidebar
if st.sidebar.button("Clear Chat History"):
    st.session_state.chat_history = []
    st.session_state.waiting_for_answer = True
    st.session_state.user_input = ""
    st.rerun()