import numpy as np

class PersonTracker:

    def __init__(self):
        self.people = {}
        self.next_id = 1
        self.max_lost_frames = 30  # Keep people for 30 frames after not seen

    def iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0

    def update(self, persons):

        updated = {}
        seen_ids = set()

        for box in persons:

            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)
            center = (cx, cy)

            # Find best matching existing person using IoU
            best_iou = 0
            best_id = None
            for pid, data in self.people.items():
                if pid not in seen_ids and "box" in data:
                    iou_val = self.iou(box, data["box"])
                    if iou_val > best_iou:
                        best_iou = iou_val
                        best_id = pid

            if best_iou > 0.3:  # IoU threshold for matching
                updated[best_id] = self.people[best_id].copy()
                updated[best_id]["center"] = center
                updated[best_id]["box"] = box
                updated[best_id]["lost_frames"] = 0  # Reset lost counter
                seen_ids.add(best_id)
            else:  # New person
                updated[self.next_id] = {
                    "center": center,
                    "box": box,
                    "score": 0,
                    "alerted": False,
                    "lost_frames": 0
                }
                self.next_id += 1

        # Handle lost people
        for pid, data in self.people.items():
            if pid not in seen_ids:
                if data.get("lost_frames", 0) < self.max_lost_frames:
                    updated[pid] = data.copy()
                    updated[pid]["lost_frames"] = data.get("lost_frames", 0) + 1
                # Else, remove by not adding to updated

        self.people = updated

        return self.people