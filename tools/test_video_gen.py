#!/usr/bin/env python3
"""
Generate a simple test video for PlateTrack.
Creates a 10-second video with a moving white rectangle simulating a car.
Output: tools/test_video.mp4
"""
import cv2
import numpy as np
import os

def main():
    output_path = os.path.join(os.path.dirname(__file__), 'test_video.mp4')
    width, height = 640, 480
    fps = 30
    duration = 10  # seconds
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for i in range(fps * duration):
        frame = np.zeros((height, width, 3), dtype=np.uint8)  # black background
        # Moving rectangle from left to right
        x = int((i / (fps * duration)) * (width - 100))
        y = height // 2 - 50
        cv2.rectangle(frame, (x, y), (x + 100, y + 100), (255, 255, 255), -1)
        out.write(frame)

    out.release()
    print(f"Test video saved to {output_path}")

if __name__ == '__main__':
    main()