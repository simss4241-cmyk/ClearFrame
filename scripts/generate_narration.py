import os
import asyncio
import subprocess
import edge_tts
import imageio_ffmpeg

VOICE = "en-US-AndrewNeural" # Crisp, professional documentary narrator
OUTPUT_DIR = "C:/Projects/NeuroForge/ClearFrame/Video"
VIDEO_IN = os.path.join(OUTPUT_DIR, "video1.mp4")
VIDEO_OUT = os.path.join(OUTPUT_DIR, "ClearFrame_Demo_Final.mp4")

# Timed narration segments (start_time_seconds, text)
SEGMENTS = [
    (
        0.5,
        "This is ClearFrame — an agentic production counsel workstation for independent films. "
        "We load our Gauntlet screenplay and execute a live clearance scan."
    ),
    (
        7.5,
        "Google Cloud Gemini ingests the script and extracts clearable entities across six specialized legal departments. "
        "ClearFrame then queries Parallel Web search APIs to cross-reference copyright registries and live web records."
    ),
    (
        25.0,
        "A core architectural pillar: AI models extract facts and citations, but a deterministic Python rule engine "
        "computes every statutory risk rating and rule ID. Zero hallucinations, zero model-assigned verdicts."
    ),
    (
        46.5,
        "As the scan finishes, the polar radar paints our liability surface, and forensic exhibit anchors bloom into the script body. "
        "Every finding links directly to live registry citations with confidence scoring."
    ),
    (
        62.0,
        "ClearFrame isn't just a static report generator — it's an interactive word processor. "
        "By switching to Edit Mode, production counsel can remediate flagged liabilities directly in the screenplay."
    ),
    (
        78.0,
        "Notice our instant provenance tracking: modifying text immediately marks the affected exhibit as stale evidence, "
        "dimming its radar blip so the legal team knows the analysis must be refreshed."
    ),
    (
        100.0,
        "We hit Recheck Clearance, and ClearFrame re-scans the script in real-time, verifying statutory compliance across the chain of title."
    ),
    (
        115.0,
        "Finally, counsel can export the cleaned screenplay directly as Final Draft XML or clean text. "
        "Built with Google Cloud ADK, Gemini, and Parallel Web."
    )
]


async def generate_audio():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.join(OUTPUT_DIR, "audio_chunks"), exist_ok=True)
    
    chunk_files = []
    
    print("Generating voiceover audio chunks...")
    for idx, (start_sec, text) in enumerate(SEGMENTS):
        chunk_path = os.path.join(OUTPUT_DIR, "audio_chunks", f"chunk_{idx:02d}.mp3")
        communicate = edge_tts.Communicate(text, VOICE, rate="+4%")
        await communicate.save(chunk_path)
        chunk_files.append((start_sec, chunk_path))
        print(f"  [OK] Chunk {idx} at {start_sec}s: {text[:40]}...")

    # Build ffmpeg filter_complex to place audio chunks at exact timestamps
    inputs = []
    filter_parts = []
    
    for idx, (start_sec, path) in enumerate(chunk_files):
        inputs.extend(["-i", path])
        delay_ms = int(start_sec * 1000)
        filter_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[a{idx}]")
    
    mix_inputs = "".join([f"[a{i}]" for i in range(len(chunk_files))])
    filter_complex = f"{';'.join(filter_parts)};{mix_inputs}amix=inputs={len(chunk_files)}:normalize=0[aout]"
    
    combined_audio = os.path.join(OUTPUT_DIR, "narration_master.wav")
    
    cmd_audio = [
        ffmpeg_exe, "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        combined_audio
    ]
    
    print("Combining audio with ffmpeg filter_complex...")
    subprocess.run(cmd_audio, check=True)
    print(f"Master audio generated: {combined_audio}")

    # Now multiplex with video1.mp4
    print("Multiplexing with video1.mp4 into final video...")
    cmd_mux = [
        ffmpeg_exe, "-y",
        "-i", VIDEO_IN,
        "-i", combined_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        VIDEO_OUT
    ]
    subprocess.run(cmd_mux, check=True)
    print(f"\n[SUCCESS] Final spruced up video ready at:\n  {VIDEO_OUT}")


if __name__ == "__main__":
    asyncio.run(generate_audio())
