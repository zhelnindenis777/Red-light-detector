from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


VEHICLE_CLASSES = {2: "автомобиль", 3: "мотоцикл", 5: "автобус", 7: "грузовик"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class VehicleDetector:
    def __init__(self, model_path):
        self.model = YOLO(str(model_path))

    def process(self, input_path, output_path, stop_line_percent, confidence, light_mode, roi):
        if Path(input_path).suffix.lower() in IMAGE_EXTENSIONS:
            return self._process_image(input_path, output_path, stop_line_percent, confidence, light_mode, roi)
        return self._process_video(input_path, output_path, stop_line_percent, confidence, light_mode, roi)

    def _detect(self, frame, confidence):
        result = self.model.predict(frame, conf=confidence, verbose=False)[0]
        detections = []
        for box in result.boxes:
            class_id = int(box.cls.item())
            if class_id not in VEHICLE_CLASSES:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append(
                {
                    "box": (x1, y1, x2, y2),
                    "class_id": class_id,
                    "name": VEHICLE_CLASSES[class_id],
                    "confidence": float(box.conf.item()),
                }
            )
        return detections

    @staticmethod
    def _red_light(frame, light_mode, roi):
        if light_mode == "red":
            return True
        if light_mode == "green":
            return False

        x, y, w, h = roi
        if w <= 0 or h <= 0:
            return False
        crop = frame[max(y, 0):max(y + h, 0), max(x, 0):max(x + w, 0)]
        if crop.size == 0:
            return False
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 90, 80]), np.array([12, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([165, 90, 80]), np.array([180, 255, 255]))
        ratio = cv2.countNonZero(cv2.bitwise_or(mask1, mask2)) / mask1.size
        return ratio >= 0.08

    @staticmethod
    def _draw(frame, detections, stop_line_y, red_light, roi):
        line_color = (0, 0, 255) if red_light else (0, 180, 0)
        cv2.line(frame, (0, stop_line_y), (frame.shape[1], stop_line_y), line_color, 3)
        cv2.putText(frame, "STOP LINE", (15, max(28, stop_line_y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, line_color, 2)

        x, y, w, h = roi
        if w > 0 and h > 0:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 190, 255), 2)

        violations = 0
        for item in detections:
            x1, y1, x2, y2 = item["box"]
            is_violation = red_light and y2 >= stop_line_y
            color = (0, 0, 255) if is_violation else (50, 190, 50)
            label = f"{item['name']} {item['confidence']:.2f}"
            if is_violation:
                label += " VIOLATION"
                violations += 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        status = "RED" if red_light else "GREEN / NOT RED"
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 45), (25, 32, 45), -1)
        cv2.putText(frame, f"Traffic light: {status} | Vehicles: {len(detections)} | Violations: {violations}",
                    (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        return violations

    def _process_image(self, input_path, output_path, stop_line_percent, confidence, light_mode, roi):
        frame = cv2.imread(str(input_path))
        if frame is None:
            raise ValueError("Изображение не удалось прочитать")
        stop_line_y = int(frame.shape[0] * stop_line_percent / 100)
        detections = self._detect(frame, confidence)
        red_light = self._red_light(frame, light_mode, roi)
        violation_count = self._draw(frame, detections, stop_line_y, red_light, roi)
        if not cv2.imwrite(str(output_path), frame):
            raise ValueError("Не удалось сохранить результат")
        return {
            "media_type": "image",
            "vehicle_count": len(detections),
            "violation_count": violation_count,
            "red_light": red_light,
            "class_counts": dict(Counter(item["name"] for item in detections)),
        }

    def _process_video(self, input_path, output_path, stop_line_percent, confidence, light_mode, roi):
        capture = cv2.VideoCapture(str(input_path))
        if not capture.isOpened():
            raise ValueError("Видео не удалось открыть")

        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        stop_line_y = int(height * stop_line_percent / 100)
        max_vehicles = 0
        max_violations = 0
        class_counts = Counter()
        red_seen = False
        last_detections = []
        frame_number = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame_number += 1
            if frame_number == 1 or frame_number % 3 == 0:
                last_detections = self._detect(frame, confidence)
            red_light = self._red_light(frame, light_mode, roi)
            violations = self._draw(frame, last_detections, stop_line_y, red_light, roi)
            writer.write(frame)
            max_vehicles = max(max_vehicles, len(last_detections))
            max_violations = max(max_violations, violations)
            red_seen = red_seen or red_light
            current_counts = Counter(item["name"] for item in last_detections)
            for name, count in current_counts.items():
                class_counts[name] = max(class_counts[name], count)

        capture.release()
        writer.release()
        if frame_number == 0:
            raise ValueError("В видео не найдено кадров")
        return {
            "media_type": "video",
            "vehicle_count": max_vehicles,
            "violation_count": max_violations,
            "red_light": red_seen,
            "class_counts": dict(class_counts),
        }
