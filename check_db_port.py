import socket

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except:
            return False

print(f"127.0.0.1:3306: {check_port('127.0.0.1', 3306)}")
print(f"127.0.0.1:3307: {check_port('127.0.0.1', 3307)}")
print(f"127.0.0.1:3308: {check_port('127.0.0.1', 3308)}")
print(f"localhost:3306: {check_port('localhost', 3306)}")
