import argparse
import re
import socket
import sys
import threading

import cv2
import numpy as np

sys.path.insert(0, "./")
sys.path.insert(0, "../")

from cheat_detector import CheatDetector


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf


def thread_send_webcam(server_socket, args):
    print("USER : CANDIDATE")
    cheatDetector = CheatDetector(args)
    capture = cv2.VideoCapture(0)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    while True:
        ret, frame = capture.read()
        if not ret:
            continue

        result, imgencode = cv2.imencode('.jpg', frame, encode_param)
        imgData = np.array(imgencode).tobytes()

        cheat_info = cheatDetector.process(frame)  # Cheat info: 0 Normal 1 CheatLeft 2 NoFace 3 CheatRight
        cheatData = bytes([cheat_info])

        stringData = imgData + cheatData  # 이미지 데이터 뒤에 치트 정보 숫자 하나 꼽사리 끼겠습니다

        try:
            server_socket.send('1'.encode(encoding='ISO-8859-1'))
            server_socket.send(str(len(stringData)).ljust(16).encode(encoding='ISO-8859-1'))
            server_socket.send(stringData)  # stringData = imgData + cheatData
            server_socket.recv(1).decode(encoding='ISO-8859-1')

        except ConnectionResetError as e:
            break

        except ConnectionAbortedError as e:
            break

        # cv2.imshow('client', frame)

    server_socket.close()


def thread_receive_webcam(server_socket):
    print("USER : SUPERVISOR")

    while True:
        try:
            uid = server_socket.recv(1024).decode(encoding='ISO-8859-1')

            if not uid:
                break

            length = server_socket.recv(16).decode(encoding='ISO-8859-1')
            print('length : ', length)

            stringData = recvall(server_socket, int(length))  # stringData = imgData + cheatData
            server_socket.send('1'.encode(encoding='ISO-8859-1'))

            imgData, cheatData = stringData[:-1], stringData[-1]
            data = np.frombuffer(imgData, dtype='uint8')
            decimg = cv2.imdecode(data, 1)
            decimg = cv2.flip(decimg, 1)
            cheat_info = int(cheatData)  # Cheat info: 0 Normal 1 Cheat 2 NoFace

            if True:  # DEBUG
                if cheat_info == 1:
                    cv2.putText(decimg, 'CHEAT : Upper Left', (decimg.shape[1] // 4, decimg.shape[0] // 4), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                elif cheat_info == 2:
                    cv2.putText(decimg, 'CHEAT : Lower Left', (decimg.shape[1] // 4, decimg.shape[0] // 4), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                elif cheat_info == 3:
                    cv2.putText(decimg, 'CHEAT : Upper Right', (decimg.shape[1] // 4, decimg.shape[0] // 4), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                elif cheat_info == 4:
                    cv2.putText(decimg, 'CHEAT : Lower Right', (decimg.shape[1] // 4, decimg.shape[0] // 4), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                elif cheat_info == 5:
                    cv2.putText(decimg, 'No Face', (decimg.shape[1] // 4, decimg.shape[0] // 4), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

            window_name = str(uid)
            x = int(re.findall("\d+", window_name)[-1])
            cv2.namedWindow(window_name)
            cv2.moveWindow(window_name, x, 100)
            cv2.imshow(window_name, decimg)

            key = cv2.waitKey(1)
            if key == ord('q'):  # press q to exit
                break

        except ConnectionAbortedError as e:
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, help='Config file for YACS. When using a config file, all the other commandline arguments are ignored. See https://github.com/hysts/pytorch_mpiigaze_demo/configs/demo_mpiigaze.yaml')
    parser.add_argument('--mode', type=str, default='eye', choices=['eye', 'face'], help='With \'eye\', MPIIGaze model will be used. With \'face\', MPIIFaceGaze model will be used. (default: \'eye\')')
    parser.add_argument('--face-detector', type=str, default='face_alignment_sfd', choices=['dlib', 'face_alignment_dlib', 'face_alignment_sfd'], help='The method used to detect faces and find face landmarks (default: \'dlib\')')
    parser.add_argument('--device', type=str, choices=['cpu', 'cuda'], help='Device used for model inference.')
    parser.add_argument('--camera', type=str, help='Camera calibration file. See https://github.com/hysts/pytorch_mpiigaze_demo/ptgaze/data/calib/sample_params.yaml')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7777)
    args = parser.parse_args()

    host = args.host
    port = args.port
    is_supervisor = False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((host, port))

    while True:
        exam_addr = input("시험 주소 입력하세요:")
        server_socket.send(exam_addr.encode(encoding='ISO-8859-1'))
        result = server_socket.recv(1024).decode(encoding='ISO-8859-1')

        # 서버로부터 받은 응답이 1이면 okay
        if result == '1':
            break

        elif result == '-1':
            print("잘못된 시험 주소 입니다.")
            continue

    uid = input("ID를 입력하세요:")
    server_socket.send(uid.encode(encoding='ISO-8859-1'))
    result = server_socket.recv(1024).decode(encoding='ISO-8859-1')

    if result == '1':
        is_supervisor = 1

    # 감독관이면 실행 안됨
    while not is_supervisor:
        print("감독관이 접속할 때까지 기다려 주세요")
        result = server_socket.recv(1024).decode(encoding='ISO-8859-1')
        if result == "1":
            print("감독관 접속")
            break

    if is_supervisor == True:
        receive_webcam_thread = threading.Thread(target=thread_receive_webcam, args=(server_socket,))
        receive_webcam_thread.start()
        receive_webcam_thread.join()

    else:
        send_webcam_thread = threading.Thread(target=thread_send_webcam, args=(server_socket, args,))
        send_webcam_thread.start()
        send_webcam_thread.join()


if __name__ == "__main__":
    main()
