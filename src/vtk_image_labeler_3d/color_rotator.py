class ColorRotator:
    def __init__(self):
        # Define a list of 10 preset RGB colors
        self.colors = [
            (255, 0, 0),     # Red
            (0, 255, 0),     # Green
            (0, 0, 255),     # Blue
            (255, 255, 0),   # Yellow
            (0, 255, 255),   # Cyan
            (255, 0, 255),   # Magenta
            (170, 255, 0),   # 
            (255, 165, 0),   # Orange
            (170, 255, 9),   # Indigo
            (0, 128, 0)      # Dark Green
        ]
        self.index = 0  # Track the current position in the rotation

    def next(self):
        """Return the next color in the rotation."""
        color = self.colors[self.index]
        self.index = (self.index + 1) % len(self.colors)  # Move to the next color, wrap around if needed
        return color

    def reset(self):
        self.index = 0