import cv2
import time
import threading
import queue
import os
import speech_recognition as sr
import pyttsx3
from deepface import DeepFace

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Queues for thread communication
frame_queue = queue.Queue(maxsize=2)
result_queue = queue.Queue()
speech_queue = queue.Queue()
response_queue = queue.Queue()
running = True

# FPS calculation variables
fps_counter = 0
fps_start_time = time.time()
current_fps = 0

# Initialize speech recognition and text-to-speech engines
recognizer = sr.Recognizer()
engine = pyttsx3.init()

def analyze_frame():
    """Worker thread function for emotion analysis"""
    global running
    
    while running:
        try:
            if not frame_queue.empty():
                frame = frame_queue.get()
                
                # Analyze with enhanced parameters
                results = DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True
                )
                
                # Put results in queue
                result_queue.put(results)
                
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            result_queue.put(None)
            
        time.sleep(0.01)

def listen_for_speech():
    """Worker thread function for speech recognition"""
    global running
    
    # Use the default microphone as the audio source
    with sr.Microphone() as source:
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source)
        print("Voice recognition active. Speak clearly to interact.")
        
        while running:
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                # Convert speech to text
                text = recognizer.recognize_google(audio)
                print(f"Recognized: {text}")
                
                # Put recognized text in queue
                speech_queue.put(text)
                
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Speech recognition service error: {e}")
            except Exception as e:
                print(f"Speech recognition error: {e}")
            
            time.sleep(0.1)

def process_speech():
    """Worker thread to process recognized speech and generate responses"""
    global running
    
    last_emotion = None
    last_response_time = 0
    cooldown_period = 5  # Seconds between responses
    
    while running:
        try:
            # Check for new recognized speech
            if not speech_queue.empty():
                text = speech_queue.get()
                text_lower = text.lower()
                
                current_time = time.time()
                # Only respond if it's been more than the cooldown period
                if current_time - last_response_time >= cooldown_period:
                    
                    # Process commands based on recognized text
                    if "hello" in text_lower or "hi" in text_lower:
                        response = "Hello! I am your emotion recognition assistant."
                    elif "how are you" in text_lower:
                        response = "I'm functioning properly, thank you for asking."
                    elif "what do you see" in text_lower:
                        if last_emotion:
                            response = f"I can see that you appear to be {last_emotion}."
                        else:
                            response = "I don't detect any emotions at the moment."
                    elif "goodbye" in text_lower or "bye" in text_lower:
                        response = "Goodbye! Have a nice day."
                    elif "quit" in text_lower or "exit" in text_lower:
                        response = "Shutting down the application."
                        response_queue.put(response)
                        running = False
                        break
                    else:
                        # Echo what was heard
                        response = f"I heard you say: {text}"
                    
                    # Put response in queue
                    response_queue.put(response)
                    last_response_time = current_time
            
            # Update last detected emotion for reference
            if not result_queue.empty():
                results = result_queue.get()
                if results and isinstance(results, list) and len(results) > 0:
                    last_emotion = results[0].get('dominant_emotion', 'unknown')
            
        except Exception as e:
            print(f"Speech processing error: {e}")
            
        time.sleep(0.1)

def speak_responses():
    """Worker thread to speak responses using text-to-speech"""
    global running
    
    while running:
        try:
            if not response_queue.empty():
                response = response_queue.get()
                
                # Use text-to-speech to speak the response
                engine.say(response)
                engine.runAndWait()
                
        except Exception as e:
            print(f"Text-to-speech error: {e}")
            
        time.sleep(0.1)

def main():
    global running, fps_counter, fps_start_time, current_fps
    
    # Initialize webcam with DirectShow backend
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print("Error: Could not open video device")
        return
    
    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Start worker threads
    worker_threads = [
        threading.Thread(target=analyze_frame, daemon=True),
        threading.Thread(target=listen_for_speech, daemon=True),
        threading.Thread(target=process_speech, daemon=True),
        threading.Thread(target=speak_responses, daemon=True)
    ]
    
    for thread in worker_threads:
        thread.start()
    
    last_results = None
    last_recognized_text = ""
    
    while running:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            break
        
        # Update FPS counter
        fps_counter += 1
        current_time = time.time()
        time_diff = current_time - fps_start_time
        
        # Update FPS every second
        if time_diff >= 1.0:
            current_fps = round(fps_counter / time_diff, 1)
            fps_counter = 0
            fps_start_time = current_time
        
        # Convert to RGB for analysis and put in queue if not full
        if frame_queue.qsize() < frame_queue.maxsize:
            analysis_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                frame_queue.put_nowait(analysis_frame)
            except queue.Full:
                pass
        
        # Check for new results
        try:
            if not result_queue.empty():
                last_results = result_queue.get_nowait()
        except queue.Empty:
            pass
        
        # Process latest results if available
        if last_results and isinstance(last_results, list):
            for face in last_results:
                # Extract face region with safety checks
                region = face.get('region', {})
                x = region.get('x', 0)
                y = region.get('y', 0)
                w = region.get('w', 0)
                h = region.get('h', 0)
                
                if w > 0 and h > 0:
                    emotion = face.get('dominant_emotion', 'Unknown').capitalize()
                    
                    # Draw annotations
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, emotion, (x, y-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Check for new recognized speech
        try:
            if not speech_queue.empty():
                # Peek at the speech queue without removing the item
                speech_queue_list = list(speech_queue.queue)
                if speech_queue_list:
                    last_recognized_text = speech_queue_list[-1]
        except Exception:
            pass
        
        # Display FPS
        cv2.putText(frame, f"FPS: {current_fps}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display recognized text
        if last_recognized_text:
            cv2.putText(frame, f"You said: {last_recognized_text}", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Emotion Recognition with Voice", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    running = False
    print("Shutting down threads...")
    
    for thread in worker_threads:
        if thread.is_alive():
            thread.join(timeout=1.0)
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Inform user about required packages
    try:
        import speech_recognition
        import pyttsx3
    except ImportError:
        print("Required packages not found. Please install:")
        print("pip install SpeechRecognition pyttsx3 pyaudio")
        exit(1)
    
    main()