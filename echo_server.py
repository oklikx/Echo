import socket
import sys
from http import HTTPStatus
from urllib.parse import urlparse, parse_qs


def parse_request(raw_data: bytes):
    """Парсит HTTP-запрос. Возвращает (method, path, headers)."""
    text = raw_data.decode('utf-8', errors='replace')
    lines = text.split('\r\n')

    # Первая строка: METHOD /path HTTP/1.1
    request_line = lines[0]
    parts = request_line.split(' ')
    method = parts[0] if parts else ''
    path = parts[1] if len(parts) > 1 else '/'

    # Заголовки до пустой строки
    headers = []
    for line in lines[1:]:
        if line == '':
            break
        if ':' in line:
            name, _, value = line.partition(':')
            headers.append((name.strip(), value.strip()))

    return method, path, headers


def get_status_from_path(path: str) -> str:
    """Извлекает статус из GET-параметра status. Возвращает строку вида '200 OK'."""
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    status_values = query.get('status')

    default_status = '200 OK'
    if not status_values:
        return default_status

    raw_status = status_values[0]
    try:
        code = int(raw_status)
        return f'{code} {HTTPStatus(code).phrase}'
    except (ValueError, KeyError):
        return default_status


def build_response(method, path, headers, client_address):
    status = get_status_from_path(path)

    body_lines = [
        f'Request Method: {method}',
        f'Request Source: {client_address}',
        f'Response Status: {status}',
    ]
    for name, value in headers:
        body_lines.append(f'{name}: {value}')

    body = '\n'.join(body_lines) + '\n'
    body_bytes = body.encode('utf-8')

    response = (
        f'HTTP/1.1 {status}\r\n'
        f'Content-Type: text/plain; charset=utf-8\r\n'
        f'Content-Length: {len(body_bytes)}\r\n'
        f'Connection: close\r\n'
        f'\r\n'
    ).encode('utf-8') + body_bytes

    return response


def handle_client(conn, addr):
    try:
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk

        if not data:
            return

        method, path, headers = parse_request(data)
        response = build_response(method, path, headers, addr)
        conn.sendall(response)
    finally:
        conn.close()


def main():
    host = '127.0.0.1'
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()

        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)


if __name__ == '__main__':
    main()
