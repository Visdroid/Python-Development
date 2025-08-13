from typing import Optional, Tuple
from pathlib import Path
import logging
import tempfile
import wave
import speech_recognition as sr
from pydub import AudioSegment
import numpy as np

logger = logging.getLogger(__name__)

class AudioService:
    """
    Service for audio processing including recording, validation, and speech-to-text conversion.
    Handles multiple audio formats and provides robust error handling.
    """
    
    def __init__(self, sample_rate: int = 16000, max_duration: int = 300):
        """
        Initialize audio service with configurable parameters.
        
        Args:
            sample_rate: Target sample rate in Hz (default: 16000)
            max_duration: Maximum allowed audio duration in seconds (default: 300)
        """
        self.recognizer = sr.Recognizer()
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        
        # Configure recognizer
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        logger.info(
            f"AudioService initialized with sample_rate={sample_rate}, "
            f"max_duration={max_duration}"
        )

    def validate_audio(self, audio_path: Path) -> Tuple[bool, str]:
        """
        Validate audio file before processing.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with wave.open(str(audio_path), 'rb') as wav:
                if wav.getnframes() == 0:
                    return False, "Empty audio file"
                
                duration = wav.getnframes() / float(wav.getframerate())
                if duration > self.max_duration:
                    return False, f"Audio exceeds maximum duration ({duration:.1f}s > {self.max_duration}s)"
                
                return True, ""
        except Exception as e:
            return False, f"Invalid audio file: {str(e)}"

    def convert_to_wav(self, input_path: Path, output_path: Path) -> bool:
        """
        Convert any audio format to standardized WAV format.
        
        Args:
            input_path: Source audio file path
            output_path: Destination WAV file path
            
        Returns:
            True if conversion succeeded, False otherwise
        """
        try:
            audio = AudioSegment.from_file(str(input_path))
            
            # Standardize audio format
            audio = audio.set_frame_rate(self.sample_rate)
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.normalize()  # Normalize volume
            
            audio.export(str(output_path), format="wav")
            return True
        except Exception as e:
            logger.error(f"Audio conversion failed: {str(e)}")
            return False

    def process_audio(self, audio_path: Path) -> Optional[str]:
        """
        Process audio file and convert to text using speech recognition.
        
        Args:
            audio_path: Path to audio file (any supported format)
            
        Returns:
            Transcribed text or None if processing failed
        """
        temp_wav = None
        try:
            # Convert to WAV if needed
            if audio_path.suffix.lower() != '.wav':
                temp_wav = Path(tempfile.mktemp(suffix='.wav'))
                if not self.convert_to_wav(audio_path, temp_wav):
                    return None
                audio_path = temp_wav

            # Validate audio file
            is_valid, message = self.validate_audio(audio_path)
            if not is_valid:
                logger.error(f"Invalid audio: {message}")
                return None

            # Process with speech recognition
            with sr.AudioFile(str(audio_path)) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(
                    audio_data,
                    language="en-ZA",  # South African English
                    show_all=False
                )
                logger.info(f"Successfully processed audio: {audio_path}")
                return text.strip()
                
        except sr.UnknownValueError:
            logger.error("Speech recognition could not understand audio")
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error processing audio: {str(e)}", exc_info=True)
        finally:
            # Clean up temporary files
            if temp_wav and temp_wav.exists():
                try:
                    temp_wav.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete temp file: {str(e)}")
        
        return None