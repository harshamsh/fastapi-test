from fastapi import FastAPI, WebSocket
import uvicorn
import asyncio
from asyncio import create_task, sleep
import time
import math
import json
import random
import numpy as np
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print('WebSocket is listening at: ws://localhost:8000/ws')

def generate_oximeter_readings():
    return round(random.uniform(95, 99), 1)

def ppg_wave(time, heart_rate=72, amplitude=1):
    frequency = heart_rate / 60
    phase_shift = 0.6
    time = time % (1/frequency) * frequency

    sine_wave = amplitude * np.sin(2 * np.pi * frequency * (time - phase_shift))
    sine_wave = np.maximum(sine_wave, 0)

    notch_center = 0.5
    notch_width = 0.1
    notch_depth = 0.3
    gaussian_notch = notch_depth * np.exp(-((time - notch_center) ** 2) / (2 * notch_width ** 2))

    ppg_value = sine_wave - gaussian_notch
    return ppg_value

def sine_wave(time, frequency=1, amplitude=1, phase=0):
    return amplitude * math.sin(2 * math.pi * frequency * time + phase)

def cosine_wave(time, frequency=1, amplitude=1, phase=0):
    return amplitude * math.cos(2 * math.pi * frequency * time + phase)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data transfer.
    """
    await websocket.accept()
    print("WebSocket connection opened.")
    should_send = False  # Initialize the sending flag
    start_time = time.time()
    last_oximeter_time = start_time
    oximeter_interval = 1

    async def handle_incoming_messages():
        nonlocal should_send
        while True:
            text_data = await websocket.receive_text()  # Wait for a start/stop message from the client
            command = json.loads(text_data)

            if command.get("command") == "start_data_stream":
                should_send = True  # Start sending data
            elif command.get("command") == "stop_data_stream":
                should_send = False  # Stop sending data

    async def send_data():
        nonlocal should_send, start_time, last_oximeter_time, oximeter_interval
        while True:
            if should_send:
                current_time = time.time()
                elapsed_time = current_time - start_time

                sine_value = sine_wave(elapsed_time)
                cosine_value = cosine_wave(elapsed_time)
                pulse_oximetry_value = ppg_wave(elapsed_time)

                data = {
                    "time_stamp": elapsed_time,
                    "pulse_oximetry": pulse_oximetry_value,
                }

                if current_time - last_oximeter_time >= oximeter_interval:
                    oximeter_reading = generate_oximeter_readings()
                    data["oximeter"] = oximeter_reading
                    last_oximeter_time = current_time

                json_data = json.dumps(data)
                await websocket.send_text(json_data)
                print(json_data)
            await sleep(0.05)  # Add some sleep to not overload the CPU

    # Start the two tasks
    await asyncio.gather(
        create_task(handle_incoming_messages()),
        create_task(send_data()),
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
