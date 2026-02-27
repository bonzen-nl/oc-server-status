#!/usr/bin/env python3
"""
System Metrics Collector voor OpenClaw Server Status

Verzamelt realtime systeemmetrics:
- RAM, CPU, Disk, Temperature
- Ollama model informatie
- ChromaDB statistieken
- Netwerk informatie

Gebruiking:
    from lib.metrics_collector import MetricsCollector
    
    collector = MetricsCollector()
    metrics = collector.collect()
    print(metrics['ram_percent'])

Author: OpenClaw Server Status
License: MIT
"""

import psutil
import platform
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class MetricsCollector:
    """
    Verzamelt systeemmetrics via psutil en lokale commando's.
    
    Metrics:
    - RAM: Total, used, available, percent
    - CPU: Load averages, core count, percent
    - Swap: Total, used, percent
    - Disk: Free space per volume
    - Temperature: M-chip (macOS) als beschikbaar
    - Ollama: Running models, tokens/sec
    - ChromaDB: Document count, database size
    
    Attributes:
        system: OS type (Darwin, Linux, Windows)
        is_mac: Boolean indicating macOS
    """
    
    def __init__(self):
        """Initialiseer MetricsCollector"""
        self.system = platform.system()
        self.is_mac = self.system == "Darwin"
    
    def collect(self) -> Dict[str, Any]:
        """
        Verzamel alle beschikbare systeemmetrics.
        
        Returns:
            Dict met alle metrics:
            {
                "timestamp": ISO timestamp,
                "ram": {percent, used_gb, total_gb},
                "swap": {percent, used_gb, total_gb},
                "cpu": {load_1min, load_5min, load_15min, percent, cores},
                "disk": {free_gb, percent_used},
                "temperature": {cpu_temp_c (if available)},
                "ollama": {models, total_memory_gb, tokens_per_sec},
                "chromadb": {doc_count, size_mb}
            }
        """
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ram": self._get_ram_metrics(),
            "swap": self._get_swap_metrics(),
            "cpu": self._get_cpu_metrics(),
            "disk": self._get_disk_metrics(),
            "temperature": self._get_temperature(),
            "ollama": self._get_ollama_metrics(),
            "chromadb": self._get_chromadb_metrics()
        }
    
    def _get_ram_metrics(self) -> Dict[str, Any]:
        """
        Haal RAM metrieken op.
        
        Returns:
            {percent: float, used_gb: float, total_gb: float}
        """
        # psutil geeft in bytes, omzetten naar GB
        ram = psutil.virtual_memory()
        return {
            "percent": ram.percent,
            "used_gb": ram.used / (1024**3),
            "total_gb": ram.total / (1024**3),
            "available_gb": ram.available / (1024**3)
        }
    
    def _get_swap_metrics(self) -> Dict[str, Any]:
        """
        Haal Swap metrieken op.
        
        Returns:
            {percent: float, used_gb: float, total_gb: float}
        """
        swap = psutil.swap_memory()
        return {
            "percent": swap.percent,
            "used_gb": swap.used / (1024**3),
            "total_gb": swap.total / (1024**3),
        }
    
    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """
        Haal CPU metrieken op.
        
        Returns:
            {load_1min, load_5min, load_15min, percent, cores}
        """
        load1, load5, load15 = psutil.getloadavg()
        return {
            "load_1min": load1,
            "load_5min": load5,
            "load_15min": load15,
            "percent": psutil.cpu_percent(interval=1),
            "cores": psutil.cpu_count()
        }
    
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """
        Haal schijfruimte metrieken op (root volume).
        
        Returns:
            {free_gb: float, percent_used: float}
        """
        disk = psutil.disk_usage('/')
        return {
            "free_gb": disk.free / (1024**3),
            "total_gb": disk.total / (1024**3),
            "percent_used": disk.percent
        }
    
    def _get_temperature(self) -> Dict[str, Any]:
        """
        Haal temperatuur op (indien beschikbaar, macOS M-chip).
        
        Returns:
            {cpu_temp_c: float} of {} als niet beschikbaar
        """
        if not self.is_mac:
            return {}
        
        try:
            # macOS: system_profiler lees M-chip temp
            import subprocess
            result = subprocess.run(
                ['system_profiler', 'SPPowerDataType'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse voor "CPU Temperature"
            for line in result.stdout.split('\n'):
                if 'CPU Temperature' in line:
                    # Verwacht format: "  CPU Temperature: 52 C"
                    temp_str = line.split(':')[1].strip().split()[0]
                    return {"cpu_temp_c": float(temp_str)}
        except:
            pass
        
        return {}
    
    def _get_ollama_metrics(self) -> Dict[str, Any]:
        """
        Haal Ollama metrics op via JSON-RPC API.
        
        Returns:
            {models: [model names], total_memory_gb: float, tokens_per_sec: float}
        """
        try:
            import requests
            
            # Ollama API endpoint
            base_url = "http://127.0.0.1:11434"
            response = requests.get(f"{base_url}/api/tags", timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get('name', 'unknown') for m in data.get('models', [])]
                
                # Approximatie: per model ~4GB voor 24B models, ~1GB voor kleine
                total_memory = len(models) * 2  # GB (rough estimate)
                
                return {
                    "models": models,
                    "model_count": len(models),
                    "total_memory_gb": total_memory
                }
        except:
            pass
        
        return {"models": [], "model_count": 0, "total_memory_gb": 0}
    
    def _get_chromadb_metrics(self) -> Dict[str, Any]:
        """
        Haal ChromaDB metrics op.
        
        Returns:
            {doc_count: int, size_mb: float}
        """
        # Controleer ChromaDB pad uit config
        config_path = Path(__file__).parent.parent / "config" / "server_status.json"
        
        chromadb_path = None
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    chromadb_path = config.get("chromadb_path")
            except:
                pass
        
        # Fallback paths
        if not chromadb_path:
            chromadb_path = "/Users/bonzen/.openclaw/workspace/openclaw_rag/index_data/openclaw_chroma_local.json"
        
        chromadb_path = Path(chromadb_path)
        
        if chromadb_path.exists():
            try:
                size_mb = chromadb_path.stat().st_size / (1024**2)
                
                # Parse JSON voor doc count
                with open(chromadb_path) as f:
                    data = json.load(f)
                    doc_count = len(data.get('documents', []))
                
                return {
                    "doc_count": doc_count,
                    "size_mb": size_mb
                }
            except:
                pass
        
        return {"doc_count": 0, "size_mb": 0}


def test_collector():
    """
    Test function voor MetricsCollector.
    
    Verzamelt metrics en toont samenvatting.
    """
    try:
        print("🧪 Testing MetricsCollector...")
        
        collector = MetricsCollector()
        metrics = collector.collect()
        
        print("✅ Metrics collected:")
        print(f"  RAM: {metrics['ram']['percent']:.1f}%")
        print(f"  CPU Load: {metrics['cpu']['load_1min']:.2f}")
        print(f"  Disk Free: {metrics['disk']['free_gb']:.1f} GB")
        print(f"  Ollama Models: {metrics['ollama']['model_count']}")
        print(f"  ChromaDB Docs: {metrics['chromadb']['doc_count']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_collector()
