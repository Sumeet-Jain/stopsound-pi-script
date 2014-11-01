import time

import spidev

spi = spidev.SpiDev()
LEDS = 32

try:
    spi.open(0,0)
    spi.max_speed_hz = 40000000

    buff = [bytearray(3) for x in range(LEDS)]
    gamma = bytearray(256)

    for i in range(256):
        gamma[i] =  0x80 | int(pow(float(i) / 255.0, 2.5) * 127.0 + 0.5)

    def fill(r, g, b, buff):
        for led in range(LEDS):
            buff[led][0] = gamma[r]
            buff[led][1] = gamma[g]
            buff[led][2] = gamma[b]

    def update(buff, spi):
        final_buf = []
        for led in buff:
            final_buf.append(led[0])
            final_buf.append(led[1])
            final_buf.append(led[2])
        final_buf.append(0)
        spi.xfer(final_buf)

    while True:
        fill(0, 0, 0, buff)
        update(buff, spi)
        time.sleep(.001)
finally:
    while i in range(500):
        fill(1, 1, 1, buff)
        update(buff, spi)
        time.sleep(.001)
    spi.close()
