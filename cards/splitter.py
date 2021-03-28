
from PIL import Image

import cv2

imgs = cv2.imread("uno.png")

for x in range(0, 168*12, 168):
    for y in range(0, 259*6, 258):
        print([x,y])
        crop_img = imgs[y:y+259, x:x+168]

        cv2.imwrite("temp.png", crop_img)


        img = Image.open('temp.png')
        img = img.convert("RGBA")

        pixdata = img.load()

        width, height = img.size
        for s in range(height):
            for d in range(width):
                if pixdata[d, s] == (255, 255, 255, 255):
                    pixdata[d, s] = (255, 255, 255, 0)



        img.save(f"cards/{str(x)+str(y)}.png", "PNG")