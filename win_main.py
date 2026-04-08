# only use 32bit python. 64bit python won't be able to load the .dll 

import win32com.client


if __name__ == '__main__':
    digital_scales_com_object = win32com.client.Dispatch("AddIn.DrvLP")

    if digital_scales_com_object.Connect() == 0:
        digital_scales_com_object.Beep()
    else:
        print("Error: " + digital_scales_com_object.ResultCodeDescription)
