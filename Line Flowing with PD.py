import numpy as np

from djitellopy import tello

import cv2


me = tello.Tello()

me.connect()

print(me.get_battery())

me.streamon()

#me.takeoff()

cap = cv2.VideoCapture(1)

hsvVals = [47,14,0,179,193,99]

sensors = 3

threshold = 0.2

width, height = 480, 360

senstivity = 3  # if number is high less sensitive

weights = [-25, -15, 0, 15, 25]

fSpeed = 5

curve = 0



def thresholding(img):

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower = np.array([hsvVals[0], hsvVals[1], hsvVals[2]])

    upper = np.array([hsvVals[3], hsvVals[4], hsvVals[5]])

    mask = cv2.inRange(hsv, lower, upper)

    return mask

def getContours(imgThres, img):
    cx = 0
    
    contours, hierarchy = cv2.findContours(imgThres, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if len(contours) != 0:
        biggest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(biggest)
        cx = x + w // 2
        cy = y + h // 2
        cv2.drawContours(img, [biggest], -1, (0, 0, 0), 7)
        cv2.circle(img, (cx, cy), 10, (0, 255, 0), cv2.FILLED)

        # Draw a line through the center point (cx, cy)
        #cv2.line(img, (width // 2, height // 2), (cx ), (0, 0, 255), 2)
        
        # Display cx, cy values below the center point
        text = f"cx: {cx}"
        #cv2.putText(img, text, (cx - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    return cx


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

def sendCommands(senOut, cx):
    global curve, prevError
    error = int((cx) - (width // 2))  # Sai số 
    Kp = 0.1  # Hệ số tỷ lệ P
    Kd = 0.02  # Hệ số tỷ lệ đạo hàm D
    lr = int(-(Kp * error + Kd * (error - prevError)))
    lr = -lr
    lr = int(np.clip(lr, -10, 10))


    ## Rotation

    if   senOut == [1, 0, 0]: curve = weights[0]

    elif senOut == [1, 1, 0]: curve = weights[1]

    elif senOut == [0, 1, 0]: curve = weights[2]

    elif senOut == [0, 1, 1]: curve = weights[3]

    elif senOut == [0, 0, 1]: curve = weights[4]

    elif senOut == [0, 0, 0]: curve = weights[2]

    elif senOut == [1, 1, 1]: curve = weights[2]

    elif senOut == [1, 0, 1]: curve = weights[2]
    
    print('left-right:', lr)
    me.send_rc_control(lr, fSpeed, 0, curve)
    prevError = error

prevError = 0

while True:

    #_, img = cap.read()

    img = me.get_frame_read().frame

    img = cv2.resize(img, (width, height))

    img = cv2.flip(img, 0)

    imgThres = thresholding(img)

    cx = getContours(imgThres, img)  ## For Translation

    senOut = getSensorOutput(imgThres, sensors)  ## Rotation

    sendCommands(senOut, cx)

    cv2.imshow("Output", img)

    cv2.imshow("Path", imgThres)

    cv2.waitKey(1)