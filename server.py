import logging
import threading
import tkinter as tk
from tkinter import PhotoImage
import socket
from dataclasses import dataclass

import pyautogui
import keyboard


@dataclass
class Gui:
    image: str = "screen.png"
    fps: int = 60

    def __init__(self):
        self.root_ = tk.Tk()
        self.widgets()
        self.update_fps()

    def widgets(self):
        self.label = tk.Label(self.root_)
        self.label.pack()

    def change_image(self, new_image: bytes):
        new_screen_image = PhotoImage(data=new_image)
        self.label.configure(image=new_screen_image)
        self.label.image = new_screen_image

    def load_window(self):
        self.root_.mainloop()

    def update_fps(self):
        try:
            with open(self.image, "rb") as image_file:
                image_data = image_file.read()
                self.change_image(image_data)
        except FileNotFoundError:
            logging.warning(f"Image not found: {self.image}")

        self.root_.after(int(1000 / self.fps), self.update_fps)

    def get_mouse_axis(self):
        position = pyautogui.position()
        logging.debug("X,Y", position)
        return position

    def get_keyboard_input(self):
        event = keyboard.read_event()
        if event.name == "unknown":
            return None
        if event.event_type == keyboard.KEY_DOWN:
            return event.name


@dataclass
class Server:
    socket_: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mouse_socket_: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    keyboard_socket_: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    port_: int = 1234
    host_ip_: str = "192.168.24.135"

    def __init__(self, gui: Gui):
        self.gui_ = gui

    def start_server(self):
        logging.info("starting server")
        with self.socket_ as sock:
            sock.bind((self.host_ip_, self.port_))
            file_size = 0
            image_data = b""

            while True:
                try:
                    packet_size = 8192
                    data, addr = sock.recvfrom(packet_size)
                    self.addr_ = addr  # register address
                    if data.startswith(b"SIZE"):
                        file_size = int(data.split()[1])
                        logging.debug(f"got size {file_size}")
                    elif data.startswith(b"END"):
                        self.process_image(image_data)
                        image_data = b""
                        logging.debug(f"reached the end of picture")
                    elif data:
                        logging.debug("data", len(image_data))
                        image_data += data

                except Exception as e:
                    logging.error(f"Error: {e}")
                    sock.close()
                    break

    def process_image(self, image_data):
        with open(self.gui_.image, "wb") as file:
            file.write(image_data)
        with open(self.gui_.image, "rb") as image_file:
            image_data = image_file.read()
            self.gui_.change_image(image_data)

    def send_keystrokes(self):
        logging.info("sending keystokes")
        with self.keyboard_socket_ as sock:
            sock.bind((self.host_ip_, self.port_ + 1))
            sock.listen()
            conn, addr = sock.accept()
            with conn:
                logging.info("connection accepted by", addr)
                while True:
                    keystroke = self.gui_.get_keyboard_input()
                    if keystroke:
                        logging.info(f"{type(keystroke)}")
                        conn.send(keystroke.encode("utf-8"))
                        logging.info(f"sending keystroke")

    def send_mouse_axis(self):
        while True:
            with self.mouse_socket_ as sock:
                position = self.gui_.get_mouse_axis()
                message = b"AXIS %d %d" % (position.x % position.y)
                # sock.

    def send_mouse_click_status(self):
        pass


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    gui = Gui()
    server = Server(gui)
    server.socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.keyboard_socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_th = threading.Thread(target=server.start_server)
    keyboard_th = threading.Thread(target=server.send_keystrokes)

    server_th.start()
    keyboard_th.start()

    gui.load_window()
    server_th.join()
    keyboard_th.join()
