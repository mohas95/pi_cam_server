import cv2

camera = cv2.VideoCapture(2)

while True:
    ret, frame = camera.read()

    if not ret:
        break


    cv2.imshow("webcam1", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break



camera.release()
cv2.destroyAllWindows()