import socket
from dataclasses import dataclass
from typing import Any
from PIL import ImageGrab
from dataclasses import dataclass
import threading
import io
import time
import logging
import pyautogui


@dataclass
class Client:
    screen_width_: int = 500
    screen_height_: int = 500
    socket_: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mouse_socket_: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    keyboard_socket_: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port_: int = 1234
    host_ip_: str = "127.0.0.1"  # client target ip

    def start_client(self):
        with self.socket_ as sock:
            address = (self.host_ip_, self.port_)
            while True:
                screenshot_data = self.get_screenshot()
                size = len(screenshot_data)
                sock.sendto(b"SIZE %d" % size, address)
                self.send_image(address, screenshot_data, size)
                #logging.debug("finished sending image chunks")
                sock.sendto(b"END", address)
                time.sleep(0.005)

    def start_mouse(self):
        logging.debug(f"setting mouse position {X,Y}")
        with self.mouse_socket_ as sock:
            address = (self.host_ip_, self.port_)
            packet_size = 500
            while True:
                data, addr = sock.recvfrom(packet_size)
                data = data.split()
                if data.startswith(b"CLICK"):
                    click = data[1]
                    self.set_mouse_click(click)
                    logging.debug(f"setting click {click}")
                elif data.startswith(b"AXIS"):
                    X, Y = int(data[1]), int(data[2])
                    self.set_mouse_axis(X, Y)
                    logging.debug(f"setting mouse position {X,Y}")

    def get_screenshot(self):
        screenshot = ImageGrab.grab(
            bbox=(0, 0, self.screen_width_, self.screen_height_)
        )
        img_arr = io.BytesIO()
        screenshot.save(img_arr, format="PNG", optimize=True)
        return img_arr.getvalue()

    def start_keyboard(self):
        logging.info("start keyboard")
        with self.keyboard_socket_ as sock:
            packet_size = 512
            sock.connect((self.host_ip_,self.port_ + 1))
            logging.info("connected!")
            while True:
                data = sock.recv(packet_size)
                logging.info(f"press {data}")
                pyautogui.typewrite(data)
                logging.debug(f"typed {data}")

    def set_mouse_axis(self, x, y):
        if pyautogui.onScreen(self.screen_width_, self.screen_height_):
            pyautogui.moveTo(x, y)

    def set_mouse_click(self, x, y, click):
        if pyautogui.onScreen(self.screen_width_, self.screen_height_, click):
            if click == None:
                return
            if click == pyautogui.LEFT:
                pyautogui.leftClick(x, y)
            elif click == pyautogui.RIGHT:
                pyautogui.rightClick(x, y)
            else:
                pyautogui.middleClick(x, y)

    def send_image(self, address, screenshot_data, size):
        packet_size = 8192
        for i in range(0, size, packet_size):
            chunk = screenshot_data[i : i + packet_size]
            self.socket_.sendto(chunk, address)
            time.sleep(0.001)


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)
    client = Client()
    # debug...
    client.socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_th = threading.Thread(target=client.start_client)
    #mouse_th = threading.Thread(target=client.start_mouse)
    keyboard_th = threading.Thread(target=client.start_keyboard)

    client_th.start()
    #mouse_th.start()
    keyboard_th.start()

    client_th.join()
    #mouse_th.join()
    keyboard_th.join()
