from machine import Pin, I2C, ADC, lightsleep
from ssd1306 import SSD1306_I2C
#from sh1106 import SH1106_I2C  # only for sh1106 display
import sys
import os
import random
import math
import re
import utime
import bme280


# board temperature sensor
board_temp_sensor = ADC(4)
conversion_factor = 3.3 / (65535)

# DC voltage sensor
adc2 = machine.ADC(28)

# display size
pix_res_x = 128
pix_res_y = 64

# push buttons
button_back = Pin(0, Pin.IN, Pin.PULL_UP)
button_ok = Pin(1, Pin.IN, Pin.PULL_UP)
button_r = Pin(2, Pin.IN, Pin.PULL_UP)
button_up = Pin(3, Pin.IN, Pin.PULL_UP)
button_l = Pin(4, Pin.IN, Pin.PULL_UP)
button_down = Pin(5, Pin.IN, Pin.PULL_UP)

light_pin = Pin(15, Pin.OUT)
battery_transistor = Pin(22, Pin.OUT)

wakeup_flag = False
def wakeup_handler(pin):
    global wakeup_flag
    wakeup_flag = True

# wakeup button
button_ok.irq(trigger=Pin.IRQ_FALLING, handler=wakeup_handler)

led1 = Pin(18, Pin.OUT)

time_offset = 0

# BME280 temperature and air pressure sensor
i2c=I2C(0, sda=Pin(16), scl=Pin(17), freq=100000)  # initializing the I2C method
bme = bme280.BME280(i2c=i2c)  # create BME280 object

