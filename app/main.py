import os, re, uuid, tempfile
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment
from openai import OpenAI

# === Config por entorno ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ACTION_API_KEY = os.getenv("ACTION_API_KEY")  # la que vas a poner en el header X-API-Key
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()

# Servir los MP3 desde /public
os.makedirs("public", exist_ok=True)
app.mount("/public", StaticFiles(directory="public"), name="public")

def parse_script(text: str):
    """Espera líneas que empiecen con A:, B: (y opcional C:). Devuelve lista de (speaker, texto)."""
    turns = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*([ABC]):\s*(.+)$", line.strip())
        if m:
            turns.append((m.group(1), m.group(2)))
    if not turns:
        raise ValueError("El guion debe tener líneas que empiecen con 'A:' o 'B:' (y opcional 'C:').")
    return turns

def synth_tts(text: str, voice: str, model: str = "gpt-4o-mini-tts") -> bytes:
    """Text-to-Speech: devuelve bytes MP3 usando la Audio API."""
    resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        format="mp3"
    )
    return resp.read()

@app.post("/duo-tts")
def duo_tts(payload: dict, x_api_key: str = Header(None)):
    # Autenticación simple por header
    if ACTION_API_KEY and x_api_key != ACTION_API_KEY:
        raise HTTPException(status_code=401, detail="Auth failed (X-API-Key incorrecta)")

    script = (payload.get("script") or "").strip()
    voice_a = payload.get("voice_a", "alloy")
    voice_b = payload.get("voice_b", "verse")
    pause_ms = int(payload.get("pause_ms", 500))

    if not script:
        raise HTTPException(status_code=400, detail="Falta 'script'")

    turns = parse_script(script)
    voice_map = {"A": voice_a, "B": voice_b, "C": "aria"}  # tercera voz opcional

    # Sintetizar cada intervención y concatenar con silencio
    segments = []
    for spk, text in turns:
        mp3_bytes = synth_tts(text, voice_map.get(spk, voice_a))
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(mp3_bytes)
            path = f.name
        segments.append(AudioSegment.from_file(path))

    final = AudioSegment.silent(duration=250)  # mini fade-in
    for i, seg in enumerate(segments):
        final += seg
        if i < len(segments) - 1:
            final += AudioSegment.silent(duration=pause_ms)

    out_name = f"{uuid.uuid4().hex}.mp3"
    out_path = os.path.join("public", out_name)
    final.export(out_path, format="mp3")

    return JSONResponse({"audio_url": f"{PUBLIC_BASE_URL}/public/{out_name}"})
