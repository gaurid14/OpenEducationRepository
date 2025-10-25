import whisper

def transcribe_audio_or_video(state: dict) -> dict:
    """
    Transcribes audio/video files using free local Whisper model.
    """
    file_path = state["file_path"]

    # Load Whisper model (base is a good balance of speed & accuracy) but the web request is timing out so using a smaller,
    # faster model like "tiny" or "small". This will significantly reduce the transcription time and should allow the process
    # to finish before any timeouts occur.
    model = whisper.load_model("tiny")

    try:
        result = model.transcribe(file_path)
        state["transcript"] = result["text"]
    except Exception as e:
        state["transcript"] = f"Transcription failed: {e}"

    return state
