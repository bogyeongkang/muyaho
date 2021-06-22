import os
import socket
import cv2
import datetime
import numpy as np
import threading
from _thread import *
import pymysql

# 필요한 기본 DB 정보
host = "127.0.0.1"  # 접속할 db의 host명
DB_user = "root"  # 접속할 db의 user명
DB_pw = "muyaho"  # 접속할 db의 password
DB = "test1"  # 접속할 db의 table명 (실제 데이터가 추출되는 table)
# DB에 접속
conn = pymysql.connect(host=host, user=DB_user, password=DB_pw, db=DB, charset="utf8")
curs = conn.cursor()

sql = "select * from signUp"
curs.execute(sql)
result = curs.fetchall()
print(result)

id_list = []
pw_list = []
for i in range(0, len(result)):
    id_list.append(result[i][0])
    pw_list.append(result[i][1])
uid_in_DB = dict(zip(id_list, pw_list))
print(uid_in_DB)

sql = "select * from Exam"
curs.execute(sql)
result = curs.fetchall()
print(result)

key_list = ['eid', 'supervisor', 'start_time', 'end_time']
value_list = []
exams = []
for i in range(0, len(result)):
    for i in range(0, len(result)):
        value_list.append(result[i][0])
        value_list.append([result[i][5]])
        value_list.append(result[i][3])
        value_list.append(result[i][4])
        exam = dict(zip(key_list, value_list))
    exams.append(exam)

print(exams)
video_path = os.path.expanduser('~/Desktop/video/')

# # 처음 시작할 때 DB에서 시험 아이디? 주소? 가져와서 exams 에 load
#
# # supervisor에 socket도  연결 들어오면 추가
# exams = [
#     {'eid': '1', 'supervisor': ['uid0'], 'start_time': '202105241330', 'end_time': '202105241500'},
#     {'eid': '2', 'supervisor': ['uid1'], 'start_time': '202105241400', 'end_time': '202105241600'},
#     {'eid': '3', 'supervisor': ['uid2'], 'start_time': '202105241400', 'end_time': '202105241600'}
# ]
#
# uid_in_DB = {'uid0':'password0', 'uid1':'password1', 'uid2':'password2'}

port = 7777

lock = threading.Lock()


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf


