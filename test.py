import streamlit as st
import PyPDF2
from dotenv import load_dotenv
from transformers import pipeline
from textblob import TextBlob
from gtts import gTTS
from pydub import AudioSegment
import tempfile
from langchain_groq import ChatGroq
from io import BytesIO
import os

# Load environment variables
load_dotenv()

# Set the path to the FFmpeg executable
AudioSegment.ffmpeg_path = r"C:/FFmpeg/ffmpeg.exe"

# Initialize GROQ chat model
def init_groq_model():
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")
    return ChatGroq(
        groq_api_key=groq_api_key, model_name="llama-3.1-70b-versatile", temperature=0.2
    )

llm_groq = init_groq_model()

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ''.join(page.extract_text() or "" for page in pdf_reader.pages)
        return text
    except Exception as e:
        st.error(f"Failed to extract text from PDF: {e}")
        return ""

def chunk_text(text, max_chunk_length=512):
    words = text.split()
    for i in range(0, len(words), max_chunk_length):
        yield ' '.join(words[i:i + max_chunk_length])

def summarize_text(text, max_length=150):
    summary = ""

    for chunk in chunk_text(text):
        chunk = chunk.strip()
        if len(chunk) == 0 or len(chunk.split()) < 5:
            continue

        try:
            response = llm_groq.generate(
                prompt=chunk, 
                max_length=max_length, 
                temperature=0.2
            )
            summary += response + " "
        except Exception as e:
            st.error(f"Error summarizing chunk with Llama: {e}")

    return summary.strip()

def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

def text_to_speech_gtts(text, sentiment_adjustment=False):
    if sentiment_adjustment:
        sentiment = analyze_sentiment(text)
        speech_rate = 1.0 if sentiment > 0 else 0.9
    else:
        speech_rate = 1.0

    # Save audio to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(tmp_file.name)  # Save the audio to the temp file
        return tmp_file.name  # Return the path to the saved audio file

def merge_audio_with_background(audio_file_path, background_music):
    if not (audio_file_path and background_music):
        raise ValueError("Both audio file and background music must be provided.")

    # Read the audio file directly from the file path
    speech = AudioSegment.from_file(audio_file_path, format="mp3")

    # Read the background music immediately
    background_data = background_music.read()  # Read the uploaded file
    background = AudioSegment.from_file(BytesIO(background_data), format="mp3")

    # Overlay the two audio segments
    combined = speech.overlay(background)

    # Save the combined audio to a temporary file
    temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    combined.export(temp_audio_path, format="mp3")

    return temp_audio_path  # Return the path to the saved audio file

# Streamlit application layout
st.title("Research Paper to Podcast Converter 🎙️")
st.write("Upload a research paper PDF, and we'll generate a podcast for you!")

uploaded_pdf = st.file_uploader("Choose a PDF file", type="pdf")
background_music = st.file_uploader("Upload background music (Optional)", type=["mp3"])
summarize = st.checkbox("Summarize the paper")
sentiment_adjustment = st.checkbox("Adjust voice tone based on sentiment")

if st.button("Generate Podcast"):
    if uploaded_pdf is not None:
        with st.spinner("Extracting text from PDF..."):
            pdf_text = extract_text_from_pdf(uploaded_pdf)

        if summarize:
            with st.spinner("Summarizing the content..."):
                pdf_text = summarize_text(pdf_text)

        with st.spinner("Generating podcast..."):
            audio_file_path = text_to_speech_gtts(pdf_text, sentiment_adjustment=sentiment_adjustment)

        if background_music:
            with st.spinner("Merging audio with background music..."):
                podcast_file = merge_audio_with_background(audio_file_path, background_music)
            st.success("Podcast generated!")
            st.audio(podcast_file)
        else:
            st.success("Podcast generated!")
            st.audio(audio_file_path)
