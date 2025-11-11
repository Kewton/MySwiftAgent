"""
Status Dashboard CLI for MySwiftAgent

This module provides a comprehensive dashboard for monitoring all services.
"""

import csv
import io
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests

# Constants
DEFAULT_HEALTH_TIMEOUT = 5
DEFAULT_WATCH_INTERVAL = 5
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60
MB_DIVISOR = 1024 * 1024


class ServiceStatusCollector:
    """Collects status information from all services"""

    SERVICES = [
        {"name": "jobqueue", "port": 8001},
        {"name": "myscheduler", "port": 8002},
        {"name": "expertagent", "port": 8003},
        {"name": "graphaiserver", "port": 8004},
        {"name": "commonui", "port": 8501},
    ]

    def collect_service_statuses(self) -> List[Dict[str, Any]]:
        """Collect status information from all services"""
        statuses: List[Dict[str, Any]] = []
        for service in self.SERVICES:
            name = service["name"]
            port = service["port"]
            if isinstance(name, str) and isinstance(port, int):
                status = self.get_service_status(name, port)
                statuses.append(status)
        return statuses

    def get_service_status(self, name: str, port: int) -> Dict[str, Any]:
        """Get status information for a single service"""
        status = {"name": name, "port": port}

        # Health check
        health = check_health_endpoint(f"http://localhost:{port}/health")
        if health:
            status["health_status"] = health.get("status", "healthy")
            status["response_time"] = health.get("response_time", 0)
        else:
            status["health_status"] = "down"
            status["response_time"] = 0

        # Process info
        port_info = check_port_usage(port)
        if port_info and port_info.get("status") == "LISTEN":
            status["port_status"] = "LISTEN"
            proc_info = get_process_info(port_info.get("pid", 0))
            if proc_info:
                status["pid"] = proc_info.get("pid", 0)
                status["uptime"] = proc_info.get("uptime", "unknown")
                status["cpu_percent"] = proc_info.get("cpu_percent", 0.0)
                status["memory_percent"] = proc_info.get("memory_percent", 0.0)
                status["memory_mb"] = proc_info.get("memory_mb", 0.0)
        else:
            status["port_status"] = "CLOSED"

        return status


class StatusFormatter:
    """Formats service status for display"""

    # Color codes
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    YELLOW = "\033[1;33m"
    RESET = "\033[0m"

    def format_table(self, statuses: List[Dict[str, Any]]) -> str:
        """Format statuses as a colored table"""
        lines = []
        for status in statuses:
            health = status.get("health_status", "unknown")
            color = self.GREEN if health == "healthy" else self.RED

            line_parts = [
                f"{color}{status.get('name', 'unknown')}{self.RESET}",
                f"{color}{health}{self.RESET}",
            ]

            if "cpu_percent" in status:
                line_parts.append(f"{status['cpu_percent']}")
            if "memory_percent" in status:
                line_parts.append(f"{status['memory_percent']}")
            if "memory_mb" in status:
                line_parts.append(f"{status['memory_mb']}")
            if "uptime" in status:
                line_parts.append(f"{status['uptime']}")

            lines.append(" | ".join(line_parts))

        return "\n".join(lines)

    def format_json(self, statuses: List[Dict[str, Any]]) -> str:
        """Format statuses as JSON"""
        return json.dumps(statuses, indent=2)

    def format_csv(self, statuses: List[Dict[str, Any]]) -> str:
        """Format statuses as CSV"""
        if not statuses:
            return ""

        output = io.StringIO()
        fieldnames = list(statuses[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        for status in statuses:
            writer.writerow(status)

        return output.getvalue()


class LogRetriever:
    """Retrieves logs from services"""

    def get_latest_logs(self, service_name: str, lines: int = 10) -> List[str]:
        """Get latest log lines from a service"""
        try:
            log_path = f"/tmp/{service_name}.log"
            return read_log_file(log_path, lines)
        except FileNotFoundError:
            return []


def check_health_endpoint(
    url: str, timeout: int = DEFAULT_HEALTH_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """Check health endpoint of a service"""
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = time.time() - start

        if response.status_code == 200:
            return {"status": "healthy", "response_time": round(elapsed, 2)}
        else:
            return {"status": "unhealthy", "response_time": round(elapsed, 2)}
    except (requests.RequestException, Exception):
        return None


def get_process_info(pid: int) -> Dict[str, Any]:
    """Get process information"""
    try:
        proc = psutil.Process(pid)
        create_time = proc.create_time()
        uptime_seconds = int(time.time() - create_time)

        hours = uptime_seconds // SECONDS_PER_HOUR
        minutes = (uptime_seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE

        uptime_str = f"{hours}h {minutes}m"

        return {
            "pid": pid,
            "uptime": uptime_str,
            "cpu_percent": round(proc.cpu_percent(interval=0.1), 1),
            "memory_percent": round(proc.memory_percent(), 1),
            "memory_mb": round(proc.memory_info().rss / MB_DIVISOR, 1),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {}


def check_port_usage(port: int) -> Dict[str, Any]:
    """Check port usage"""
    try:
        for conn in psutil.net_connections(kind="inet"):
            laddr = conn.laddr
            if laddr and hasattr(laddr, "port") and laddr.port == port and conn.status == "LISTEN":  # type: ignore
                return {"port": port, "status": "LISTEN", "pid": conn.pid}
    except (psutil.AccessDenied, PermissionError):
        # Fallback: Use lsof command on macOS/Linux when psutil doesn't have permission
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-t"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])
                return {"port": port, "status": "LISTEN", "pid": pid}
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
            pass
    return {"port": port, "status": "CLOSED"}


def read_log_file(log_path: str, lines: int = 10) -> List[str]:
    """Read last N lines from a log file"""
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    with open(path, "r") as f:
        all_lines = f.readlines()
        return [line.strip() for line in all_lines[-lines:]]


def main(args: List[str]) -> None:
    """Main entry point for the CLI"""
    watch_mode = "--watch" in args
    output_format = "table"

    if "--format" in args:
        fmt_idx = args.index("--format")
        if fmt_idx + 1 < len(args):
            output_format = args[fmt_idx + 1]

    collector = ServiceStatusCollector()
    formatter = StatusFormatter()

    try:
        while True:
            statuses = collector.collect_service_statuses()

            if output_format == "json":
                output = formatter.format_json(statuses)
            elif output_format == "csv":
                output = formatter.format_csv(statuses)
            else:
                output = formatter.format_table(statuses)

            sys.stdout.write(output + "\n")

            if not watch_mode:
                break

            time.sleep(DEFAULT_WATCH_INTERVAL)
    except KeyboardInterrupt:
        pass


def cli_main() -> None:
    """CLI entry point for setuptools"""
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