def init_i2c(scl_pin, sda_pin, freq):  # Initialize I2C device
    i2c_dev = I2C(1, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
    i2c_addr = [hex(i) for i in i2c_dev.scan()]
    
    if not i2c_addr:
        print('No I2C Device Found')
        sys.exit()
    else:
        print(f"I2C Address      : {i2c_addr[0]}")
        print(f"I2C Configuration: {i2c_dev}")
    
    return i2c_dev

i2c_dev = init_i2c(scl_pin=27, sda_pin=26, freq=800000)
oled = SSD1306_I2C(pix_res_x, pix_res_y, i2c_dev)
#oled = SH1106_I2C(pix_res_x, pix_res_y, i2c_dev)  # only for sh1106 display
#oled.rotate()

def enter_sleep():
    global wakeup_flag
    wakeup_flag = False
    while not wakeup_flag:
        utime.sleep_ms(1)

def load_time_from_file():
    try:
        with open("time.txt", "r") as file:
            data = file.read().strip()
            saved_time = [int(x) for x in data.split(",")]
            print("Saved time:", saved_time)

            current_time = list(utime.localtime())

            # check if localtime is already up to date
            if saved_time > current_time:
                print("Setting time from file...")
                set_time(*saved_time[:6])
            else:
                print("utime.localtime is already up to date.")

    except Exception as e:
        print("No time found or error loading file:", e)
        
def save_time_to_file():
    try:
        current_time = get_adjusted_time()
        with open("time.txt", "w") as file:
            file.write(",".join(map(str, current_time[:6])))  # save time like: yyyy,mm,dd,hh,mm,ss
    except Exception as e:
        print("Error saving time:", e)

def get_adjusted_time():
    current_time = utime.time() + time_offset
    return utime.localtime(current_time)

def set_time(year, month, day, hour, minute, second):
    global time_offset
    # convert to seconds since 2000-01-01
    desired_time = utime.mktime((year, month, day, hour, minute, second, 0, 0))
    current_time = utime.time()
    time_offset = desired_time - current_time

def adjust_time():
    global time_offset  # offset for localtime

    while True:
        current_time = list(get_adjusted_time())  # tupel to list
        
        oled.fill(0)
        oled.text(f"{current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d}", 24, 24)
        oled.text(f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}", 32, 40)
        oled.show()
        
        utime.sleep(0.25)
        set_select = 5

        while True:
            current_time = list(get_adjusted_time())
            
            oled.fill(0)
            oled.text(f"{current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d}", 24, 24)
            oled.text(f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}", 32, 40)
            oled.text(f"Set: {set_select}", 32, 0)
            oled.show()

            if button_back.value() == 0 or button_ok.value() == 0:
                utime.sleep(0.5)
                return
            
            if button_r.value() == 0:
                set_select = (set_select + 1) % 6
                utime.sleep(0.25)
            if button_l.value() == 0:
                set_select = (set_select - 1) % 6
                utime.sleep(0.25)

            if button_up.value() == 0:
                current_time[set_select] += 1
                utime.sleep(0.1)
            if button_down.value() == 0:
                current_time[set_select] -= 1
                utime.sleep(0.1)

            set_time(*current_time[:6])
            
def battery_status(cx, cy, c):
    battery_transistor.on()
    utime.sleep_ms(10)
    adc_voltage = adc2.read_u16() * (3.3/65536) * 2
    battery_transistor.off()
    max_voltage = 4.15
    min_voltage = 3.7
    battery_percentage = (adc_voltage - min_voltage) / (max_voltage - min_voltage) * 100  # needs some finetuning for different batteries or resistors

    oled.line(cx, cy+1, cx, cy+6, c)
    oled.pixel(cx+1, cy+1, c)
    oled.pixel(cx+1, cy+6, c)
    oled.pixel(cx+2, cy+1, c)
    oled.pixel(cx+2, cy+6, c)
    oled.line(cx+2, cy, cx+19, cy, c)
    oled.line(cx+2, cy+7, cx+19, cy+7, c)
    oled.line(cx+20, cy, cx+20, cy+7, c)
    
    for i in range(int(battery_percentage+10) // 20):
        oled.rect(cx+17-3*i, cy+2, 2, 4, c)
    
    oled.text(f"   {int(round(battery_percentage, -1))}%", cx, cy)

def board_temp():  # temperature in °C
    value_a = board_temp_sensor.read_u16()
    voltage = value_a * conversion_factor
    board_temp = 27 - (voltage - 0.706) / 0.001721
    return board_temp

def cross(cx, cy, s, c):  # center x, center y, height, color[0;1]
    oled.line((cx-s), (cy-s), (cx+s), (cy+s), c)
    oled.line((cx+s), (cy-s), (cx-s), (cy+s), c)

def circle(cx, cy, r, c):  # center x, center y, radius, coulor[0;1]
    for angle in range(0, 90, 2): #in 2 Sekunden
        y = int(r*math.sin(math.radians(angle)))
        x = int(r*math.cos(math.radians(angle)))
        oled.pixel(cx-x, cy+y, c)
        oled.pixel(cx-x, cy-y, c)
        oled.pixel(cx+x, cy+y, c)
        oled.pixel(cx+x, cy-y, c)

def clock(cx, cy, r, c):  # x-center, y-center, radius, coulor[0;1]
    for i in range(12):  # 12 hours
        angle = math.radians(i * 30)  # 30° steps for each hour
        x1 = int(cx + r * math.cos(angle))
        y1 = int(cy + r * math.sin(angle))
        x2 = int(cx + (r - 6*(r/32)) * math.cos(angle))
        y2 = int(cy + (r - 6*(r/32)) * math.sin(angle))
        
        oled.line(x1, y1, x2, y2, c)

def draw_hand(cx, cy, length, angle, c):
    x2 = int(cx + length * math.cos(math.radians(angle)))
    y2 = int(cy + length * math.sin(math.radians(angle)))
    oled.line(cx, cy, x2, y2, c)

def draw_clock(cx, cy, r, c):
    year, month, day, hour, minute, second, wday, _ = get_adjusted_time()

    sec_angle = 270 + second * 6  # 360°/60s → 6° per second
    min_angle = 270 + minute * 6  # 360°/60min → 6° per minute
    hour_angle = 270 + (hour % 12) * 30 + (minute / 2)  # 360°/12h → 30° per hour

    clock(cx, cy, r, c)  # draws the clock
    
    # Zeiger zeichnen
    draw_hand(cx, cy, int(r * 0.45), hour_angle, 1)  # hour hand
    draw_hand(cx, cy, int(r * 0.7), min_angle, 1)    # minute hand
    draw_hand(cx, cy, int(r * 0.9), sec_angle, 1)    # second hand

def draw_time(cx, cy, c):
    year, month, day, hour, minute, second, wday, _ = get_adjusted_time()
    if (wday == 0):
        wday_name = "mon"
    elif (wday == 1):
        wday_name = "tue"
    elif (wday == 2):
        wday_name = "wed"
    elif (wday == 3):
        wday_name = "thu"
    elif (wday == 4):
        wday_name = "fri"
    elif (wday == 5):
        wday_name = "sat"
    elif (wday == 6):
        wday_name = "sun"
    battery_status(cx, cy-11, c)
    oled.text(f"{day:02d}.{month:02d}", cx, cy)
    oled.text(f"{year}", cx, cy+11)
    oled.text(f"{wday_name}", cx, cy+22)
    oled.text(bme.values[0], cx, cy+33)
    oled.text(f"{hour:02d}:{minute:02d}:{second:02d}", cx, cy+44)

def show_watch():
    oled.fill(0)
    draw_time(0, 12, 1)
    circle(96, 32, 32, 1)
    draw_clock(96, 32, 31, 1)
    oled.show()
    
def watch_menu():
    utime.sleep(0.25)
    oled.fill(0)
    app_list = [
        [("adjust time", "adjust_time"),
         ("light", "light_on"),
         ("snake", "snake_game"),
         ("pong", "pong_game"),
         ("calculator", "calculator_app")],
        [("dino", "dino_game"),
         ("future update", "future_update")]
        ]
    
    app_select = 0
    page_nr = 0
    
    while True:
        # list available applications
        for i in range(len(app_list[page_nr])):
            app_name, _ = app_list[page_nr][i]
            oled.text(f"* {app_name}", 0, 12*i+2)
        
        oled.rect(0, (12*app_select), 128, 12, 1)
        oled.show()
        
        # return to watch
        if button_back.value() == 0 or button_l.value() == 0:
            return
        
        # choose app
        if button_up.value() == 0:
            app_select = (app_select - 1)
            if app_select < 0 and page_nr > 0:
                page_nr -= 1
                app_select = len(app_list[page_nr])-1
            elif app_select < 0:
                app_select = len(app_list[page_nr])-1
            utime.sleep(0.25)
        if button_down.value() == 0:
            app_select = (app_select + 1)
            if app_select >= len(app_list[page_nr]) and page_nr < len(app_list)-1:
                page_nr += 1
                app_select = 0
            elif app_select >= len(app_list[page_nr]):
                app_select = 0
            utime.sleep(0.25)
        
        oled.fill(0)
        
        # execute selected app
        if button_ok.value() == 0 or button_r.value() == 0:
            app_name, app_func = app_list[page_nr][app_select]
            exec(f"app = {app_func}")
            app()

def return_to_menu():
    oled.fill(0)
    oled.text("returning", 26, 26)
    oled.text("to the menu ...", 6, 38)
    oled.show()
    utime.sleep(0.5)

light_status = 0
def light_on():
    global light_status
    if light_status:
        light_pin.off()
        light_status = 0
    else:
        light_pin.on()
        light_status = 1
    utime.sleep(0.5)

""" snake application """
class Vector2:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if self.x == other.x and self.y == other.y:
            return True
        return False

    def __add__(self, other):
        new_x = self.x + other.x
        new_y = self.y + other.y
        return Vector2(new_x, new_y)

    def __sub__(self, other):
        new_x = self.x - other.x
        new_y = self.y - other.y
        return Vector2(new_x, new_y)

    def __str__(self):
        return(self.x, self.y)

class Draw:
    def __init__(self, oled):
        self.oled = oled

    def draw(self, x, y, size):
        self.oled.fill_rect(x, y, size, size, 1)

    def reset(self):
        self.oled.fill_rect(0, 0, 132, 64, 0)

    def show(self, score):
        oled.text(f'{score}', 0, 56)
        self.oled.show()

draw = Draw(oled)

cell_x_num = 16
cell_y_num = 8
cell_size = 8

def snake_random(rmin, rmax):
    return utime.ticks_ms() % (rmax - rmin) + rmin

class Fruit:
    def __init__(self, oled):
        x = snake_random(0, cell_x_num)
        y = snake_random(0, cell_y_num)
        self.pos = Vector2(x, y)
        self.oled = oled

    def random(self):
        x = snake_random(0, cell_x_num)
        y = snake_random(0, cell_y_num)
        self.pos = Vector2(x, y)

    def draw(self):
        self.oled.fill_rect((self.pos.x) * cell_size + cell_size // 3,
                            (self.pos.y) * cell_size + cell_size // 3,
                             cell_size // 2, cell_size // 2, 1)

    def get_pos(self):
        return self.pos

fruit = Fruit(oled)

class Snake:
    def __init__(self) -> None:
        self.body = [Vector2(cell_x_num // 2, cell_y_num // 2)]
        self.add_to_body = 2
        self.set_direction = Vector2(1, 0)
        self.direction = Vector2(1, 0)
        self.score = 0
        self.highscore = 0

    def init(self, clas):
        self.snak = clas

    def game_over(self):
        self.body = [Vector2(cell_x_num // 2, cell_y_num // 2)]
        self.add_to_body = 2
        self.set_direction = Vector2(1, 0)
        self.direction = Vector2(1, 0)
        oled.fill(0)
        oled.text(f'SCORE: {self.score}', 36, 26)
        oled.show()
        utime.sleep(0.5)
        if (self.score > self.highscore):
            self.highscore = self.score
            for i in range(3):
                oled.text('NEW HIGHSCORE!!!', 2, 38)
                oled.show()
                utime.sleep(0.5)
                oled.fill(0)
                oled.text(f'SCORE: {self.score}', 36, 26)
                oled.show()
                utime.sleep(0.5)
            oled.text('NEW HIGHSCORE!!!', 2, 38)
            oled.show()
        else:
            oled.text(f'HIGHSCORE: {self.highscore}', 18, 38)
            oled.show()
            utime.sleep(1.5)
        utime.sleep(1)
        self.score = 0

    def draw_snake(self):
        draw.reset()
        for block in self.body:
            draw.draw(block.x * cell_size, block.y * cell_size, cell_size)

    def move_snake(self, detect_self_colistion=1):
        self.direction = self.set_direction
        if detect_self_colistion == 1:
            if self.body[0] + self.direction in self.body:
                self.snak.game_over()
        self.body.insert(0, self.body[0] + self.direction)
        if self.add_to_body > 0:
            self.add_to_body -= 1
        else:
            self.body = self.body[:-1]

    def wall_colision(self):
        if self.body[0].x < 0 or self.body[0].x > cell_x_num - 1:
            self.snak.game_over()
            fruit.random()
        elif self.body[0].y < 0 or self.body[0].y > cell_y_num - 1:
            self.snak.game_over()
            fruit.random()

    def fruit_colision(self):
        if self.body[0] == fruit.get_pos():
            self.add_to_body += 1
            self.score += 1
            fruit.random()

    def add_body(self):
        self.add_to_body += 1

    def set_dir(self, newdir):
        self.set_direction = newdir

    def get_dir(self):
        return (self.direction)

    def get_body(self):
        return (self.body)

def snake_game():
    snake = Snake()
    snake.init(snake)
    snake.draw_snake()
    fruit.draw()
    utime.sleep(0.3)
    while button_back.value():
        snake_dir = snake.get_dir()
        if not snake_dir == Vector2(-1, 0):
            if button_r.value() == 0:
                snake.set_dir(Vector2(1, 0))

        if not snake_dir == Vector2(0, 1):
            if button_up.value() == 0:
                snake.set_dir(Vector2(0, -1))

        if not snake_dir == Vector2(1, 0):
            if button_l.value() == 0:
                snake.set_dir(Vector2(-1, 0))

        if not snake_dir == Vector2(0, -1):
            if button_down.value() == 0:
                snake.set_dir(Vector2(0, 1))

        snake.move_snake()
        snake.wall_colision()
        snake.fruit_colision()

        snake.draw_snake()
        fruit.draw()
        draw.show(snake.score)
        utime.sleep(0.3)
    
    return_to_menu()

""" pong application """
class Pong:
    import random
    def __init__(self) -> None:
        self.points_a = 0
        self.points_b = 0
        self.paddle_height = 12
        self.paddle_width = 2
        self.paddle_x1 = 5
        self.paddle_y1 = 26
        self.paddle_x2 = 121
        self.paddle_y2 = 26
        self.ball_x = 64
        self.ball_y = 32
        self.ball_dx = 2
        self.ball_dy = 2  # velocity
        if self.random.random() > 0.5:
            self.ball_dx *= -1
        if self.random.random() > 0.5:
            self.ball_dy *= -1
        self.button_up1 = button_l
        self.button_down1 = button_down
        self.button_up2 = button_up
        self.button_down2 = button_r
        self.speed = 50

    def update_paddles(self):
        if not self.button_up1.value() and self.paddle_y1 > 0:
            self.paddle_y1 -= 2
        if not self.button_down1.value() and self.paddle_y1 < 64 - self.paddle_height:
            self.paddle_y1 += 2
        if not self.button_up2.value() and self.paddle_y2 > 0:
            self.paddle_y2 -= 2
        if not self.button_down2.value() and self.paddle_y2 < 64 - self.paddle_height:
            self.paddle_y2 += 2

    def update_ball(self):
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        # border collision
        if self.ball_y <= 0 or self.ball_y >= 63:
            self.ball_dy = -self.ball_dy

        # paddle collision
        if (self.paddle_x1 <= self.ball_x <= self.paddle_x1 + self.paddle_width and 
            self.paddle_y1 <= self.ball_y <= self.paddle_y1 + self.paddle_height) or \
           (self.paddle_x2 <= self.ball_x <= self.paddle_x2 + self.paddle_width and 
            self.paddle_y2 <= self.ball_y <= self.paddle_y2 + self.paddle_height):
            self.ball_dx = -self.ball_dx
            if self.speed >= 0:
                self.speed -= 5

        # ball leaves field
        if self.ball_x < 0:
            self.points_b += 1
            self.reset_game()
        if self.ball_x > 127:
            self.points_a += 1
            self.reset_game()

    def reset_game(self):
        self.ball_x = 64
        self.ball_y = 32
        self.ball_dx = 2
        self.ball_dy = 2
        if self.random.random() > 0.5:
            self.ball_dx *= -1
        if self.random.random() > 0.5:
            self.ball_dy *= -1
        self.speed = 50
        utime.sleep(1)

    def draw(self):
        oled.fill(0)
        oled.rect(self.paddle_x1, self.paddle_y1, self.paddle_width, self.paddle_height, 1)
        oled.rect(self.paddle_x2, self.paddle_y2, self.paddle_width, self.paddle_height, 1)
        circle(self.ball_x, self.ball_y, 2, 1)
        oled.pixel(self.ball_x, self.ball_y, 1)
        oled.text(f"{self.points_a:02d}:{self.points_b:02d}", 48, 0)

def pong_game():
    pong = Pong()
    pong.update_paddles()
    pong.update_ball()
    pong.draw()
    utime.sleep(1)
    while button_back.value():
        pong.update_paddles()
        pong.update_ball()
        pong.draw()
        oled.show()
        utime.sleep_ms(pong.speed)
    return_to_menu()

""" dino game """
class Obstacle:
    from random import randint
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def move(self, speed):
        global score
        self.x -= speed
        if self.x + self.width < 0:  # Wenn das Hindernis aus dem Bild verschwindet
            self.x = 128 + random.randint(10, 50)  # Setze es neu an eine zufällige Position rechts
            score += 1
    
    def draw(self):
        oled.rect(self.x, self.y, self.width, self.height, 1)

class Dino:
    def __init__(self) -> None:
        self.highscore = 0
        self.dino_x = 12
        self.dino_y = 40
        self.dino_width = 14
        self.dino_height = 20
        self.jump_status = 0
        self.jump_path = [0, 8, 7, 6, 5, 4, 3, 2, 1, 0, -1, -2, -3, -4, -5, -6, -7, -8]
        self.jump_duration = 0
        self.terrain_x_offset = 0
        self.dino_animation_status = 0
        
        self.dino0_map = [
            (11, 1), (12, 1), (13, 1), (14, 1), (15, 1), (16, 1), (17, 1), (18, 1), 
            (10, 2), (11, 2), (14, 2), (15, 2), (16, 2), (17, 2), (18, 2), (19, 2),
            (10, 3), (11, 3), (14, 3), (15, 3), (16, 3), (17, 3), (18, 3), (19, 3),
            (10, 4), (11, 4), (12, 4), (13, 4), (14, 4), (15, 4), (16, 4), (17, 4), (18, 4), (19, 4),
            (10, 5), (11, 5), (12, 5), (13, 5), (14, 5), (15, 5), (16, 5), (17, 5), (18, 5), (19, 5), 
            (10, 6), (11, 6), (12, 6), (13, 6), (14, 6), 
            (10, 7), (11, 7), (12, 7), (13, 7), (14, 7), (15, 7), (16, 7), (17, 7), 
            (0, 8), (9, 8), (10, 8), (11, 8), (12, 8), (13, 8), 
            (0, 9), (8, 9), (9, 9), (10, 9), (11, 9), (12, 9), (13, 9), 
            (0, 10), (1, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (11, 10), (12, 10), (13, 10), (14, 10), (15, 10), 
            (0, 11), (1, 11), (2, 11), (5, 11), (6, 11), (7, 11), (8, 11), (9, 11), (10, 11), (11, 11), (12, 11), (13, 11),  (15, 11), 
            (0, 12), (1, 12), (2, 12), (3, 12), (4, 12), (5, 12), (6, 12), (7, 12), (8, 12), (9, 12), (10, 12), (11, 12), (12, 12), (13, 12),  
            (0, 13), (1, 13), (2, 13), (3, 13), (4, 13), (5, 13), (6, 13), (7, 13), (8, 13), (9, 13), (10, 13), (11, 13), (12, 13), (13, 13), 
            (1, 14), (2, 14), (3, 14), (4, 14), (5, 14), (6, 14), (7, 14), (8, 14), (9, 14), (10, 14), (11, 14), (12, 14),
            (2, 15), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15), (10, 15), (11, 15), (12, 15), 
            (3, 16), (4, 16), (5, 16), (6, 16), (7, 16), (8, 16), (9, 16), (10, 16), (11, 16), 
            (4, 17), (5, 17), (6, 17), (7, 17), (8, 17), (9, 17), (10, 17), 
            (5, 18), (6, 18), (7, 18), (9, 18), (10, 18), 
            (5, 19), (6, 19), (10, 19), 
            (5, 20), (10, 20), 
            (5, 21), (6, 21), (10, 21), (11, 21)]
        self.dino1_map = [
            (11, 1), (12, 1), (13, 1), (14, 1), (15, 1), (16, 1), (17, 1), (18, 1), 
            (10, 2), (11, 2), (14, 2), (15, 2), (16, 2), (17, 2), (18, 2), (19, 2),
            (10, 3), (11, 3), (14, 3), (15, 3), (16, 3), (17, 3), (18, 3), (19, 3),
            (10, 4), (11, 4), (12, 4), (13, 4), (14, 4), (15, 4), (16, 4), (17, 4), (18, 4), (19, 4),
            (10, 5), (11, 5), (12, 5), (13, 5), (14, 5), (15, 5), (16, 5), (17, 5), (18, 5), (19, 5), 
            (10, 6), (11, 6), (12, 6), (13, 6), (14, 6), 
            (10, 7), (11, 7), (12, 7), (13, 7), (14, 7), (15, 7), (16, 7), (17, 7), 
            (0, 8), (9, 8), (10, 8), (11, 8), (12, 8), (13, 8), 
            (0, 9), (8, 9), (9, 9), (10, 9), (11, 9), (12, 9), (13, 9), 
            (0, 10), (1, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (11, 10), (12, 10), (13, 10), (14, 10), (15, 10), 
            (0, 11), (1, 11), (2, 11), (5, 11), (6, 11), (7, 11), (8, 11), (9, 11), (10, 11), (11, 11), (12, 11), (13, 11),  (15, 11), 
            (0, 12), (1, 12), (2, 12), (3, 12), (4, 12), (5, 12), (6, 12), (7, 12), (8, 12), (9, 12), (10, 12), (11, 12), (12, 12), (13, 12),  
            (0, 13), (1, 13), (2, 13), (3, 13), (4, 13), (5, 13), (6, 13), (7, 13), (8, 13), (9, 13), (10, 13), (11, 13), (12, 13), (13, 13), 
            (1, 14), (2, 14), (3, 14), (4, 14), (5, 14), (6, 14), (7, 14), (8, 14), (9, 14), (10, 14), (11, 14), (12, 14),
            (2, 15), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15), (10, 15), (11, 15), (12, 15), 
            (3, 16), (4, 16), (5, 16), (6, 16), (7, 16), (8, 16), (9, 16), (10, 16), (11, 16), 
            (4, 17), (5, 17), (6, 17), (7, 17), (8, 17), (9, 17), (10, 17), 
            (5, 18), (6, 18), (7, 18), (9, 18), (10, 18), 
            (5, 19), (6, 19), (10, 19), 
            (4, 20), (5, 20), (11, 20), (12, 20)]
        self.dino2_map = [
            (11, 1), (12, 1), (13, 1), (14, 1), (15, 1), (16, 1), (17, 1), (18, 1), 
            (10, 2), (11, 2), (15, 2), (16, 2), (17, 2), (18, 2), (19, 2),
            (10, 3), (11, 3), (13, 3), (15, 3), (16, 3), (17, 3), (18, 3), (19, 3),
            (10, 4), (11, 4), (15, 4), (16, 4), (17, 4), (18, 4), (19, 4),
            (10, 5), (11, 5), (12, 5), (13, 5), (14, 5), (15, 5), (16, 5), (17, 5), (18, 5), (19, 5), 
            (10, 6), (11, 6), (12, 6), (13, 6), (14, 6), 
            (10, 7), (11, 7), (12, 7), (13, 7), (14, 7), (15, 7), (16, 7), (17, 7), 
            (0, 8), (9, 8), (10, 8), (11, 8), (12, 8), (13, 8), 
            (0, 9), (8, 9), (9, 9), (10, 9), (11, 9), (12, 9), (13, 9), 
            (0, 10), (1, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (11, 10), (12, 10), (13, 10), (14, 10), (15, 10), 
            (0, 11), (1, 11), (2, 11), (5, 11), (6, 11), (7, 11), (8, 11), (9, 11), (10, 11), (11, 11), (12, 11), (13, 11),  (15, 11), 
            (0, 12), (1, 12), (2, 12), (3, 12), (4, 12), (5, 12), (6, 12), (7, 12), (8, 12), (9, 12), (10, 12), (11, 12), (12, 12), (13, 12),  
            (0, 13), (1, 13), (2, 13), (3, 13), (4, 13), (5, 13), (6, 13), (7, 13), (8, 13), (9, 13), (10, 13), (11, 13), (12, 13), (13, 13), 
            (1, 14), (2, 14), (3, 14), (4, 14), (5, 14), (6, 14), (7, 14), (8, 14), (9, 14), (10, 14), (11, 14), (12, 14),
            (2, 15), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15), (10, 15), (11, 15), (12, 15), 
            (3, 16), (4, 16), (5, 16), (6, 16), (7, 16), (8, 16), (9, 16), (10, 16), (11, 16), 
            (4, 17), (5, 17), (6, 17), (7, 17), (8, 17), (9, 17), (10, 17), 
            (5, 18), (6, 18), (7, 18), (9, 18), (10, 18), 
            (5, 19), (6, 19), (10, 19), 
            (5, 20), (10, 20), 
            (5, 21), (6, 21), (10, 21), (11, 21)]
        
        self.obstacles = [
            Obstacle(128, 50, 10, 12),
            Obstacle(180, 50, 8, 12)
        ]
        
    def update_obstacles(self):
        for obstacle in self.obstacles:
            obstacle.move(3)  # Obstacle velocity
            obstacle.draw()
    
    def check_collision(self):
        for obstacle in self.obstacles:
            if (self.dino_x < obstacle.x + obstacle.width and
                self.dino_x + self.dino_width > obstacle.x and
                self.dino_y < obstacle.y + obstacle.height and
                self.dino_y + self.dino_height > obstacle.y):
                self.game_over()
                return True
        return False
    
    def update_dino(self):
        if self.jump_status > 0:
            if self.jump_path[self.jump_status] != 0:
                self.dino_y += self.jump_path[self.jump_status]
            elif button_ok.value() == 0 and self.jump_duration < 20:
                self.jump_duration += 1
                self.jump_status += 1
            elif self.jump_duration >= 20:
                self.jump_duration = 0
            self.jump_status -= 1
        
    def draw_terrain(self):
        for i in range(5):
            i *= 32
            oled.line(0+i-self.terrain_x_offset, 63, 32+i-self.terrain_x_offset, 62, 1)
        self.terrain_x_offset = (self.terrain_x_offset + 1) % 32
        #oled.line(32, 63, 64, 62, 1)
        
    def draw_dino(self, cx, cy, c):
        if self.dino_animation_status < 8:
            for (x, y) in self.dino0_map:
                oled.pixel(cx+x, cy+y, c)
        else:
            for (x, y) in self.dino1_map:
                oled.pixel(cx+x, cy+y, c)
        self.dino_animation_status = (self.dino_animation_status + 1) % 16
        
    def draw(self):
        global score
        self.draw_dino(self.dino_x, self.dino_y, 1)
        self.draw_terrain()
        oled.text(f"{score:05d}", 85, 0)
        
    def game_over(self):
        for obstacle in self.obstacles:
            obstacle.x += 180
        global score
        oled.fill(0)
        oled.text(f'SCORE: {score}', 36, 26)
        oled.show()
        utime.sleep(0.5)
        if (score > self.highscore):
            self.highscore = score
            for i in range(3):
                oled.text('NEW HIGHSCORE!!!', 2, 38)
                oled.show()
                utime.sleep(0.5)
                oled.fill(0)
                oled.text(f'SCORE: {score}', 36, 26)
                oled.show()
                utime.sleep(0.5)
            oled.text('NEW HIGHSCORE!!!', 2, 38)
            oled.show()
        else:
            oled.text(f'HIGHSCORE: {self.highscore}', 18, 38)
            oled.show()
            utime.sleep(1.5)
        utime.sleep(1)
        score = 0
        

def dino_game():
    global score
    score = 0
    dino = Dino()
    while button_back.value():
        oled.fill(0)
        if button_ok.value() == 0 and dino.jump_status == 0:
            dino.jump_status = len(dino.jump_path)-1
        dino.update_dino()
        dino.update_obstacles()
        dino.draw()
        dino.check_collision()
        oled.show()
        utime.sleep_ms(10)
    
    return_to_menu()

""" calculator application """
keyboard = [["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "."],
            ["(", ")", "+", "-", "*", "/", "^", "!", "p", "e"],
            ["sin", '', '', "cos", '', '', "tan", '', '', "="]]

def draw_term(term_list):
    term_str = ''.join(term_list)
    if len(term_str) < 17:
        oled.text(f"{term_str}", 0, 0)
    else:
        oled.text(f"{term_str[:16]}", 0, 0)
        oled.text(f"{term_str[16:]}", 0, 11)

def draw_keyboard():
    for i in range(len(keyboard)):
        for j in range(len(keyboard[i])):
            oled.text(f"{keyboard[i][j]}", 2+12*j, 32+11*i)
            
def draw_key_select(x, y):
    oled.rect(0+12*x, 30+11*y, 12*len(keyboard[y][x]), 11, 1)

def calculate_term(term_list):
    term_str = "".join(term_list)
    term_str = term_str.replace("^", "**").replace("p", str(math.pi)).replace("e", str(math.e))

    term_str = re.sub(r'(\d+)!', r'math.factorial(\1)', term_str)

    allowed_names = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "math": math}

    try:
        result = eval(term_str, {"__builtins__": None}, allowed_names)
        return result
    except Exception as e:
        return f"{e}"

def calculator_app():
    utime.sleep(0.25)
    key_x = key_y = 0
    term = []
    while button_back.value():
        oled.fill(0)
        draw_term(term)
        draw_keyboard()
        draw_key_select(key_x, key_y)
        oled.show()
        
        if button_up.value() == 0:
            key_y = (key_y - 1) % len(keyboard)
            while key_x >= len(keyboard[key_y]):
                key_x -= 1
            utime.sleep(0.15)
            while keyboard[key_y][key_x] == '':
                key_x = (key_x - 1) % len(keyboard[key_y])
        if button_down.value() == 0:
            key_y = (key_y + 1) % len(keyboard)
            while key_x >= len(keyboard[key_y]):
                key_x -= 1
            utime.sleep(0.15)
            while keyboard[key_y][key_x] == '':
                key_x = (key_x - 1) % len(keyboard[key_y])
        if button_l.value() == 0:
            key_x = (key_x - 1) % len(keyboard[key_y])
            utime.sleep(0.15)
            while keyboard[key_y][key_x] == '':
                key_x = (key_x - 1) % len(keyboard[key_y])
        if button_r.value() == 0:
            key_x = (key_x + 1) % len(keyboard[key_y])
            utime.sleep(0.15)
            while keyboard[key_y][key_x] == '':
                key_x = (key_x + 1) % len(keyboard[key_y])
        
        if rp2.bootsel_button():
            term = term[:-1]
            utime.sleep(0.15)
        
        if button_ok.value() == 0:
            if keyboard[key_y][key_x] != "=":
                term.append(keyboard[key_y][key_x])
                utime.sleep(0.15)
                if keyboard[key_y][key_x] in ["sin", "cos", "tan"]:
                    term.append("(")
            else:
                result = calculate_term(term)
                oled.text(f"= {result}", 0, 22)
                oled.show()
                utime.sleep(0.25)
                while button_ok.value() and button_back.value():
                    utime.sleep_ms(1)
                utime.sleep(0.25)
        
        
    return_to_menu()

""" future update """
def future_update():
    while button_back.value():
        oled.fill(0)
        oled.text("working on it...", 0, 32)
        oled.show()
        utime.sleep(0.1)
    return_to_menu()



def main():
    global time_offset
    
    load_time_from_file()

    last_update = utime.localtime()[5]
    
    while True:
        # display watch
        if utime.localtime()[5] - last_update >= 1 or utime.localtime()[5] == 0 and last_update == 59:
            show_watch()
            last_update = utime.localtime()[5]
            save_time_to_file()

        # application menu
        if button_ok.value() == 0 or button_r.value() == 0:
            watch_menu()
            last_update = 0
            utime.sleep(0.25)
        
        # power saving mode
        if button_back.value() == 0:
            oled.poweroff()
            enter_sleep()
            oled.poweron()
            last_update = 0
            utime.sleep(0.5)

if __name__ == '__main__':
    main()