def thread_webcam(client_socket, addr):
    port = 7777
    exam = None
    eid = None
    uid = None
    is_supervisor = False
    supervisor = None
    supervisor_socket = None

    print("CONNECTED BY : ", addr)

    # login, sign up
    while True:
        recv = client_socket.recv(1024).decode(encoding='ISO-8859-1')
        messages = recv.split('@')

        if messages[0] == 'login':

            uid = messages[1]
            pw = messages[2]
            print("uid:", uid, "pw:", pw)

            if uid in uid_in_DB:
                print("uid is in uid_in_DB")
                if uid_in_DB[uid] == pw:
                    client_socket.send('1'.encode(encoding='ISO-8859-1'))
                    break

            client_socket.send('0'.encode(encoding='ISO-8859-1'))

        elif messages[0] == 'signUp':
            messages = recv.split('@')
            uid = messages[1]
            pw = messages[2]
            phoneNum = messages[3]
            uid_in_DB[uid] = pw
            print("uid_in_DB\n", uid_in_DB)
            client_socket.send('0'.encode(encoding='ISO-8859-1'))

            conn = pymysql.connect(host=host, user=DB_user, password=DB_pw, db=DB, charset="utf8")
            curs = conn.cursor()

            sql = "insert into signup(uid,password,phonenumber) values (%s,%s,%s);"
            curs.execute(sql, (uid, pw, phoneNum))
            conn.commit()
            print("sign up completed")

    # enter exam, create exam
    while True:

        recv = client_socket.recv(1024).decode(encoding='ISO-8859-1')
        messages = recv.split('@')

        if messages[0] == 'enterExam':
            eid = messages[1]
            print("eid:", eid)
            print("user entered exam")
            if any(exam['eid'] == eid for exam in exams):
                exam = next(exam for exam in exams if exam['eid'] == eid)
                supervisor = exam['supervisor']

                if supervisor[0] == uid:
                    client_socket.send('1'.encode(encoding='ISO-8859-1'))
                    print('supervisor')
                    is_supervisor = True
                    supervisor.insert(1, client_socket)

                else:
                    client_socket.send('0'.encode(encoding='ISO-8859-1'))
                    print('candidate')
                    tid = get_ident()  # it will be modified to uid or eid_uid
                    path = video_path + str(tid) + ".avi"
                    fourcc = cv2.VideoWriter_fourcc(*'MGEG')  # video codec
                    out = cv2.VideoWriter(path, fourcc, 20.0, (640, 480))
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

                    # extract problemNum, problem, answer from DB
                    conn = pymysql.connect(host=host, user=DB_user, password=DB_pw, db=DB, charset="utf8")
                    curs = conn.cursor()
                    sql = "select * from test" + eid + ";"
                    curs.execute(sql)
                    result = curs.fetchall()
                    print(result)

                    for i in range(0, len(result)):
                        problemNum = result[i][0]
                        problem = result[i][1]
                        answer = result[i][2]
                        problemInfo = problemNum + '@' + problem + '@' + answer
                        client_socket.send(problemInfo.encode(encoding='ISO-8859-1'))
                        _ = client_socket.recv(1024).decode(encoding='ISO-8859-1')

                    client_socket.send('0'.encode(encoding='ISO8859-1'))

                break

            # when exam code user typed is wrong
            else:
                client_socket.send('-1'.encode(encoding='ISO-8859-1'))
                continue


        elif messages[0] == 'createExam':

            eid = messages[1]
            start_date = messages[2]
            start_time = messages[3]
            end_date = messages[4]
            end_time = messages[5]
            client_socket.send('0'.encode(encoding='ISO-8859-1'))

            exams.append({'eid': eid, 'supervisor': [uid], 'start_time': start_date + start_time, 'end_time': end_date + end_date})
            print("exams\n", exams)

            print(messages)

            conn = pymysql.connect(host=host, user=DB_user, password=DB_pw, db=DB, charset="utf8")
            curs = conn.cursor()
            sql = "insert into Exam(eid,startdate,enddate,starttime,endtime,uid) values (%s,%s,%s,%s,%s,%s)"
            curs.execute(sql, (eid, start_date, end_date, start_time, end_time, uid))
            conn.commit()
            print("exam created")

            # create exam table
            curs.execute('create table ' + "test" + eid + '(problemNum text, question text,answer text)')
            conn.commit()

            while True:
                recv = client_socket.recv(1024).decode(encoding='ISO-8859-1')
                messages = recv.split('@')

                if messages[0] == 'newProblem':
                    problemNum = messages[1]
                    question = messages[2]
                    answer = messages[3]
                    client_socket.send('1'.encode(encoding='ISO-8859-1'))

                    print("eid:", eid, messages)

                    conn = pymysql.connect(host=host, user=DB_user, password=DB_pw, db=DB, charset="utf8")
                    curs = conn.cursor()
                    sql = "insert into test" + eid + "(problemNum,question,answer) values (%s,%s,%s)"
                    print(sql)

                    curs.execute(sql, (problemNum, question, answer))
                    conn.commit()
                    print("exam created")

                elif messages[0] == 'complete':
                    client_socket.send('1'.encode(encoding='ISO-8859-1'))
                    break

    while True:
        # supervisor[1] -> socket
        if is_supervisor == False and len(supervisor) != 1:
            client_socket.send('1'.encode(encoding='ISO-8859-1'))
            supervisor_socket = supervisor[1]
            break

    # send webcam image received from candidates to supervisor
    while not is_supervisor:
        try:
            data = client_socket.recv(1).decode(encoding='ISO-8859-1')

            # when candidate submitted answers
            if data == '0':
                answerInfo = client_socket.recv(1).decode(encoding='ISO-8859-1')
                messages = answerInfo.split('@')
                uid = messages[1]
                for i in range(0, len(messages) - 2):
                    print(messages[i])
                break

            length = client_socket.recv(16).decode(encoding='ISO-8859-1')
            stringData = recvall(client_socket, int(length))  # stringData = imgData + cheatData
            client_socket.send('1'.encode(encoding='ISO-8859-1'))

            imgData, cheatData = stringData[:-1], stringData[-1]
            data = np.frombuffer(imgData, dtype='uint8')
            decimg = cv2.imdecode(data, 1)
            out.write(decimg)

            lock.acquire()
            supervisor_socket.send(uid.encode(encoding='ISO-8859-1'))
            supervisor_socket.send(str(len(stringData)).ljust(16).encode(encoding='ISO-8859-1'))
            supervisor_socket.send(stringData)  # stringData = imgData + cheatData
            supervisor_socket.recv(1).decode(encoding='ISO-8859-1')
            lock.release()

        except Exception as e:
            lock.release()
            supervisor.pop(1)
            break

    while is_supervisor:
        try:
            pass

        except Exception as e:
            supervisor.pop(1)
            break

    client_socket.close()
    print("DISCONNECT BY : ", addr)


def main():
    global port

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # SOCK.STREAM : TCP, SOCK.DGRAM : UDP
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', port))  # '' => INADDR_ANY

    print("WAITING FOR CLIENT...")

    server_socket.listen()

    while True:
        client_socket, addr = server_socket.accept()
        start_new_thread(thread_webcam, (client_socket, addr,))

    server_socket.close()


if __name__ == "__main__":
    main()
