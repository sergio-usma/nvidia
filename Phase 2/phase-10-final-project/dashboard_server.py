#!/usr/bin/env python3
"""
INNOVALABS — Dashboard & Remote Control Server
================================================
Servidor web ligero para monitorear y controlar la fábrica
de literatura desde cualquier dispositivo en la red local.

Endpoints API:
  GET  /api/system       → Métricas de CPU, RAM, GPU, disco, temperatura
  GET  /api/pipeline      → Estado del pipeline (cola, historias, proceso actual)
  GET  /api/ollama        → Estado de Ollama y modelos cargados
  GET  /api/n8n           → Estado de n8n y últimas ejecuciones
  GET  /api/stories       → Lista de historias generadas
  GET  /api/stories/{id}  → Contenido de una historia específica
  GET  /api/logs          → Últimas líneas de logs del sistema
  POST /api/control       → Acciones de control remoto

Uso:
  python3 server.py                    # Arranca en 0.0.0.0:8080
  python3 server.py --port 9090        # Puerto personalizado
  python3 server.py --host 127.0.0.1   # Solo acceso local

Target: NVIDIA Jetson AGX Orin (aarch64) / Ubuntu 22.04
"""

import asyncio
import json
import os
import glob
import subprocess
import time
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Dependencias no instaladas. Ejecutar:")
    print("  pip install fastapi uvicorn[standard] pydantic")
    exit(1)

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

HISTORIAS_DIR = os.environ.get(
    "INNOVALABS_HISTORIAS_DIR", "/var/opt/innovalabs/historias"
)
N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LOG_LINES = 100  # Líneas de log a devolver
TEMPLATES_DIR = Path(__file__).parent / "templates"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DASHBOARD] %(levelname)s: %(message)s",
)
log = logging.getLogger("dashboard")

# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="INNOVALABS Dashboard",
    description="Remote monitoring & control for the Autonomous Literature Factory",
    version="1.0.0",
)


# ─────────────────────────────────────────────
# Modelos de datos
# ─────────────────────────────────────────────

class ControlAction(BaseModel):
    action: str  # restart_ollama, restart_n8n, trigger_pipeline, kill_writer, shutdown
    confirm: bool = False


# ─────────────────────────────────────────────
# Utilidades de sistema
# ─────────────────────────────────────────────

