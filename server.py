#this is the server to recive the file to decrypt the file and store it into 
#the file system


from typing import Final , NoReturn, NewType

import logging
import os
import threading
import random
import socket
import json
import tqdm 
from cryptography.fernet import Fernet
import dotenv
dotenv.load_dotenv()
#this is the size of the buffer when reciving from the server
BUFFER_SIZE: Final= 1024
#this is the number of character to check for a the end of the byte stream
END_TAG:Final = -5
END_MESSAGE:Final[bytes] = os.getenv("END_MESSAGE",default="").encode()
DIGEST_KEY:Final[bytes] =os.getenv("DIGEST_KEY",default="") .encode()
PORT: Final[int] = int(os.getenv("PORT",default=0000))
HOST: Final[str] = os.getenv("HOST",default="127.0.0.1")
#time out for the server to close if no connections
TIME_OUT:Final = 25.0
#log file name
LOG_FILE:Final[str] = "tcp-log.log"
#encode type for the log file
ENCODER:Final[str] = 'utf-8'
#level for the log file
LOG_LEVEL:Final = logging.DEBUG
#new type for the socket address becuase Retaddress it not working
Socket_Address = NewType("Socket_Address",str)
#logging types are aliases for ints but i want the type checker to make sure they are of the same type
#so im going to type cast them to the loggType
LoggType = NewType("LoggType",int)



#will raise for bad input instead of handling becuse i want it to stop the program
#if the log file fails
def valid_input(log_file:str,etype:str,debug_level:LoggType) ->None:
    #cast all of the logging levels to log type 
    check:list[LoggType] = [LoggType(logging.DEBUG), LoggType(logging.INFO), LoggType(logging.WARNING),LoggType(logging.ERROR),LoggType(logging.WARN)]
    if log_file == " " or not type(log_file) == str:
        raise ValueError("invalid input for the log file")
    if etype == " " or not type(etype) == str:
        raise ValueError("invalid input for encoding type")
    if debug_level not in check:
        raise ValueError("invalid input for debugging level")
    return


def configure_logging(
    log_file:str, 
    encoding_type:str,
    debug_level:LoggType
) -> None:
    path = os.path.join(os.getcwd(), "log-files")
    logging.getLogger()
    valid_input(log_file,encoding_type,debug_level)
    #check if the dir for the log files exits if not create it 
    if not os.path.exists(path):
        os.makedirs(path,exist_ok=False)
    logging.basicConfig(filename=os.path.join(path,log_file),encoding=encoding_type,level=debug_level,filemode='a')


def init_fernet(key:str)-> Fernet:
    return Fernet(key)

def init_socket(*,host:str,port) -> socket.socket:
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        s.bind((host,port))
        logging.info(f"socket created, port:{port}, host:{host}")
    except socket.error :
        logging.fatal("socket faild to bind")
        raise socket.error("there was an error when binding the socket")
    except Exception as e:
        logging.fatal(f"unknown error when binding: {e}")
        BaseException("there was an unexpected error")
    return s


#put this in its own fucntion so i can handle deserializing specific errors
def deseralize_data(data:str,addr:Socket_Address)-> tuple[str,int]:
    fn = None
    fs = None
    try:
        deseralized:dict[str,str] = json.loads(data)
        fn = deseralized["file_name"]
        fs = deseralized["file_size"]
    except (json.JSONDecodeError, KeyError):
        logging.warning(f"error when deserializing client data from :{addr}")
        raise ValueError("failed when deserializing data")
    return fn,int(fs)

def recive_file_details(conn:socket.socket,addr:Socket_Address) ->tuple[str,int]:
    #have to declare because of possibe unbond error
    try:
        data = conn.recv(BUFFER_SIZE).decode()
        file_name,file_size = deseralize_data(data,addr)
        print(f"recived:\n file_name: {file_name}, file_size: {file_size}\n from:\n address: {addr}")
        logging.info(f"recived:\n file_name: {file_name}, file_size: {file_size}\n from:\n address: {addr}")
    except Exception as e:
        logging.warning(f"error when reciving data from client: {addr}, {e}")
        raise socket.error("there was an error when reciving the file details")
    return file_name,file_size

def build_file_data(conn:socket.socket,size:int, addr:Socket_Address) -> bytes:
    done = False
    file_bytes = b" "
    # completion = 1
    # progress = tqdm.tqdm(unit="B",unit_scale=True,unit_divisor=1000,total=int(size))
    while not done:
        try:
            data = conn.recv(BUFFER_SIZE)
            if file_bytes[END_TAG:] == END_MESSAGE:
                done = True
            else:
                # completion += 1
                file_bytes+=data
                # n = (completion / size) * 100
                # sys.stdout.write(u"\u001b[1000D" + str(n) + "%")
                # sys.stdout.flush()
                
            # progress.update(BUFFER_SIZE)
        except Exception as e:
            logging.warning(f"error when build file for client:{addr}, {e}")
            raise BaseException( "there was an error when building the file bytes")
    return file_bytes


def decrypt_data(data:bytes) -> bytes:
    fer = Fernet(key=DIGEST_KEY)
    try:
        e = fer.decrypt(data[:END_TAG])
    except Exception as e:
        logging.warning(f"error when decrypting client bytes, {e}")
        raise BaseException("there was an error when decrypting the data")
    return e

def write_to_file(file_name:str,data:bytes)-> None:
    number = random.randint(1,100) 
    new_file_name = "server_" +str(number) +file_name
    out_dir = os.path.join(os.getcwd(),"server-files")
    try:
        with open(os.path.join(out_dir,new_file_name),'wb') as f:
            f.write(decrypt_data(data))
    except Exception as e:
        logging.warning(f"error when writting to file, {e}")
        raise BaseException("there was an error when writing to the file")

def close_client(conn:socket.socket, addr:Socket_Address) -> None:
    try:
        conn.close()
        logging.info(f"client socket {addr} closed")
    except Exception as e:
        logging.error(f"failed to close socket for client:{addr}, {e}")
        raise socket.error(f"problem closing socket {addr}")

def handle_connections(conn:socket.socket, addr:Socket_Address) ->  None:
    file_name,file_size = recive_file_details(conn,addr)
    file_bytes = build_file_data(conn,file_size, addr)
    write_to_file(file_name,file_bytes)
    close_client(conn,addr)


#this is a check for the dir that the transfered files will be stored
def create_out_dir():
    try:
        os.makedirs(os.path.join(os.getcwd() ,"server-files"),exist_ok=False)
        logging.info("creating dir to hold client files")
    except FileExistsError :
        pass
    except:
        logging.fatal("failed to create directory for client files")
        raise OSError("there was an unexpected error when creating the directory ")

#no return because either runs forever or is exited from os
def main() -> NoReturn:
    #make sure to cast the logg level to the loggtype
    configure_logging(LOG_FILE,ENCODER,LoggType(LOG_LEVEL))
    s = init_socket(host=HOST,port=PORT)
    s.listen()
    s.settimeout(TIME_OUT)
    logging.info(f"server timeout set at {TIME_OUT}")
    create_out_dir()
    while True:
        try:
            client,address = s.accept()
            t = threading.Thread(target=handle_connections,args=(client,address))
            t.start()
        except socket.timeout:
            print("the server has safely timed out!!")
            s.close()
            logging.info("the server has been successfully closed")
            logging.shutdown()
            os._exit(0)
main()