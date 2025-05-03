from gtts import gTTS
import os

def text_to_speech(text, lang='en', output_file="output.mp3"):
    """
    Convert text to speech using gTTS and save it as an MP3 file.
    
    Parameters:
    text (str): The text to convert to speech.
    lang (str): The language for the speech. Default is English ('en').
    
    """
    # Create a gTTS object, specifying the text and language
    tts = gTTS(text=text, lang=lang)
    
    # Save the generated speech to an MP3 file
    # if file exists, remove it
    if os.path.exists(output_file):
        os.remove(output_file)

    tts.save(output_file)

    return output_file
 

def play_audio(file_path):
    """
    Play the audio file using the default system player.
    
    Parameters:
    file_path (str): The path to the audio file to play.
    
    """
    # wait for a second to ensure the audio is played
    import time
    time.sleep(1)
    # optionally, you can use a library like playsound or pydub for more control over audio playback
    from playsound import playsound
    playsound(file_path)