def run_cmd(cmd: str, timeout: int = 10) -> str:
    """Ejecuta un comando y retorna stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"


def get_cpu_info() -> dict:
    """Obtiene información de CPU."""
    try:
        # Uso promedio
        load1, load5, load15 = os.getloadavg()
        cores = os.cpu_count() or 12

        # Uso por core (simplificado)
        cpu_usage = run_cmd(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"
        )

        # Frecuencia actual
        freq = run_cmd(
            "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null"
        )
        freq_mhz = int(freq) / 1000 if freq.isdigit() else 0

        return {
            "cores": cores,
            "usage_percent": float(cpu_usage) if cpu_usage.replace(".", "").isdigit() else 0,
            "load_1m": round(load1, 2),
            "load_5m": round(load5, 2),
            "load_15m": round(load15, 2),
            "freq_mhz": round(freq_mhz),
        }
    except Exception as e:
        return {"error": str(e)}


def get_memory_info() -> dict:
    """Obtiene información de memoria."""
    try:
        mem_info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(":")
                val = int(parts[1])  # kB
                mem_info[key] = val

        total = mem_info.get("MemTotal", 0) / 1024  # MB
        available = mem_info.get("MemAvailable", 0) / 1024
        used = total - available
        swap_total = mem_info.get("SwapTotal", 0) / 1024
        swap_free = mem_info.get("SwapFree", 0) / 1024
        swap_used = swap_total - swap_free

        return {
            "total_mb": round(total),
            "used_mb": round(used),
            "available_mb": round(available),
            "usage_percent": round((used / total) * 100, 1) if total > 0 else 0,
            "swap_total_mb": round(swap_total),
            "swap_used_mb": round(swap_used),
        }
    except Exception as e:
        return {"error": str(e)}


def get_gpu_info() -> dict:
    """Obtiene información de GPU via tegrastats o sysfs."""
    try:
        # Temperatura
        temp_zones = glob.glob("/sys/devices/virtual/thermal/thermal_zone*/temp")
        temps = {}
        for zone in temp_zones:
            zone_name_path = zone.replace("temp", "type")
            try:
                with open(zone_name_path) as f:
                    name = f.read().strip()
                with open(zone) as f:
                    temp_mc = int(f.read().strip())
                temps[name] = round(temp_mc / 1000, 1)
            except (FileNotFoundError, ValueError):
                continue

        # GPU load
        gpu_load = run_cmd(
            "cat /sys/devices/platform/bus@0/17000000.gpu/load 2>/dev/null"
        )

        # Frecuencia GPU
        gpu_freq = run_cmd(
            "cat /sys/devices/platform/bus@0/17000000.gpu/devfreq/17000000.gpu/cur_freq 2>/dev/null"
        )
        gpu_freq_mhz = int(gpu_freq) / 1000000 if gpu_freq.isdigit() else 0

        # Potencia (si está disponible)
        power = run_cmd(
            "cat /sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon*/in1_input 2>/dev/null"
        )

        return {
            "gpu_load_percent": int(gpu_load) / 10 if gpu_load.isdigit() else 0,
            "gpu_freq_mhz": round(gpu_freq_mhz),
            "temperatures": temps,
            "power_mw": int(power) if power.isdigit() else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_disk_info() -> dict:
    """Información de disco."""
    try:
        stat = os.statvfs("/")
        total = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
        free = (stat.f_bfree * stat.f_frsize) / (1024 ** 3)
        used = total - free

        # Espacio de historias
        historias_size = run_cmd(
            f"du -sh {HISTORIAS_DIR} 2>/dev/null | cut -f1"
        )

        return {
            "total_gb": round(total, 1),
            "used_gb": round(used, 1),
            "free_gb": round(free, 1),
            "usage_percent": round((used / total) * 100, 1) if total > 0 else 0,
            "historias_size": historias_size or "0",
        }
    except Exception as e:
        return {"error": str(e)}


def get_uptime() -> dict:
    """Tiempo de actividad del sistema."""
    try:
        with open("/proc/uptime") as f:
            uptime_secs = float(f.read().split()[0])
        days = int(uptime_secs // 86400)
        hours = int((uptime_secs % 86400) // 3600)
        minutes = int((uptime_secs % 3600) // 60)
        return {
            "seconds": int(uptime_secs),
            "formatted": f"{days}d {hours}h {minutes}m",
        }
    except Exception:
        return {"seconds": 0, "formatted": "unknown"}


# ─────────────────────────────────────────────
# Utilidades de servicios
# ─────────────────────────────────────────────

def get_service_status(service: str) -> dict:
    """Estado de un servicio systemd o contenedor Docker."""
    # Intentar systemd primero
    status = run_cmd(f"systemctl is-active {service} 2>/dev/null")
    if status in ("active", "inactive", "failed"):
        return {"mode": "systemd", "status": status, "name": service}

    # Intentar Docker
    docker_status = run_cmd(
        f"docker inspect --format='{{{{.State.Status}}}}' innovalabs-{service} 2>/dev/null"
    )
    if docker_status in ("running", "exited", "paused", "created"):
        health = run_cmd(
            f"docker inspect --format='{{{{.State.Health.Status}}}}' innovalabs-{service} 2>/dev/null"
        )
        return {
            "mode": "docker",
            "status": docker_status,
            "health": health if health else None,
            "name": f"innovalabs-{service}",
        }

    return {"mode": "unknown", "status": "not_found", "name": service}


async def check_ollama() -> dict:
    """Estado de Ollama y modelos."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = []
            for m in data.get("models", []):
                models.append({
                    "name": m.get("name", ""),
                    "size_gb": round(m.get("size", 0) / (1024**3), 1),
                    "modified": m.get("modified_at", ""),
                })
            return {"online": True, "models": models, "model_count": len(models)}
    except Exception as e:
        return {"online": False, "models": [], "error": str(e)}


