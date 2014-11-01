import spidev

spi = spidev.SpiDev()
LEDS = 32
spi.open(0,0)

buff = [bytearray(3) for x in range(LEDS)]
gamma = bytearray(256)

for i in range(256):
    gamma[i] =  0x80 | int(pow(float(i) / 255.0, 2.5) * 127.0 + 0.5)

def fill(r, g, b, buff):
    for led in range(LEDS):
        buff[led][0] = gamma(r)
        buff[led][1] = gamma(g)
        buff[led][2] = gamma(b)

def update(buff, spi):
    final_buf = [buff[i][0] for i in range(LEDS)]
    final_buf.append(0)
    spi.xfer(final_buf)

fill(0, 0, 0, buff)
update(buff, spi)

spi.close()
