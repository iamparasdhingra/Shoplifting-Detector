import numpy as np

class BehaviorAnalyzer:

    # Change this threshold to control how sensitive the stealing alert is.
    ALERT_THRESHOLD = 60

    def __init__(self):
        self.person_scores = {}
        self.alerted = {}

    def analyze(self, people, items, carts):

        events = []

        for pid, data in people.items():

            pc = data["center"]

            score = self.person_scores.get(pid, 0)

            # Check if person has a cart nearby
            has_cart = False
            for cart in carts:
                cc = (
                    int((cart[0] + cart[2]) / 2),
                    int((cart[1] + cart[3]) / 2)
                )
                cart_distance = np.linalg.norm(
                    np.array(pc) - np.array(cc)
                )
                if cart_distance < 200:  # Person is near a cart
                    has_cart = True
                    break

            for item in items:

                ic = (
                    int((item[0] + item[2]) / 2),
                    int((item[1] + item[3]) / 2)
                )

                distance = np.linalg.norm(
                    np.array(pc) - np.array(ic)
                )

                if distance < 100:  # Reduced from 150 to 100 for more precision
                    if has_cart:
                        # Assuming adding to cart, maybe decrease score or don't increase
                        score = max(0, score - 10)  # Reward for having cart
                    else:
                        # No cart, suspicious
                        score += 10  # Reduced from 20 to 10 for slower accumulation
                        score = min(100, score)  # Cap at 100

            self.person_scores[pid] = score

            if score >= self.ALERT_THRESHOLD and not self.alerted.get(pid, False):
                events.append({
                    "person": pid,
                    "score": score,
                    "type": "stealing" if not has_cart else "adding_to_cart"
                })
                self.alerted[pid] = True

        return events