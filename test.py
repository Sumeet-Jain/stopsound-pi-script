import spidev

spi = spidev.SpiDev()
LEDS = 32
spidev.open(0,0)

buff = [bytearray(3) for x in range(LEDS)]
gamma = bytearray(256)

def fill(r, g, b, buff):
    for led in range(LEDS):
        buff[led][0] = r
        buff[led][1] = g
        buff[led][2] = b

def update(buff, spi):
    final_buf = [buff[i][0] for i in range(LEDS)]
    final_buf.append(0)
    spi.xfer(final_buf)

fill(0, 0, 0, buff)
update(buff, spi)

spidev.close()
