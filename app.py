import streamlit as st
from groq import Groq
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr
import os
import tempfile
import asyncio
import edge_tts
from claude_responses import SYSTEM_PROMPT

# Page configuration
st.set_page_config(
    page_title="Ashit's Voice Bot",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #667eea;
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2em;
        margin-top: 0;
        margin-bottom: 2em;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .user-message {
        background-color: #082f63;
        border-left: 4px solid #061942;
    }
    .bot-message {
        background-color: #3b0373;
        border-left: 4px solid #764ba2;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: black;
        border: none;
        padding: 1rem 2rem;
        font-size: 1.2em;
        font-weight: bold;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .stButton>button:disabled {
        background: #cccccc;
        cursor: not-allowed;
        transform: none;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'groq_client' not in st.session_state:
    # Get API key from secrets or environment
    api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
    if api_key:
        st.session_state.groq_client = Groq(api_key=api_key)
    else:
        st.session_state.groq_client = None
if 'last_audio' not in st.session_state:
    st.session_state.last_audio = None
if 'conversation_count' not in st.session_state:
    st.session_state.conversation_count = 0

# Functions
def speech_to_text(audio_bytes):
    """Convert audio bytes to text using speech recognition"""
    try:
        recognizer = sr.Recognizer()
        
        # Save audio bytes to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name
        
        # Load audio file
        with sr.AudioFile(tmp_file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
        
        # Clean up temporary file
        os.unlink(tmp_file_path)
        
        return text
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand the audio. Please try again."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"
    except Exception as e:
        return f"Error processing audio: {e}"

def get_claude_response(user_message):
    """Get response from Groq API with Ashit's personality"""
    try:
        if not st.session_state.groq_client:
            return "API key not configured. Please add GROQ_API_KEY to Streamlit secrets."
        
        # Build conversation history for context
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add recent chat history (last 5 exchanges for context)
        recent_history = st.session_state.chat_history[-10:] if len(st.session_state.chat_history) > 10 else st.session_state.chat_history
        for chat in recent_history:
            messages.append({
                "role": "user" if chat['role'] == 'user' else "assistant",
                "content": chat['message']
            })
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Call Groq API
        response = st.session_state.groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            top_p=0.9
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error getting response: {e}"


def text_to_speech(text):
    """Convert text to speech using Microsoft Edge TTS with Indian male voice"""
    try:
        # Use Indian English male voice
        voice = "en-GB-RyanNeural"

        async def _generate():
            # Create a temporary file to save the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_path = tmp_file.name
            
            # Generate speech and save to temp file
            communicate = edge_tts.Communicate(text, voice=voice)
            await communicate.save(tmp_path)
            
            # Read the audio data
            with open(tmp_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            return audio_data

        # Run the async function
        return asyncio.run(_generate())

    except Exception as e:
        st.error(f"Error generating speech: {e}")
        return None


def display_chat_history():
    """Display the chat history"""
    for idx, chat in enumerate(st.session_state.chat_history):
        if chat['role'] == 'user':
            st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {chat['message']}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>Ashit:</strong> {chat['message']}
                </div>
            """, unsafe_allow_html=True)
            
            # Add audio playback if available
            if 'audio' in chat and chat['audio']:
                st.audio(chat['audio'], format='audio/mp3')

# Main UI
def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 Ashit Voice Bot</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ask me about myself! I\'m Ashit, an AI assistant.</p>', unsafe_allow_html=True)
    
    # Sidebar with instructions
    with st.sidebar:
        st.header("📋 How to Use")
        st.markdown("""
        1. **Click** the microphone button below
        2. **Speak** your question clearly
        3. **Click** "Process Recording"
        4. **Listen** to my audio answer
        5. **Repeat** for more questions!
        
        ---
        
        ### 💡 Sample Questions:
        - What should we know about your life story?
        - What's your #1 superpower?
        - What are the top 3 areas you'd like to grow in?
        - What misconception do people have about you?
        - How do you push your boundaries?
        
        ---
        
        ### 📊 Conversation Stats
        """)
        
        st.metric("Messages Exchanged", len(st.session_state.chat_history))
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        
        # Option to type instead of speak
        use_text_input = st.checkbox("Type instead of speaking", value=False)
        
        # Clear chat history button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.session_state.last_audio = None
            st.session_state.conversation_count = 0
            st.rerun()
    
    # Main content area
    st.markdown("---")
    
    # Chat history display
    if st.session_state.chat_history:
        st.subheader("💬 Conversation History")
        display_chat_history()
        st.markdown("---")
    else:
        st.info("👋 Start a conversation by recording your voice or typing a question!")
    
    # Input method: Voice or Text
    if use_text_input:
        # Text input mode
        st.subheader("✍️ Type Your Question")
        
        # Use a form for better UX
        with st.form(key="text_form", clear_on_submit=True):
            user_input = st.text_area(
                "Your question:", 
                key="text_input", 
                placeholder="Type your question here...",
                height=100
            )
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit_button = st.form_submit_button("Send 📤", use_container_width=True)
        
        if submit_button and user_input:
            with st.spinner("🤔 Thinking..."):
                # Get response
                response = get_claude_response(user_input)
                
                with st.spinner("🔊 Generating voice..."):
                    # Generate speech
                    audio_bytes = text_to_speech(response)
                
                # Add to chat history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'message': user_input
                })
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'message': response,
                    'audio': audio_bytes
                })
                
                st.session_state.conversation_count += 1
                st.rerun()
    else:
        # Voice input mode
        st.subheader("🎤 Speak Your Question")
        
        # Instructions
        st.info("👇 Click the microphone to record, then click 'Process Recording' to get a response")
        
        # Audio recorder
        audio_bytes = audio_recorder(
            text="Click to record",
            recording_color="#e74c3c",
            neutral_color="#667eea",
            icon_name="microphone",
            icon_size="3x",
            key=f"audio_recorder_{st.session_state.conversation_count}"
        )
        
        # Check if new audio is recorded
        if audio_bytes:
            if audio_bytes != st.session_state.last_audio:
                st.session_state.last_audio = audio_bytes
                st.success("✅ Recording captured! Click 'Process Recording' below.")
            st.audio(audio_bytes, format="audio/wav")
        
        # Process button - always visible
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            process_clicked = st.button(
                "🔄 Process Recording", 
                disabled=not audio_bytes, 
                use_container_width=True,
                type="primary"
            )
        
        if process_clicked and audio_bytes:
            with st.spinner("🎧 Processing your voice..."):
                # Convert speech to text
                user_message = speech_to_text(audio_bytes)
                
                if user_message and not user_message.startswith("Sorry") and not user_message.startswith("Error"):
                    st.success(f"📝 You said: **{user_message}**")
                    
                    with st.spinner("🤔 Getting Ashit's response..."):
                        # Get response from Ashit
                        response = get_claude_response(user_message)
                        
                        with st.spinner("🔊 Generating voice..."):
                            # Convert response to speech
                            response_audio = text_to_speech(response)
                        
                        # Add to chat history
                        st.session_state.chat_history.append({
                            'role': 'user',
                            'message': user_message
                        })
                        st.session_state.chat_history.append({
                            'role': 'assistant',
                            'message': response,
                            'audio': response_audio
                        })
                        
                        # Reset last audio to allow new recording
                        st.session_state.last_audio = None
                        st.session_state.conversation_count += 1
                        
                        st.rerun()
                else:
                    st.error(f"❌ {user_message}")
        
        # Show help text
        st.markdown("---")
        st.markdown("""
            <div style='text-align: center; color: #888; font-size: 0.9em; padding: 1rem; background-color: #f8f9fa; border-radius: 10px;'>
                💡 <strong>Tip:</strong> After each response, click the microphone again to ask another question!<br>
                🔄 The conversation remembers context from previous messages.
            </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            <p>Built with Streamlit • Powered by Groq • Voice by Microsoft Edge TTS (Indian Male)</p>
            <p>This is a demonstration of Ashit's personality in a voice interface</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()