async def check_n8n() -> dict:
    """Estado de n8n."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{N8N_URL}/healthz")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return {"online": True, "status": data.get("status", "unknown")}
    except Exception as e:
        return {"online": False, "error": str(e)}


def get_running_processes() -> list:
    """Detecta procesos pesados de inferencia."""
    processes = []
    ps_output = run_cmd("ps aux | grep -E 'llama-cli|ollama|n8n' | grep -v grep")
    for line in ps_output.split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 11:
            processes.append({
                "pid": parts[1],
                "cpu": parts[2],
                "mem": parts[3],
                "command": " ".join(parts[10:])[:80],
            })
    return processes


# ─────────────────────────────────────────────
# Utilidades de historias
# ─────────────────────────────────────────────

def list_stories() -> list:
    """Lista historias generadas."""
    stories = []
    pattern = os.path.join(HISTORIAS_DIR, "Historia_*.md")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    for filepath in files[:50]:  # Últimas 50
        filename = os.path.basename(filepath)
        stat = os.stat(filepath)
        size_kb = stat.st_size / 1024

        # Extraer metadata del front-matter
        meta = {}
        try:
            with open(filepath, "r") as f:
                content = f.read(2000)  # Solo el inicio
                if content.startswith("---"):
                    fm_end = content.find("---", 3)
                    if fm_end > 0:
                        fm = content[3:fm_end]
                        for line in fm.strip().split("\n"):
                            if ":" in line:
                                k, v = line.split(":", 1)
                                meta[k.strip()] = v.strip().strip('"')
        except Exception:
            pass

        stories.append({
            "filename": filename,
            "id": filename.replace("Historia_", "").replace(".md", ""),
            "size_kb": round(size_kb, 1),
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "tema": meta.get("tema", ""),
            "moraleja": meta.get("moraleja", ""),
            "palabras": meta.get("palabras", ""),
        })

    return stories


def read_story(story_id: str) -> Optional[str]:
    """Lee el contenido completo de una historia."""
    # Sanitizar story_id para prevenir path traversal
    safe_id = os.path.basename(story_id).replace("/", "").replace("\\", "").replace("..", "")
    filepath = os.path.join(HISTORIAS_DIR, f"Historia_{safe_id}.md")
    # Verificar que la ruta resuelta está dentro del directorio permitido
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(HISTORIAS_DIR)):
        return None
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return f.read()


# ─────────────────────────────────────────────
# Endpoints API
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Sirve el dashboard HTML."""
    html_path = TEMPLATES_DIR / "index.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=500)
    with open(html_path) as f:
        return HTMLResponse(f.read())


@app.get("/factory", response_class=HTMLResponse)
async def serve_factory():
    """Sirve la vista pixel-art de la fábrica."""
    html_path = TEMPLATES_DIR / "factory.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Factory template not found</h1>", status_code=500)
    with open(html_path) as f:
        return HTMLResponse(f.read())


