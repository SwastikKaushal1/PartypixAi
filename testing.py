import cv2
import face_recognition
import os
import numpy as np
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk

# Path to images folder
dataset_path = "wedding_photos"

# Load guest image
guest_image_path = "guest.jpeg"
guest_image = face_recognition.load_image_file(guest_image_path)
guest_encoding = face_recognition.face_encodings(guest_image)

if len(guest_encoding) == 0:
    print("❌ No face found in the guest image.")
    exit()

guest_encoding = guest_encoding[0]

# Get all images in the dataset
all_images = []

for filename in os.listdir(dataset_path):
    if filename.endswith(('.jpg', '.jpeg', '.png')):
        image_path = os.path.join(dataset_path, filename)
        image = face_recognition.load_image_file(image_path)

        # Find face locations and encodings
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image, face_locations)

        # Load image using OpenCV
        img_cv2 = cv2.imread(image_path)
        match_found = False
        accuracy = 0

        # Check for matches using face distance
        for face_encoding, face_location in zip(face_encodings, face_locations):
            distance = face_recognition.face_distance([guest_encoding], face_encoding)[0]
            accuracy = round(1 - distance, 2)
            if accuracy >= 0.6:
                match_found = True
                top, right, bottom, left = face_location
                cv2.rectangle(img_cv2, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(img_cv2, f"Accuracy: {accuracy}", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Save image, even if no match found
        all_images.append((filename, accuracy, img_cv2, match_found))

# Tkinter GUI Setup
root = tk.Tk()
root.title("Face Recognition Results")

label = Label(root)
label.pack()

info_label = Label(root, text="", font=("Arial", 14))
info_label.pack()

index = 0

def show_next_image(event=None):
    global index
    if index < len(all_images):
        filename, accuracy, img_cv2, match_found = all_images[index]
        
        img = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(img)
        
        label.config(image=img)
        label.image = img
        
        if match_found:
            info_label.config(text=f"✅ Match found in: {filename} | Accuracy: {accuracy}")
        else:
            info_label.config(text=f"❌ No match in: {filename}")
        
        index += 1
    else:
        info_label.config(text="No more images.")

root.bind("<Return>", show_next_image)  # Press "Enter" to go to the next image

show_next_image()  # Show the first image
root.mainloop()
    