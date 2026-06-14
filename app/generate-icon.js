// Generates a simple solid-color square PNG for the tray icon (assets/icon.png)
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const SIZE = 256;
const COLOR = [217, 119, 87, 255]; // #d97757

function crc32(buf) {
  let crc = ~0;
  for (let i = 0; i < buf.length; i++) {
    crc ^= buf[i];
    for (let j = 0; j < 8; j++) {
      crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
  }
  return ~crc >>> 0;
}

function chunk(type, data) {
  const typeBuf = Buffer.from(type, 'ascii');
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

const ihdrData = Buffer.alloc(13);
ihdrData.writeUInt32BE(SIZE, 0);
ihdrData.writeUInt32BE(SIZE, 4);
ihdrData.writeUInt8(8, 8); // bit depth
ihdrData.writeUInt8(6, 9); // color type RGBA
ihdrData.writeUInt8(0, 10);
ihdrData.writeUInt8(0, 11);
ihdrData.writeUInt8(0, 12);

const raw = Buffer.alloc(SIZE * (1 + SIZE * 4));
for (let y = 0; y < SIZE; y++) {
  const rowStart = y * (1 + SIZE * 4);
  raw[rowStart] = 0; // filter
  for (let x = 0; x < SIZE; x++) {
    const px = rowStart + 1 + x * 4;
    raw[px] = COLOR[0];
    raw[px + 1] = COLOR[1];
    raw[px + 2] = COLOR[2];
    raw[px + 3] = COLOR[3];
  }
}
const idatData = zlib.deflateSync(raw);

const png = Buffer.concat([
  signature,
  chunk('IHDR', ihdrData),
  chunk('IDAT', idatData),
  chunk('IEND', Buffer.alloc(0))
]);

const outDir = path.join(__dirname, 'assets');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'icon.png'), png);
console.log('Wrote', path.join(outDir, 'icon.png'));