@app.get("/api/system")
async def api_system():
    """Métricas completas del sistema."""
    return {
        "timestamp": datetime.now().isoformat(),
        "uptime": get_uptime(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "gpu": get_gpu_info(),
        "disk": get_disk_info(),
        "hostname": run_cmd("hostname"),
        "ip": run_cmd("hostname -I | awk '{print $1}'"),
    }


@app.get("/api/pipeline")
async def api_pipeline():
    """Estado del pipeline."""
    stories = list_stories()
    processes = get_running_processes()

    # Detectar fase actual
    current_phase = "idle"
    for proc in processes:
        cmd = proc["command"].lower()
        if "llama-cli" in cmd:
            current_phase = "writing"
        elif "ollama" in cmd and "serve" not in cmd:
            current_phase = "inferencing"
        elif "scout" in cmd or "pytrends" in cmd:
            current_phase = "scouting"

    # Determinar si el writer está activo
    writer_active = any("llama-cli" in p["command"] for p in processes)

    return {
        "timestamp": datetime.now().isoformat(),
        "current_phase": current_phase,
        "writer_active": writer_active,
        "active_processes": processes,
        "stories_total": len(stories),
        "latest_story": stories[0] if stories else None,
        "stories_today": len([
            s for s in stories
            if s["created"][:10] == datetime.now().strftime("%Y-%m-%d")
        ]),
    }


@app.get("/api/ollama")
async def api_ollama():
    """Estado de Ollama."""
    status = await check_ollama()
    service = get_service_status("ollama")
    return {**status, "service": service}


@app.get("/api/n8n")
async def api_n8n():
    """Estado de n8n."""
    status = await check_n8n()
    service = get_service_status("n8n")
    return {**status, "service": service}


@app.get("/api/stories")
async def api_stories():
    """Lista de historias generadas."""
    return {"stories": list_stories()}


@app.get("/api/stories/{story_id}")
async def api_story_detail(story_id: str):
    """Contenido de una historia."""
    content = read_story(story_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Historia no encontrada")
    return {"id": story_id, "content": content}


@app.get("/api/stories/{story_id}/download")
async def api_story_download(story_id: str):
    """Descargar historia como archivo .md."""
    safe_id = os.path.basename(story_id).replace("/", "").replace("\\", "").replace("..", "")
    filepath = os.path.join(HISTORIAS_DIR, f"Historia_{safe_id}.md")
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(HISTORIAS_DIR)):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Historia no encontrada")
    return FileResponse(filepath, filename=f"Historia_{safe_id}.md")


@app.get("/api/logs")
async def api_logs(service: str = "all", lines: int = LOG_LINES):
    """Últimas líneas de logs."""
    lines = min(lines, 500)

    if service == "n8n":
        output = run_cmd(f"journalctl -u n8n --no-pager -n {lines} 2>/dev/null || "
                         f"docker logs innovalabs-n8n --tail {lines} 2>&1")
    elif service == "ollama":
        output = run_cmd(f"journalctl -u ollama --no-pager -n {lines} 2>/dev/null || "
                         f"docker logs innovalabs-ollama --tail {lines} 2>&1")
    elif service == "writer":
        output = run_cmd(f"docker logs innovalabs-writer --tail {lines} 2>&1")
    else:
        output = run_cmd(f"journalctl --no-pager -n {lines} -p info 2>/dev/null")

    return {
        "service": service,
        "lines": output.split("\n") if output else [],
        "count": len(output.split("\n")) if output else 0,
    }


@app.post("/api/control")
async def api_control(action: ControlAction):
    """Acciones de control remoto."""

    ALLOWED_ACTIONS = {
        "restart_ollama": {
            "cmd_systemd": "sudo systemctl restart ollama",
            "cmd_docker": "docker restart innovalabs-ollama",
            "desc": "Reiniciar Ollama",
        },
        "restart_n8n": {
            "cmd_systemd": "sudo systemctl restart n8n",
            "cmd_docker": "docker restart innovalabs-n8n",
            "desc": "Reiniciar n8n",
        },
        "trigger_pipeline": {
            "cmd_systemd": "source /opt/innovalabs/venv/bin/activate && python3 /opt/innovalabs/scripts/scout_trends.py --dry-run",
            "cmd_docker": "docker exec innovalabs-n8n wget -qO- http://localhost:5678/webhook-test/trigger 2>&1 || echo 'Use n8n UI to trigger manually'",
            "desc": "Disparar pipeline manualmente",
        },
        "kill_writer": {
            "cmd_systemd": "pkill -f llama-cli",
            "cmd_docker": "docker exec innovalabs-writer pkill -f llama-cli",
            "desc": "Detener proceso del Escritor",
        },
        "clear_vram": {
            "cmd_systemd": "sudo systemctl restart ollama && sleep 5",
            "cmd_docker": "docker restart innovalabs-ollama && sleep 5",
            "desc": "Liberar VRAM (reiniciar Ollama)",
        },
        "jetson_clocks": {
            "cmd_systemd": "sudo jetson_clocks",
            "cmd_docker": "sudo jetson_clocks",
            "desc": "Maximizar frecuencias (jetson_clocks)",
        },
    }

    if action.action not in ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Acción no válida. Opciones: {list(ALLOWED_ACTIONS.keys())}",
        )

    if not action.confirm:
        return {
            "status": "pending_confirmation",
            "action": action.action,
            "description": ALLOWED_ACTIONS[action.action]["desc"],
            "message": "Enviar de nuevo con confirm=true para ejecutar",
        }

    spec = ALLOWED_ACTIONS[action.action]

    # Detectar si estamos en modo Docker o nativo
    is_docker = get_service_status("ollama")["mode"] == "docker"
    cmd = spec["cmd_docker"] if is_docker else spec["cmd_systemd"]

    log.info(f"Ejecutando acción: {action.action} → {cmd}")
    output = run_cmd(cmd, timeout=30)

    return {
        "status": "executed",
        "action": action.action,
        "description": spec["desc"],
        "output": output,
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="INNOVALABS Dashboard Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8080, help="Port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on changes")
    args = parser.parse_args()

    log.info(f"INNOVALABS Dashboard starting on http://{args.host}:{args.port}")
    log.info(f"Access from your Windows PC: http://<JETSON_IP>:{args.port}")

    uvicorn.run(
        "server:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
