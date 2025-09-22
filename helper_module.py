import socket
import urllib.request

def get_public_ip():
    """Fetch the public IP address of the client machine."""
    try:
        with urllib.request.urlopen("https://api.ipify.org") as response:
            return response.read().decode("utf-8")
    except Exception as e:
        return f"Failed to retrieve public IP: {e}"

def test_port_connectivity(host, port, timeout=5):
    """Test connectivity to a given host and port."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, f"Successfully connected to {host}:{port} from this machine."
    except Exception as e:
        return False, f"Failed to connect to {host}:{port} from this machine. Error: {e}"
