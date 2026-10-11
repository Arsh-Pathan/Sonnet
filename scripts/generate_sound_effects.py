import wave
import os
import numpy as np

def create_sound_file(filepath, wave_array, sample_rate=44100):
    audio_bytes = (np.clip(wave_array, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    with wave.open(filepath, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(audio_bytes)
    print(f"Generated: {filepath} ({len(audio_bytes)} bytes)")

def generate_all_sounds():
    out_dir = "assets/sounds"
    os.makedirs(out_dir, exist_ok=True)
    sr = 44100

    # 1. Sonar Ping (Hydroacoustic transducer ping)
    dur = 0.45
    t = np.linspace(0, dur, int(sr * dur), False)
    freq = np.linspace(900, 1300, len(t))
    env = np.exp(-6.5 * t)
    # Add subtle sub-harmonic resonance
    carrier = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * (freq * 0.5) * t)
    ping = carrier * env * 0.65
    create_sound_file(os.path.join(out_dir, "sonar_ping.wav"), ping, sr)

    # 2. Target Lock (Subtle tactical chirp)
    dur = 0.14
    t = np.linspace(0, dur, int(sr * dur), False)
    freq1 = np.linspace(1400, 1750, len(t))
    env = np.sin(np.pi * (t / dur)) ** 1.5 * np.exp(-4 * t)
    target = np.sin(2 * np.pi * freq1 * t) * env * 0.45
    create_sound_file(os.path.join(out_dir, "target_lock.wav"), target, sr)

    # 3. Threat Alarm (Dual-pulse hydrophone warning for naval mines)
    dur = 0.32
    t = np.linspace(0, dur, int(sr * dur), False)
    # Dual pulsed tone
    pulse = np.sin(2 * np.pi * 950 * t) * (np.sin(2 * np.pi * 14 * t) > 0).astype(float)
    env = np.exp(-3.5 * t)
    threat = pulse * env * 0.70
    create_sound_file(os.path.join(out_dir, "threat_alarm.wav"), threat, sr)

    # 4. Action Confirm (Soft UI click/chime)
    dur = 0.08
    t = np.linspace(0, dur, int(sr * dur), False)
    env = np.exp(-35 * t)
    confirm = np.sin(2 * np.pi * 880 * t) * env * 0.40
    create_sound_file(os.path.join(out_dir, "action_confirm.wav"), confirm, sr)

    # 5. Export Complete (Ascending C-E-G triad chime)
    dur = 0.38
    t = np.linspace(0, dur, int(sr * dur), False)
    # 3 segment tones
    n3 = len(t) // 3
    t1, t2, t3 = t[:n3], t[n3:2*n3] - t[n3], t[2*n3:] - t[2*n3]
    w1 = np.sin(2 * np.pi * 523.25 * t1) * np.exp(-8 * t1)
    w2 = np.sin(2 * np.pi * 659.25 * t2) * np.exp(-8 * t2)
    w3 = np.sin(2 * np.pi * 783.99 * t3) * np.exp(-5 * t3)
    complete = np.concatenate([w1, w2, w3]) * 0.50
    create_sound_file(os.path.join(out_dir, "export_complete.wav"), complete, sr)

if __name__ == "__main__":
    generate_all_sounds()
