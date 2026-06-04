from ultralytics import YOLO
import torch

class ObjectDetector:

    def __init__(self):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        self.model = YOLO("yolov8m.pt")
        self.model.to(device)

    def detect(self, frame):

        results = self.model.track(frame, persist=True)[0]

        persons = []
        items = []
        carts = []

        for box in results.boxes:
            label = self.model.names[int(box.cls)]

            if label == "person":
                id_val = box.id[0].item() if box.id is not None else None
                persons.append({'bbox': box.xyxy[0].cpu().numpy(), 'id': id_val})

            if label in ["bottle","cell phone","book","cup"]:
                items.append(box.xyxy[0].cpu().numpy())

            if label in ["shopping cart", "cart"]:  # Assuming YOLO detects carts
                carts.append(box.xyxy[0].cpu().numpy())

        return persons, items, carts