# Imports
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUiType
from os import path
import sys
import pyperclip
from PIL import Image, ImageFilter, ImageDraw  # Python Imaging Library
import pytesseract
from gtts import gTTS
import pygame


# Import GUI file
FORM_CLASS, QMainWindow = loadUiType(path.join(path.dirname(__file__), "AOCR.ui"))


# Initial UI file
class AOCRScreen(QMainWindow, FORM_CLASS):

    # Global Variables
    copied = ''
    audio_path = ''
    isPlaying = False

    # Constructor
    def __init__(self, parent=None):
        super(AOCRScreen, self).__init__(parent)
        QMainWindow.__init__(self)
        self.setupUi(self)

        # set frame 'frame' to be 40% of the screen width
        self.scrollArea.setMinimumWidth(int(self.width() * 0.65))
        self.scrollArea.setMaximumWidth(int(self.width() * 0.65))

        # handle buttons
        self.button_start.clicked.connect(self.applyOCR)  # start button
        self.button_reset.clicked.connect(self.reset)  # reset button
        self.button_copy.clicked.connect(lambda: self.copy_to_clipboard(self.copied))  # copy button
        self.button_playAudio.clicked.connect(self.playAudio)  # play audio button
        self.button_exit.clicked.connect(self.close)  # exit button


    """
       Function to perform the AOCR process
       @param self
   """
    def applyOCR(self):

        # Select an image
        img = self.selectImage()

        if img:
            self.label_message.setText("Loading, please wait!")
            QTimer.singleShot(3000, lambda: self.label_message.setText(""))

            # Pre-process the image
            processed_img = self.preProcess(img)

            # Extract the text from the image
            imgText = self.extractText(processed_img)

            # image with boxes on the detected words and lines
            self.drawBoxes(img)

            # Save an image with boxes on detected words with a confidence value (60% in this case)
            # self.confidenceText(img, 60)

            # Generate an audio file from extracted text
            self.generateAudio(imgText)
        else:
            self.label_message.setText("Please, select an image!")
            QTimer.singleShot(2500, lambda: self.label_message.setText(""))
            print("Error, no image selected!")


    """
        Function for image upload
        @param self
    """
    def selectImage(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setWindowTitle("Select an image")
        file_dialog.selectNameFilter("JPG file (*.jpg)")
        file_dialog.setNameFilters(["All files (*.*)", "JPG file (*.jpg)", "PNG file (*.png)"])

        if file_dialog.exec_() == QFileDialog.Accepted:
            selected_files = file_dialog.selectedFiles()
            imPath = selected_files[0]

            # display the image
            pixmap = QPixmap(imPath)
            self.label_inputImage.setPixmap(pixmap.scaled(450, 350))

            img = Image.open(imPath)
            img = img.resize((450, 350))

            return img
        else:
            print("No file selected")
            return False


    """
        Function to perform pre-processing on the image
        @param self, img
    """
    def preProcess(self, img):

        # Convert the image to grayscale
        gray = img.convert('L')

        # Smoothing - Apply a median filter
        med_filter = gray.filter(ImageFilter.MedianFilter(size=1))

        # Apply thresholding to the image
        threshold = med_filter.point(lambda x: 255 if x > 128 else 0, '1')

        # Enhancement - Apply high-pass filter for sharpening
        # laplacian_kernel = (0, -1, 0, -1, 4, -1, 0, -1, 0)
        log_kernel = (-1, -1, -1,
                      -1, 9, -1,
                      -1, -1, -1)
        img = threshold.filter(ImageFilter.Kernel(size=(3, 3), kernel=log_kernel, scale=1))

        # Save the pre-processed image
        img.save("pre-processed.jpg")

        # display the pre-processed image
        pixmap = QPixmap("pre-processed.jpg")
        self.label_preprocessedImage.setPixmap(pixmap)

        return img


    """
        Function to extract text from an image
        @param self, img
    """
    def extractText(self, img):

        # Define path to tessaract.exe
        path_to_tesseract = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # Point tessaract_cmd to tessaract.exe
        pytesseract.pytesseract.tesseract_cmd = path_to_tesseract

        # Extract text from image
        imgText = pytesseract.image_to_string(img, lang='ara')

        # Copy the extracted text into the clipboard
        self.copy_to_clipboard(imgText)
        AOCRScreen.copied = imgText  # global variable

        # Display the extracted text from the image
        self.textViewer.setText(imgText)

        return imgText


    """
        Function to detect words by drawing boxes on them
        @param self, img
    """
    def drawBoxes(self, img):
        # Get bounding boxes around recognized text
        boxes = pytesseract.image_to_boxes(img)

        # Draw bounding boxes on image
        draw = ImageDraw.Draw(img)
        for b in boxes.splitlines():
            b = b.split(' ')
            x1, y1, x2, y2 = int(b[1]), img.height - int(b[2]), int(b[3]), img.height - int(b[4])
            draw.rectangle([x1, y1, x2, y2], outline=(0,), width=2)

        # save the image
        img.save('boxes.jpg')

        # display the image with bounding boxes
        pixmap = QPixmap('boxes.jpg')
        self.label_outputImage.setPixmap(pixmap)


    """
        Function to get recognized text with confidence scores
        @param self, img
    """
    def confidenceText(self, img, confidence_value):

        data = pytesseract.image_to_data(img, lang='ara', output_type=pytesseract.Output.DICT)

        draw = ImageDraw.Draw(img)
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > confidence_value:
                (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                draw.rectangle((x, y, x + w, y + h), outline=(0), width=2)

        # Save image
        img.save('confidence.jpg')


    """
        Function to copy the text into the clipboard
        @param self, text
    """
    def copy_to_clipboard(self, text):
        if AOCRScreen.copied:
            pyperclip.copy(text)

            # message to the user
            self.label_message.setText("Text copied to clipboard!")
            QTimer.singleShot(2500, lambda: self.label_message.setText(""))
        else:
            # message to the user
            self.label_message.setText("No text to copy!")
            QTimer.singleShot(2500, lambda: self.label_message.setText(""))


    """
        Function to generate audio file from extracted text
        @param self, text
    """
    def generateAudio(self, text):
        # Pre-process the text first
        arabic_text = text.strip()

        # generate an audio file using google text-to-speech API (gTTS)
        tts = gTTS(arabic_text, lang='ar')

        # save the file
        tts.save('test.mp3')

        # Update the audio file path global variable (audio_path) with the saved file path
        AOCRScreen.audio_path = "test.mp3"


    """
        Function to play the recognized text when the 'Play Audio' button is clicked
        @param self
    """
    def playAudio(self):
        if AOCRScreen.audio_path:
            if not AOCRScreen.isPlaying:
                # initialize the audio handler
                pygame.mixer.init()

                # load the audio file
                pygame.mixer.music.load(AOCRScreen.audio_path)

                # play the audio file
                pygame.mixer.music.play()
                AOCRScreen.isPlaying = True

                # message to the user
                self.label_message.setText("Audio is now playing!")
                QTimer.singleShot(2500, lambda: self.label_message.setText(""))
            else:
                pygame.mixer.music.pause()
                AOCRScreen.isPlaying = False

                # message to the user
                self.label_message.setText("Audio has been paused!")
                QTimer.singleShot(2500, lambda: self.label_message.setText(""))
        else:
            # message to the user
            self.label_message.setText("No audio to play!")
            QTimer.singleShot(2500, lambda: self.label_message.setText(""))


    """
        Function to reset everything
        @param self
    """
    def reset(self):
        # reset the preview images
        pixmap = QPixmap("assets/placeholder.png")
        self.label_inputImage.setPixmap(pixmap.scaled(450, 350))
        self.label_preprocessedImage.setPixmap(pixmap.scaled(450, 350))
        self.label_outputImage.setPixmap(pixmap.scaled(450, 350))

        self.textViewer.setText("")

        AOCRScreen.copied = ''
        AOCRScreen.audio_path = ''

        self.label_message.setText("You have successfully reset everything!")
        QTimer.singleShot(2500, lambda: self.label_message.setText(""))

    """
        Function to close the application
        @param self
    """
    def closeEvent(self, event):
        # Override closeEvent to display a confirmation dialog
        reply = QMessageBox.question(self, "Exit", "Are you sure you want to quit?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


# Driver code
def main():
    app = QApplication(sys.argv)
    window = AOCRScreen()
    window.show()
    app.exec_()  # infinite loop


if __name__ == '__main__':
    main()
