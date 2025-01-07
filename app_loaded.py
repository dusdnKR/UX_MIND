import cv2
from flask import Flask, Response, render_template, request
import io
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler
import torch
from controlnet_aux import OpenposeDetector
import atexit
import numpy as np
from deepface import DeepFace
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import json
import mne
import matplotlib.pyplot as plt
import scipy
from flask_cors import CORS
import torch
from flask import Flask, Response, render_template, stream_with_context
import time
from mne import create_info
from scipy import signal
import pickle
from joblib import load
import matplotlib as mpl
from PIL import Image
import matplotlib.cm as cm
from PyQt5 import QtWidgets
import math
import pylsl
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from typing import List
from pylsl import StreamInlet, resolve_stream
import warnings
import os
from utils.wrapper import StreamDiffusionWrapper
import threading
warnings.filterwarnings(action='ignore')

# Flask 애플리케이션 생성
app = Flask(__name__)
CORS(app)

# 웹캠 비디오 캡처 객체 생성
cap = cv2.VideoCapture(0)

########################################🌟 MNE TOPOLOGY ###################################

# Generate MNE topomaps
def generate_mne():
    global concatenated_data, info

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(7, 4), facecolor='none')
    ax = fig.add_subplot(111)


    vmax = 20
    vmin = -20
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    colormapping = cm.ScalarMappable(norm=norm, cmap='jet') #, cmap=cmap

    buffer_size = 1
    eeg_buffer = np.zeros((14, buffer_size))

    time_step = 0
    cb = fig.colorbar(colormapping, ax=plt.gca(), location='right', pad=0.04)
    
    while True:
        if time_step >= concatenated_data.shape[1]:
            time_step = 0

        ax.clear()

        mne.viz.plot_topomap(
            concatenated_data[:32, time_step],
            info,
            vlim=(vmin, vmax),
            axes=ax,
            show=False,
            outlines='head',
            cmap='jet',
            sensors=False,
            contours=0
        )

        canvas = FigureCanvas(fig)
        buf = io.BytesIO()
        canvas.print_png(buf)
        buf.seek(0)

        time_step += 1
        
        yield (b'--frame\r\n'
            b'Content-Type: image/png\r\n\r\n' + buf.read() + b'\r\n')


