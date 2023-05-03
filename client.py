#this is the client that will encypt the file and send the encrypted 
#bytes to the sever to be saved in its file system

from typing import Final,Tuple,NoReturn
from cryptography.fernet import Fernet
import os
import socket
import dotenv
import json
dotenv.load_dotenv()

#the key for the ecryption and decryption need to be the same
#fernet.generate_key will not always return the same key
#so i have to use the same key as a constant in both the server and the client
#NOTE the end message and the key both have to be in binary form
END_MESSAGE:Final[bytes] = os.getenv("END_MESSAGE",default="").encode()
DIGEST_KEY:Final[bytes] =os.getenv("DIGEST_KEY",default="").encode()
PORT: Final[int] = int(os.getenv("PORT",default=0000))
HOST: Final[str] = os.getenv("HOST","127.0.0.1")

#this will return all of the data regarding the file including path and name
def get_file_info() -> Tuple[str,str]:
    file_type = input("what is the type of file you wish to send?\n")
    file_name = input("what is the name of the file you wish to send?\n")
    choice = input("is the file you wish to send in this directrory?\n").lower()
    built_file = file_name + '.' + file_type
    path = ""
    if choice[0] == 'y':
        path = os.path.join(os.getcwd(),built_file)
    else:
        _dir = input("please enter the path to the directory where the file you entered is(absolute)\n")
        path = os.path.join(_dir,built_file)
    return path,built_file

def handle_file_exception(file_name:str,p:str) ->Tuple[str,bytes]:
    # need to declare these becuse of possible ubnounded error
    f = " "
    d = b""
    c = input(f"file: {file_name} was not found!\n would you like to enter another file\n").lower()
    if c[0] == 'y':
        p,f = get_file_info()
        try:
            with open(p,'rb') as file:
                d = file.read()
        except:
            raise BaseException("there was an error when handling the excpetion for the get_file function")
    return f,d

#this file will be for getting file data and the file name 
#this function will always return to me a tuple of filename:str data:bytes
def get_file() ->Tuple[str,bytes]:
    path,file_name = get_file_info()
    try:
        with open(path,'rb') as f:
            data = f.read()
    except FileNotFoundError:
        return handle_file_exception(file_name,path) 
    except:
        raise BaseException("there was a unexpected error")
    return file_name,data


def get_size(b:bytes) -> int:
    return len(b)

def encrypt_data(data:bytes) -> bytes:
    fer = Fernet(key=DIGEST_KEY) 
    try:
        e = fer.encrypt(data)
    except:
        raise BaseException("there was an error when encrypting the data")
    return e

def serialize_data(file_name:str, file_size:int) -> bytes:
    if file_name == "" or file_size <= 0:
        raise ValueError("invalid file data")
    try:
        obj ={
            "file_name": file_name,
            "file_size" :file_size
        }
        serialized = json.dumps(obj)
    except:
        raise BaseException("error when serializing the data")
    return serialized.encode()

def send_to_server(*,conn:socket.socket,file_name:str, file_size:int,encypted_data:bytes) -> None:
    print(f"file size: {file_size}")
    print(f"file name: {file_name}")
    try:
        conn.send(serialize_data(file_name,file_size))
        conn.sendall(encypted_data)
        conn.send(END_MESSAGE)
    except socket.error:
        raise socket.error("there was an error when sending off the data ")
    except:
        raise BaseException("there was an unexpected error")
    finally:
        conn.close()


def main() ->NoReturn:
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.connect((HOST,PORT))
    file_info,data = get_file()
    size = get_size(data)
    encrypted = encrypt_data(data)
    send_to_server(conn=server,file_name=file_info,file_size=size,encypted_data=encrypted)
    print("YOUR FILE HAS BEEN SENT OFF TO THE SERVER!!")
    os._exit(0)
    

main()