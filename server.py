import os
import re
import socket
from datetime import datetime


class SocketServer:
    def __init__(self):
        self.bufsize = 1024  # 버퍼 크기 설정
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read()  # 응답 파일 읽기
        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        """디렉토리 생성"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def receiveRequest(self, clnt_sock):
        """클라이언트 요청 전체 수신 (헤더 + Content-Length 만큼의 바디)"""
        response = b""
        header, body = b"", b""
        try:
            # 1) 헤더 끝(\r\n\r\n)까지 수신
            while b"\r\n\r\n" not in response:
                chunk = clnt_sock.recv(self.bufsize)
                if not chunk:
                    break
                response += chunk

            header, _, body = response.partition(b"\r\n\r\n")

            # 2) Content-Length 확인
            content_length = 0
            for line in header.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    content_length = int(line.split(b":", 1)[1].strip())

            # 3) 바디 나머지 수신
            while len(body) < content_length:
                chunk = clnt_sock.recv(self.bufsize)
                if not chunk:
                    break
                body += chunk
        except socket.timeout:
            print("Timeout: 수신 중단")
            header, _, body = response.partition(b"\r\n\r\n")

        return header, body

    def saveRequest(self, data, timestamp):
        """실습 1: 요청 원본을 이진 파일로 저장"""
        path = os.path.join(self.DIR_PATH, timestamp + ".bin")
        with open(path, "wb") as f:
            f.write(data)
        print(f"Request saved: {path}")

    def saveImage(self, header, body, timestamp):
        """실습 2: multipart 바디에서 파일 파트를 찾아 이미지로 저장"""
        m = re.search(rb'boundary=([^\r\n;]+)', header)
        if not m:
            return
        boundary = b"--" + m.group(1).strip().strip(b'"')

        count = 0
        for part in body.split(boundary):
            if b'filename="' not in part:
                continue

            part_header, _, data = part.partition(b"\r\n\r\n")
            # 파트 끝의 CRLF 제거 (rstrip 사용 시 이미지 바이트가 손상될 수 있음)
            if data.endswith(b"\r\n"):
                data = data[:-2]

            fname_match = re.search(rb'filename="([^"]*)"', part_header)
            fname = fname_match.group(1).decode(errors="ignore") if fname_match else ""
            ext = os.path.splitext(fname)[1] or ".bin"

            suffix = f"_{count}" if count > 0 else ""
            path = os.path.join(self.DIR_PATH, timestamp + suffix + ext)
            with open(path, "wb") as f:
                f.write(data)
            print(f"Image saved: {path}")
            count += 1

    def run(self, ip, port):
        """서버 실행"""
        # 소켓 생성
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)
        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")

        try:
            while True:
                # 클라이언트의 요청 대기
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0)  # 타임아웃 설정 (5초)
                print("Request message...\r\n")

                # 요청 수신
                header, body = self.receiveRequest(clnt_sock)
                response = header + b"\r\n\r\n" + body

                if response.strip():
                    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

                    # 실습 1: 요청 원본 저장
                    self.saveRequest(response, timestamp)

                    # 실습 2: multipart 이미지 저장
                    if b"multipart/form-data" in header:
                        self.saveImage(header, body, timestamp)

                # 응답 전송
                clnt_sock.sendall(self.RESPONSE)

                # 클라이언트 소켓 닫기
                clnt_sock.close()
        except KeyboardInterrupt:
            print("\r\nStop the server...")

        # 서버 소켓 닫기
        self.sock.close()


if __name__ == "__main__":
    server = SocketServer()
    server.run("127.0.0.1", 8000)