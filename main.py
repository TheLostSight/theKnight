from MX1508 import *
from VL53L0X import *
from tcs34725 import *
from time import sleep_ms,sleep
from machine import Pin, I2C
import uasyncio as asio
from neopixel import NeoPixel
import aioespnow
import network

i2c_bus = I2C(0, sda=Pin(14), scl=Pin(27))
tof = VL53L0X(i2c_bus)
i2c_bus1 = I2C(1, sda=Pin(2), scl=Pin(15))
tcs = TCS34725(i2c_bus1)
tcs.gain(4)
tcs.integration_time(80)
motor_L = MX1508(23, 18)
motor_R = MX1508(21, 19)
R_m_pin = Pin(34, Pin.IN)
L_m_pin = Pin(35, Pin.IN)
R_W_count,W_count,col_id,col_id_l,direct,di,dist,busy,busy_col,col_sel=0,0,0,0,0,0,500,0,0,5
NUM_OF_LED = 2
np = NeoPixel(Pin(33), NUM_OF_LED)
search_color = ['Red','Green','Cyan','Magenta']
color=['Red','Yellow','White','Green','Black','Cyan','Blue','Magenta']
dir_move=['Stop','Forward','Left','Right','Reverse']
Lt = 60
Sp=1000
debug = 1

network.WLAN(network.STA_IF).active(True)
e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
e.active(True)
# peer = b'\xC8\xF0\x9E\x52\x66\x0C' #C8F09E52660C
# #'\\x'+mac[0:2]+'\\x'+mac[2:4]+'\\x'+mac[4:6]+'\\x'+mac[6:8]+'\\x'+mac[8:10]+'\\x'+mac[10:12]
# e.add_peer(peer)
# peer = b'\xC8\xF0\x9E\x4E\x9C\xA8' #C8F09E4E9CA8
# e.add_peer(peer)

motor_R.forward(Sp)
motor_L.forward(Sp)

def R_W_int(pin):
    global W_count,R_W_count
    W_count+=1
    R_W_count+=1
#    print(W_count, R_W_count)
def L_W_int(pin):
    global W_count
    W_count-=1
#    print("!!!", W_count)
   
R_m_pin.irq(trigger=Pin.IRQ_RISING, handler=R_W_int)
L_m_pin.irq(trigger=Pin.IRQ_RISING, handler=L_W_int)

async def synch(int_ms):
    while True:
        await asio.sleep_ms(int_ms)
        if direct==0: # движение вперед
            if W_count>0:
                motor_R.forward(0)
                motor_L.forward(Sp)
            elif W_count<0:
                motor_R.forward(Sp)
                motor_L.forward(0)
            else:
                motor_R.forward(Sp)
                motor_L.forward(Sp)
        elif direct==1: # поворот направо
            if W_count>0:
                motor_R.forward(0)
                motor_L.reverse(Sp)
            elif W_count<0:
                motor_R.forward(Sp)
                motor_L.reverse(0)
            else:
                motor_R.forward(Sp)
                motor_L.reverse(Sp)
        elif direct==2: # поворот налево
            if W_count>0:
                motor_R.reverse(0)
                motor_L.forward(Sp)
            elif W_count<0:
                motor_R.reverse(Sp)
                motor_L.forward(0)
            else:
                motor_R.reverse(Sp)
                motor_L.forward(Sp)        
        elif direct==3: # движение назад
            if W_count>0:
                motor_R.reverse(0)
                motor_L.reverse(Sp)
            elif W_count<0:
                motor_R.reverse(Sp)
                motor_L.reverse(0)
            else:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp)
        elif direct==-1: # остановка
            motor_R.reverse(0)
            motor_L.reverse(0)

async def W_sp(int_ms): # устанавливем направление движения
    global R_W_count,dist,direct,busy_col
    while True:
        await asio.sleep_ms(int_ms)
        await color_det()
        await dist_det()
        if 150<dist<250: di=1
        elif dist<150: di=2
        else: di=0
        if (not busy) & (not busy_col):
            if di==1:
                if dist%2:
                    direct=1
                else:
                    direct=2
                await move(8)
            elif di==2:
                direct=3
                await move(16)
            else:
                direct=0
        if  col_id==4: #col_id_l==col_id &
            direct=3
            await move(4)
            direct=2
            await move(8)
        if color[col_id] in search_color:
            direct=-1
            busy_col=1
        else:
            motor_R.reverse(Sp)
            motor_L.forward(Sp)
            busy_col=0
            
async def move(turn):
    global R_W_count,busy
    busy=1
    R_W_count=0    
    while R_W_count<turn:   
        await asio.sleep_ms(0)
    busy=0
    
async def dist_det():
    global dist
    tof.start()
    dist=tof.read()
    dist=int(dist*0.9)
    tof.stop()
    if debug:
        print('Distance is {}. W_count {}'.format(dist   ,W_count))

async def color_det():
    global col_id,col_id_l
    rgb=tcs.read(1)
    r,g,b=rgb[0],rgb[1],rgb[2]
    h,s,v=rgb_to_hsv(r,g,b)
    if 340<h<370:
        col_id_l=col_id
        col_id=0
    elif 45<h<110:
        col_id_l=col_id
        col_id=1
    elif 121<h<200:
        if v>270:
            col_id_l=col_id
            col_id=2
        elif 60<v<110:
            col_id_l=col_id
            col_id=3
        elif v<40:
            col_id_l=col_id
            col_id=4
    elif 181<h<240:
        if v>160:
            col_id_l=col_id
            col_id=5
        elif v>40:
            col_id_l=col_id
            col_id=6
    elif 241<h<340:
        col_id_l=col_id
        col_id=7 
    if debug:
         print('Color is {}. R:{} G:{} B:{} H:{:.0f} S:{:.0f} V:{:.0f}'.format(color[col_id],r,g,b,h,s,v))

async def LED_cont(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
        if col_id==0:
            np[0]=(Lt,0,0)
        elif col_id==1:
            np[0]=(Lt,Lt,0)
        elif col_id==2:
            np[0]=(Lt,Lt,Lt)
        elif col_id==3:
            np[0]=(0,Lt,0)
        elif col_id==4:
            np[0]=(0,0,0)
            np.write()
            await asio.sleep_ms(300)
            np[0]=(Lt,0,0)
            np.write()
            await asio.sleep_ms(300)
        elif col_id==5:
            np[0]=(0,Lt,Lt)
        elif col_id==6:
            np[0]=(0,0,Lt) 
        elif col_id==7:
            np[0]=(Lt,0,Lt)
        np.write()

async def send(e, period):
    while 1:
        await e.asend(color[col_id]+' '+dir_move[1+direct]+' '+str(dist)) #
        await asio.sleep_ms(period)
        
async def resive(e,int_ms):
    global col_sel
    while 1:
        async for mac, msg in e:
            col_sel=int.from_bytes(msg,'big')-48
            if color[col_sel] in search_color:
                search_color.remove(str(color[col_sel]))
            await asio.sleep_ms(int_ms)
        

loop = asio.get_event_loop()
loop.create_task(synch(1))
loop.create_task(W_sp(100))
loop.create_task(LED_cont(100))
#loop.create_task(send(e,100))
#loop.create_task(resive(e,100))
loop.run_forever()