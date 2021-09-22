def converthex(colorHex):
    try:
        colorHex = colorHex.replace("#", "")
    except:
        colorHex = colorHex
    convert = int(colorHex, 16)
    final = int(hex(convert), 0)
    return final