# Route to display MNE topomaps
@app.route('/mne_feed_model')
def mne_feed_model():
    #info, inlet = load_realtime_eeg_data()
    response = Response(generate_mne(), mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    
    return response

@app.route('/mne_feed')
def mne_feed():
    return render_template('mne_feed.html')

########################################🌟 EEG PLOT ###################################
def load_eeg_data():
    mat_file = "./datas/s01.mat"
    mat = scipy.io.loadmat(mat_file)
    data = mat["data"][0, :, 384:]
    sfreq = 128
    ch_names = [
    "Fp1", "AF3", "F3", "F7", "FC5", "FC1", "C3", "T7", "CP5", "CP1",
    "P3", "P7", "PO3", "O1", "Oz", "Pz", "Fp2", "AF4", "Fz", "F4",
    "F8", "FC6", "FC2", "Cz", "C4", "T8", "CP6", "CP2", "P4", "P8",
    "PO4", "O2", "hEOG", "vEOG", "zEMG", "tEMG", "GSR", "Respiration belt", "Plethysmograph", "Temperature"]

    info = mne.create_info(
        ch_names,
        sfreq,
        ch_types=["eeg"] * 32
        + ["eog"] * 2
        + ["emg"] * 2
        + ["gsr"] * 1
        + ["resp"] * 1
        + ["misc"] * 1
        + ["temperature"] * 1,
    )

    info.set_montage("standard_1020")
    info["description"] = "SO1 subject"

    concatenated_data = data
    return info, concatenated_data


def pull_data(concatenated_data, time_step):
    sample = concatenated_data[:, time_step] * 1e4

    return sample


def generate_data():
    global concatenated_data
    time_step = 0

    while True:
        sample = pull_data(concatenated_data, time_step).tolist()
        time_step += 1
        json_data = json.dumps({"time": time_step, "value": sample})

        yield f"data:{json_data}\n\n"
        time.sleep(0.03)

        if time_step > concatenated_data.shape[1]:
            time_step = 0

@app.route("/eeg_feed_model")
def eeg_feed_model():
    response = Response(
        stream_with_context(generate_data()),
        mimetype="text/event-stream",
    )
    
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"

    return response


@app.route("/eeg_feed")
def eeg_feed():
    return render_template("eeg_feed.html")


########################################🌟 ATTENTION PLOT ###################################

# Define constants
CHANNEL_NAMES = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']
SFREQ = 128
BAND_PASS_LOW = 0.16
TIME_WINDOW = 1

select_ch = ['F7', 'F3', 'AF4', 'P7', 'P8', 'O1', 'O2']
use_channel_inds = []
diff_focus = "focus" 

# Apply a Butterworth high-pass filter
def butter_highpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
    return b, a

# Apply a high-pass filter to EEG data
def butter_highpass_filter(data, cutoff, fs, order=5):
    b, a = butter_highpass(cutoff, fs, order=order)
    x = signal.filtfilt(b, a, data)
    y = signal.filtfilt(b, a, x)
    return y

# Extract features from EEG data
def extract_features(concatenated_eeg, time_window, time_points, window_blackman):
    col = len(select_ch) #7
    power_eeg = {}
    bin_eeg = {}
    bin_eeg_avg = {}
    knn_focus ={}

    power_eeg['data']=np.zeros([7, 513, time_window+1])
    bin_eeg['data']=np.zeros([7, 36, time_window+1])
    bin_eeg_avg['data']=np.zeros([7, 36, 1])
    knn_focus['data']=np.zeros([252,1])

    if concatenated_eeg.shape[0] < time_points:
        original_array = np.random.rand(concatenated_eeg.shape[0],7)
        additional_values = np.random.rand(time_points - concatenated_eeg.shape[0], 7)
        concatenated_eeg = np.concatenate((original_array, additional_values))

    else:
        pass
    
    for i in range(col):
        concatenated_eeg[:,i] = butter_highpass_filter(concatenated_eeg[:,i], 0.16, 128, 5)
        f, t, y1=scipy.signal.stft(concatenated_eeg[:,i],fs=128, window=window_blackman, nperseg=128, 
                      noverlap=0, nfft=1024, detrend=False,return_onesided=True, boundary='zeros',
                      padded=True)
        
        power_eeg['data'][i,:, :]=(np.abs(y1))**2
        
    for chn in range(col):
        j=0
        for i in range(1,144,4):
            bin_eeg['data'][chn,j,:]=np.average(power_eeg['data'][chn,i:i+4,:],axis=0)
            j+=1

    for chn in range(col):
        j=0
        for k in range(0,1):
            bin_eeg_avg['data'][chn,:,j]=np.average(bin_eeg['data'][chn,:,k:k+(601-time_window+1)],axis=1)
            j += 1

    for j in range(1):      
        knn_focus['data'][:,j]=bin_eeg_avg['data'][:,:,j].reshape(1,-1)

    knn_focus['data'] = 10*np.log(knn_focus['data'])
    if time_window == 15:
        loaded_scaler = load('./models/scaler_knn.joblib')
        with open('./models/saved_model', 'rb') as f:
            mod = pickle.load(f)

    elif time_window == 5:
        loaded_scaler = load('./models/scaler_knn_5second.joblib')
        with open('./models/saved_model_5second', 'rb') as f:
            mod = pickle.load(f)

    elif time_window == 10:
        loaded_scaler = load('./models/scaler_knn_10second.joblib')
        with open('./models/saved_model_10second', 'rb') as f:
            mod = pickle.load(f)

    elif time_window == 1:
        loaded_scaler = load('./models/scaler_knn_1second.joblib')
        with open('./models/saved_model_1second', 'rb') as f:
            mod = pickle.load(f)

    return knn_focus['data'].T,loaded_scaler, mod

def get_attention():
    global concatenated_data, focus
    time_step = 0
    time_points = TIME_WINDOW * SFREQ
    t_win = np.arange(0, 128)
    buffer_size = 1
    M = 12
    window_blackman = 0.42 - 0.5 * np.cos((2 * np.pi * t_win) / (M - 1)) + 0.08 * np.cos((4 * np.pi * t_win) / (M - 1))

    while True:
        if time_step > concatenated_data.shape[1]:
            time_step = 0

        samples = concatenated_data[:, time_step:time_step + time_points]
        time_step += time_points

        samples = np.array([row for row in samples]).T
        realtime_data = samples[use_channel_inds, :]

        realtime_data, loaded_scaler, mod = extract_features(realtime_data.T, TIME_WINDOW, time_points, window_blackman)
        realtime_data_scaled = loaded_scaler.transform(realtime_data)
        
        value = mod.predict(realtime_data_scaled)[0]
        focus = "focus" if value == 0 else ("unfocus" if value == 1 else ("drowsy" if value == 2 else "unknown"))

        yield f"data: {value}\n\n"
        
        time.sleep(0.5)  # Pause for 0.5 seconds before the next update

@app.route('/attention_feed_model')
def attention_feed_model():
    response = Response(stream_with_context(get_attention()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"

    return response

@app.route('/attention_feed')
def attention_feed():
    return render_template('attention_feed.html')


########################################🌟 DIFFUSION MODEL ###################################
cmd = "Character"

def generate_images(openpose, pipe):
    global cmd, diff_focus, diff_emotion
    success = True
    
    focus_cmd = "strongly"
    emotion_cmd  = "happy"

    while success:
        if diff_focus == "drowsy" or diff_focus == "unfocus":
            focus_cmd = "drowsy"        
        else:
            focus_cmd = "strongly"

        emotion_cmd = diff_emotion
        ret, frame = cap.read()

        pose_img = openpose(frame)

        image_output = pipe(f"{focus_cmd} + ' ' + {emotion_cmd}, beautiful, highly insanely detailed, top quality, best quality, 4k, 8k, art single girl character, art like, very high quality",
                            pose_img,
                            negative_prompt="normal quality, low quality, worst quality, jpeg artifacts, chinese, username, watermark, signature, time signature,\
                                            timestamp, artist name, copyright name, copyright, loli, child, infant, baby, bad anatomy, extra hands, extra legs, extra digits, \
                                            extra_fingers, wrong finger, inaccurate limb, African American, African, tits, nipple, pubic hair",
                            num_inference_steps=2).images[0]
        combined_img = np.concatenate((pose_img, image_output), axis=1)
        combined_pil_img = Image.fromarray(combined_img)

        img_byte_array = io.BytesIO()
        combined_pil_img.save(img_byte_array, format='JPEG')
        img_bytes = img_byte_array.getbuffer()

        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')

@app.route('/diffusion_feed_model', methods=['GET'])
def diffusion_feed_model():
    # OpenPose 모델 및 Diffusion 초기화
    openpose = OpenposeDetector.from_pretrained('lllyasviel/ControlNet')
    controlnet = ControlNetModel.from_pretrained("lllyasviel/control_v11p_sd15_openpose", torch_dtype=torch.float16)
    pipe = StableDiffusionControlNetPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", controlnet=controlnet, safety_checker=None, torch_dtype=torch.float16)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload(gpu_id=0)
    pipe.enable_xformers_memory_efficient_attention()

    response = Response(generate_images(openpose, pipe), mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"

    return response

@app.route('/diffusion_feed')
def diffusion_feed():
    return render_template('diffusion_feed.html')


########################################🌟 CAMERA THREAD ###################################

cap = None  # 웹캠 캡처 객체

def start_camera():
    """웹캠 캡처를 별도의 스레드에서 실행"""
    global cap
    cap = cv2.VideoCapture(0)  # 웹캠 열기
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

# 웹캠 캡처 스레드 시작
camera_thread = threading.Thread(target=start_camera)
camera_thread.daemon = True
camera_thread.start()

########################################🌟 STREAMDIFFUSION MODEL ###################################

def generate_streamdiffusion_images(stream):
    global diff_focus, diff_emotion

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save frame to temporary file
        temp_input_path = "temp_input.png"
        cv2.imwrite(temp_input_path, frame)

        # 사용자 상태 기반으로 prompt 생성 ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
        focus_cmd = "drowsy" if diff_focus in ["drowsy", "unfocus"] else "strongly focused"
        emotion_cmd = diff_emotion if diff_emotion else "neutral"
        if emotion_cmd in ["angry"]:
            dynamic_prompt = f"{focus_cmd}, {emotion_cmd}, Portrait of The Joker halloween costume, {emotion_cmd} face painting, beautiful, highly insanely detailed, top quality, best quality, 4k, 8k, art single girl character, art like, very high quality"
        elif emotion_cmd in ["disgust"]:
            dynamic_prompt = f"{focus_cmd}, {emotion_cmd}, Portrait of The green {emotion_cmd} face costume, face painting, highly insanely detailed, top quality, best quality, 4k, 8k, art single {emotion_cmd} girl character, art like, very high quality"
        elif emotion_cmd in ["fear"]:
            dynamic_prompt = f"{focus_cmd}, {emotion_cmd}, Portrait of The Scream of Nature, face painting, highly insanely detailed, top quality, best quality, 4k, 8k, art single {emotion_cmd} girl character, art like, very high quality"
        elif emotion_cmd in ["happy", "surprise", "neutral"]:
            dynamic_prompt = f"{focus_cmd}, {emotion_cmd}, beautiful, highly insanely detailed, top quality, best quality, 4k, 8k, art single {emotion_cmd} girl character, art like, very high quality"
        elif emotion_cmd in ["sad"]:
            dynamic_prompt = f"{focus_cmd}, {emotion_cmd}, Portrait of the sad person, crying, blue, tears, beautiful, highly insanely detailed, top quality, best quality, 4k, 8k, art single {emotion_cmd} girl character, art like, very high quality"


        # StreamDiffusionWrapper를 호출하여 결과 생성
        output_image = stream(image=temp_input_path, prompt=dynamic_prompt)

        # Convert PIL image to OpenCV format
        output_image_cv = cv2.cvtColor(np.array(output_image), cv2.COLOR_RGB2BGR)

        # Convert OpenCV image to JPEG
        _, buffer = cv2.imencode('.jpg', output_image_cv)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        # Clean up temporary file
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

@app.route('/streamdiffusion_feed_model', methods=['GET'])
def streamdiffusion_feed_model():
    global diff_focus, diff_emotion

    # Prepare StreamDiffusionWrapper
    stream = StreamDiffusionWrapper(
        model_id_or_path="stabilityai/sd-turbo",
        t_index_list=[27],
        frame_buffer_size=1,
        width=720,
        height=480,
        warmup=10,
        acceleration="xformers",
        mode="img2img",
        use_denoising_batch=True,
        cfg_type="self",
        seed=123,
    )
    stream.prepare(
        prompt="",
        negative_prompt="normal quality, low quality, worst quality, jpeg artifacts, chinese, username, watermark, signature, time signature,\
                         timestamp, artist name, copyright name, copyright, loli, child, infant, baby, bad anatomy, extra hands, extra legs, extra digits, \
                         extra_fingers, wrong finger, inaccurate limb, African American, African, tits, nipple, pubic hair",
        num_inference_steps=50,
        guidance_scale=1.0,
        delta=1.0,
    )

    if cap is None or not cap.isOpened():
        return "Error: Could not open webcam."

    return Response(generate_streamdiffusion_images(stream), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/streamdiffusion_feed')
def streamdiffusion_feed():
    return render_template('streamdiffusion_feed.html')

########################################🌟 EMOTION RECOGNITION ###################################

diff_emotion = "happy"
emotions = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

@app.route('/emotion_feed_model')
def emotion_feed_model():
    def generate_emotion_data():
        global diff_emotion
        success = True

        while success:
            success, frame = cap.read()
            if success:
                # Perform emotion analysis
                predictions = DeepFace.analyze(frame, actions=['emotion'], detector_backend="opencv", enforce_detection=False, silent=True)
                emotion_data = predictions[0]['emotion']
                probabilities = [emotion_data[emotion] for emotion in emotions]

                max_probability_index = probabilities.index(max(probabilities))
                max_emotion = emotions[max_probability_index]

                diff_emotion = max_emotion
                # Create JSON data to send to the front-end
                json_data = json.dumps({'emotions': emotions, 'probabilities': probabilities})
                yield f"data:{json_data}\n\n"

    response = Response(generate_emotion_data(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.route('/emotion_feed')
def emotion_feed():
    return render_template('emotion_feed.html')

########################################🌟 POSE ESTIMATION ###################################

# def generate_frames(faceCascade):
#     while True:
#         success, frame = cap.read()
#         if success:
#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#             faces = faceCascade.detectMultiScale(gray, 1.1, 5)
#             for (x,y,w,h) in faces:
#                 cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 4)

#             # 프레임을 바이트로 변환하여 스트리밍
#             ret, buffer = cv2.imencode('.jpg', frame)
#             if ret:
#                 frame_bytes = buffer.tobytes()
#                 yield (b'--frame\r\n'
#                     b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# @app.route('/face_feed_model')
# def face_feed_model():
#     faceCascade = cv2.CascadeClassifier("./models/haarcascade_frontalface_alt.xml")

#     response = Response(generate_frames(faceCascade), mimetype='multipart/x-mixed-replace; boundary=frame')
#     response.headers["Cache-Control"] = "no-cache"
#     response.headers["X-Accel-Buffering"] = "no"

#     return response

# @app.route('/face_feed')
# def face_feed():
#     return render_template('face_feed.html')

########################################🌟 VIDEO ###################################

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed_model():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed')
def video_feed():
    return render_template('video_feed.html')

###########################################################################################

@atexit.register
def release_capture():
    cap.release()

if __name__ == '__main__':
    info, concatenated_data = load_eeg_data()

    app.run(host='0.0.0.0', port='5000', debug=False)