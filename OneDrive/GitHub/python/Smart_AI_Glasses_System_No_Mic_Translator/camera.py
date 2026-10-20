import cv2


class CameraSystem:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None

    def open_camera(self):
        possible_indexes = [self.camera_index, 0, 1, 2, 3, 4, 5]
        tried = set()

        for index in possible_indexes:
            if index in tried:
                continue

            tried.add(index)

            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(index)

            if not cap.isOpened():
                cap.release()
                continue

            ret, frame = cap.read()

            if ret and frame is not None:
                self.cap = cap
                self.camera_index = index
                print(f"Camera opened successfully. Index: {index}")
                return True

            cap.release()

        print("Error: Camera not found.")
        print("Close Camera App / Zoom / Teams and try again.")
        return False

    def preview(self):
        if self.cap is None:
            opened = self.open_camera()
            if not opened:
                return

        print("Camera preview started.")
        print("Press Q or ESC to exit.")

        while True:
            ret, frame = self.cap.read()

            if not ret or frame is None:
                print("Cannot read frame from camera.")
                break

            cv2.imshow("Smart AI Glasses Camera Preview", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

        self.release()

    def get_frame(self):
        if self.cap is None:
            opened = self.open_camera()
            if not opened:
                return None

        ret, frame = self.cap.read()

        if not ret or frame is None:
            return None

        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        cv2.destroyAllWindows()


if __name__ == "__main__":
    camera = CameraSystem()
    camera.preview()