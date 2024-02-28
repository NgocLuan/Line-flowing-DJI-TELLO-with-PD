import numpy as np
from djitellopy import tello
import cv2
import pandas as pd

# connect to tello drone
me = tello.Tello()
me.connect()
print(me.get_battery())
me.streamon()
me.takeoff()
# opencv2
cap = cv2.VideoCapture(1)
# image processing data
hsvVals = [0, 17, 0, 29, 255, 130]
threshold = 0.2
width, height = 480, 360
fSpeed = 10
curve = 0
sensors = 3

class PDController:
    def __init__(self, kp, kd, setpoint):
        self.kp = kp
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0

    def update(self, current_value):
        error = self.setpoint - current_value
        derivative = error - self.prev_error
        output = self.kp * error + self.kd * derivative
        self.prev_error = error
        return output

class PDControllerangle:
    def __init__(self, kp_a, kd_a, setpoint_a):
        self.kp_a = kp_a
        self.kd_a = kd_a
        self.setpoint_a = setpoint_a
        self.prev_error_a = 0

    def update(self, current_value_a):
        error_a = self.setpoint_a - current_value_a
        derivative_a = error_a - self.prev_error_a
        output_a = self.kp_a * error_a + self.kd_a * derivative_a
        self.prev_error_a = error_a
        return output_a

def thresholding(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([hsvVals[0], hsvVals[1], hsvVals[2]])
    upper = np.array([hsvVals[3], hsvVals[4], hsvVals[5]])
    mask = cv2.inRange(hsv, lower, upper)
    return mask

def getContours(imgThres, img):
    cx = 0
    cy = 0
    angle = 0

    contours, hierarchy = cv2.findContours(imgThres, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if len(contours) != 0:
        biggest = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(biggest)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # Vẽ hình chữ nhật bao quanh đối tượng
        cv2.drawContours(img, [box], 0, (0, 0, 255), 2)

        # Tính góc nghiêng của hình chữ nhật
        angle = rect[2]

        x, y, w, h = cv2.boundingRect(biggest)
        cx = x + w // 2
        cy = y + h // 2
        
        if angle < 45:
            angle = angle
        if angle > 45:
            angle = 90 - angle
        
        # Draw a line from the center to the top center of the largest contour
        # cv2.line(img, (width // 2, height // 2), (cx, y), (0, 255, 255), 2)
        
        # Display cx, cy, and adjusted angle values
        text = f"cx: {cx},angle: {angle:.2f} degrees"
        cv2.putText(img, text, (cx - 40, cy + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)


        cv2.circle(img, (cx, cy), 10, (0, 255, 0), cv2.FILLED)

    return cx,cy, angle

def getSensorOutput(imgThres, sensors):

    imgs = np.hsplit(imgThres, sensors)

    totalPixels = (img.shape[1] // sensors) * img.shape[0]

    senOut = []

    for x, im in enumerate(imgs):

        pixelCount = cv2.countNonZero(im)

        if pixelCount > threshold * totalPixels:

            senOut.append(1)

        else:

            senOut.append(0)

        # cv2.imshow(str(x), im)

    # print(senOut)

    return senOut

def sendCommands(senOut, cx, pd_controller,pd_controllerangle):
    global curve, prevError
    # error = int(cx - 240)  # Sai số
    lr = pd_controller.update(cx)
    lr = -lr
    lr = int(np.clip(lr, -10, 10))
    
    ang = pd_controllerangle.update(angle)
    ang = int(np.clip(ang, -10, 10))

    ## Rotation
    if senOut ==   [1, 0, 0]: curve = ang
    elif senOut == [1, 1, 0]: curve = ang
    elif senOut == [0, 1, 0]: curve = 0
    elif senOut == [0, 1, 1]: curve = -ang
    elif senOut == [0, 0, 1]: curve = -ang
    elif senOut == [0, 0, 0]: curve = 0
    elif senOut == [1, 1, 1]: curve = 0
    elif senOut == [1, 0, 1]: curve = 0

    # print('angel:', ang)
    # print('error:', error)
    me.send_rc_control(lr, fSpeed, 0, curve)
    
    # prevError = error
    
    data.append({'Time': time, 'SP': 240, 'PV': cx})

# Khởi tạo DataFrame
data = []

# Thêm cột thời gian
time = 0

# Khởi tạo PD controller
pd_controller = PDController(kp=0.2, kd=0.14, setpoint=240)
pd_controllerangle = PDControllerangle(kp_a=0.132, kd_a=0.15, setpoint_a= 0)

while True:
    img = me.get_frame_read().frame
    img = cv2.resize(img, (width, height))
    img = cv2.flip(img, 0)
    imgThres = thresholding(img)
    cx,cy,angle = getContours(imgThres, img)  # For Translation
    senOut = getSensorOutput(imgThres, sensors)  # Rotation
    sendCommands(senOut, cx, pd_controller,pd_controllerangle)
    cv2.imshow("Output", img)
    cv2.imshow("Path", imgThres)
    cv2.waitKey(1)
    time += 1

    # Ghi dữ liệu vào file Excel 0.05s
    if time % 30== 0:
        df = pd.DataFrame(data)
        df.to_excel('final_4.xlsx', index=False)
