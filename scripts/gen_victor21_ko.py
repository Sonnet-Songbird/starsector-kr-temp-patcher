"""
gen_victor21_ko.py — victor21.fnt 한국어 지원 버전 생성

전략: 슈퍼샘플링 + UnsharpMask
  ① 8× NEAREST 업스케일 (완벽한 픽셀아트 보존)
  ② LANCZOS 다운스케일 (고품질 안티앨리어싱)
  ③ UnsharpMask (edge 선명화)

스케일 = 18/15 = 1.20
  - victor14 Korean 최대 높이 15px → 18px
  - victor21 lineHeight=19px 에 18px 글리프 → 1px 행간 확보
  - 직접 1.46×보다 약간 작지만 행간이 생기고 비율이 자연스러움

출력:
  patches/starsectorkorean/graphics/fonts/victor21.fnt
  patches/starsectorkorean/graphics/fonts/victor21_0.png
"""

from pathlib import Path
import os, json
from PIL import Image, ImageFilter

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

GAME_CORE    = _resolve(_p['game_core'])
GAME_MODS    = _resolve(_p['game_mods'])
PATCHES      = _resolve(_p['patches'])

GAME_FONTS = os.path.join(GAME_CORE, 'graphics/fonts')
MOD_FONTS  = os.path.join(PATCHES, 'starsectorkorean/graphics/fonts')
OUT_FONTS  = os.path.join(PATCHES, 'starsectorkorean/graphics/fonts')

V21_FNT = os.path.join(GAME_FONTS, "victor21.fnt")
V21_PNG = os.path.join(GAME_FONTS, "victor21_0.png")
V14_FNT = os.path.join(MOD_FONTS,  "victor14.fnt")
V14_PNG = os.path.join(MOD_FONTS,  "victor14_0.png")

OUT_FNT = os.path.join(OUT_FONTS, "victor21.fnt")
OUT_PNG = os.path.join(OUT_FONTS, "victor21_0.png")

# ── victor21 메트릭 (원본)
V21_LINE_HEIGHT = 19
V21_BASE        = 16

# ── 스케일: Korean 최대 높이(15px) → 18px, lineHeight(19) 안에 1px 여백
# 18/15 = 1.2 — 직접 1.46(22px overflow) 대신 여백 확보 우선
SCALE = 18.0 / 15.0   # ≈ 1.200

# ── 슈퍼샘플링 배수 (높을수록 품질↑, 8× 추천)
SUPER = 8

# ── UnsharpMask 파라미터 (R/G/B 채널에만 적용)
USM_RADIUS    = 0.5
USM_PERCENT   = 150
USM_THRESHOLD = 2

# ── 아틀라스
ATLAS_W = 4096
ATLAS_H = 4096
PADDING = 1


# ──────────────────────────────────────────────
def parse_fnt(path):
    """BMFont .fnt 파일 파싱 → char dict 반환."""
    chars = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if not parts or parts[0] != 'char':
                continue
            d = {}
            for p in parts[1:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    d[k] = int(v)
            if 'id' in d:
                chars[d['id']] = d
    return chars


def extract_glyph(img, c):
    """아틀라스 이미지에서 글리프 크롭. 빈 글리프면 None."""
    if c['width'] == 0 or c['height'] == 0:
        return None
    return img.crop((c['x'], c['y'], c['x'] + c['width'], c['y'] + c['height']))


def scale_glyph(glyph, scale, up=SUPER):
    """슈퍼샘플링: up× NEAREST 업 → LANCZOS 다운 → UnsharpMask.
    R/G/B 채널만 선명화, alpha는 원본 보존."""
    tw = max(1, round(glyph.width  * scale))
    th = max(1, round(glyph.height * scale))

    # ① up× NEAREST (픽셀아트를 깔끔하게 확대)
    interim = glyph.resize((glyph.width * up, glyph.height * up), Image.NEAREST)

    # ② LANCZOS 다운스케일
    scaled = interim.resize((tw, th), Image.LANCZOS)

    # ③ UnsharpMask — R/G/B만 처리 (glyph 데이터 채널)
    r, g, b, a = scaled.split()
    usm = ImageFilter.UnsharpMask(
        radius=USM_RADIUS, percent=USM_PERCENT, threshold=USM_THRESHOLD)
    r = r.filter(usm)
    g = g.filter(usm)
    b = b.filter(usm)
    return Image.merge('RGBA', (r, g, b, a)), tw, th


class RowPacker:
    """단순 행 기반 아틀라스 패커."""
    def __init__(self, w, h, pad=1):
        self.image = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        self.w = w; self.h = h; self.pad = pad
        self.cx = pad; self.cy = pad; self.row_h = 0

    def pack(self, glyph):
        if glyph is None:
            return 0, 0
        gw, gh = glyph.size
        if gw == 0 or gh == 0:
            return self.cx, self.cy
        if self.cx + gw + self.pad > self.w:
            self.cx = self.pad
            self.cy += self.row_h + self.pad
            self.row_h = 0
        if self.cy + gh + self.pad > self.h:
            raise OverflowError(
                f"아틀라스 부족: cursor=({self.cx},{self.cy}) glyph={gw}×{gh}")
        x, y = self.cx, self.cy
        self.image.paste(glyph, (x, y))
        self.cx += gw + self.pad
        self.row_h = max(self.row_h, gh)
        return x, y


# ──────────────────────────────────────────────
def main():
    os.makedirs(OUT_FONTS, exist_ok=True)

    print("폰트 파일 파싱 중...")
    v21_chars = parse_fnt(V21_FNT)
    v14_chars = parse_fnt(V14_FNT)
    print(f"  victor21 (원본): {len(v21_chars)}자")
    print(f"  victor14 (모드): {len(v14_chars)}자")
    print(f"  스케일: {SCALE:.3f}  ({SUPER}× NEAREST → LANCZOS → UnsharpMask)")
    print(f"  Korean 예상 높이: {round(15 * SCALE)}px / lineHeight {V21_LINE_HEIGHT}px "
          f"(행간 {V21_LINE_HEIGHT - round(15 * SCALE)}px)")

    print("이미지 로드 중...")
    v21_img = Image.open(V21_PNG).convert('RGBA')
    v14_img = Image.open(V14_PNG).convert('RGBA')

    packer    = RowPacker(ATLAS_W, ATLAS_H, PADDING)
    new_chars = {}

    # ── 1단계: victor21 원본 ASCII 글리프 (그대로)
    print("victor21 ASCII 글리프 패킹 중...")
    ascii_packed = 0
    for cid in sorted(v21_chars):
        c = v21_chars[cid]
        glyph = extract_glyph(v21_img, c)
        if glyph is None:
            new_chars[cid] = dict(id=cid, x=0, y=0,
                                  width=c['width'], height=c['height'],
                                  xoffset=c['xoffset'], yoffset=c['yoffset'],
                                  xadvance=c['xadvance'], page=0, chnl=15)
        else:
            x, y = packer.pack(glyph)
            new_chars[cid] = dict(id=cid, x=x, y=y,
                                  width=glyph.width, height=glyph.height,
                                  xoffset=c['xoffset'], yoffset=c['yoffset'],
                                  xadvance=c['xadvance'], page=0, chnl=15)
        ascii_packed += 1
    print(f"  ASCII {ascii_packed}자 완료")

    # ── 2단계: victor14 한국어 글리프 — 슈퍼샘플링 스케일
    print(f"victor14 한국어 글리프 패킹 중 (scale={SCALE:.3f})...")
    ko_packed = 0
    skipped   = 0
    for cid in sorted(v14_chars):
        if cid in new_chars:
            skipped += 1
            continue
        c     = v14_chars[cid]
        glyph = extract_glyph(v14_img, c)

        xoffset  = round(c['xoffset']  * SCALE)
        yoffset  = round(c['yoffset']  * SCALE)
        xadvance = round(c['xadvance'] * SCALE)

        if glyph is None:
            new_chars[cid] = dict(id=cid, x=0, y=0, width=0, height=0,
                                  xoffset=xoffset, yoffset=yoffset,
                                  xadvance=xadvance, page=0, chnl=15)
        else:
            scaled, tw, th = scale_glyph(glyph, SCALE)
            x, y = packer.pack(scaled)
            new_chars[cid] = dict(id=cid, x=x, y=y, width=tw, height=th,
                                  xoffset=xoffset, yoffset=yoffset,
                                  xadvance=xadvance, page=0, chnl=15)
        ko_packed += 1
        if ko_packed % 1000 == 0:
            print(f"    {ko_packed}자 처리 중...")

    print(f"  한국어 {ko_packed}자 완료 (중복 {skipped}자 생략)")

    # ── 3단계: 아틀라스 PNG 저장
    used_h = packer.cy + packer.row_h + PADDING
    print(f"아틀라스 저장: {OUT_PNG}")
    print(f"  사용 영역: {ATLAS_W}×{used_h}px")
    packer.image.save(OUT_PNG)

    # ── 4단계: .fnt 파일 저장
    total = len(new_chars)
    print(f"폰트 파일 저장: {OUT_FNT}  ({total}자)")
    with open(OUT_FNT, 'w', encoding='utf-8') as f:
        f.write(
            f'info face="Victor\'sPixelFont" size=-21 bold=0 italic=0 charset="" unicode=1 '
            f'stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=1,1 outline=0\n'
        )
        f.write(
            f'common lineHeight={V21_LINE_HEIGHT} base={V21_BASE} '
            f'scaleW={ATLAS_W} scaleH={ATLAS_H} pages=1 packed=0 '
            f'alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0\n'
        )
        f.write('page id=0 file="victor21_0.png"\n')
        f.write(f'chars count={total}\n')
        for cid in sorted(new_chars):
            c = new_chars[cid]
            f.write(
                f'char id={c["id"]} '
                f'x={c["x"]} y={c["y"]} '
                f'width={c["width"]} height={c["height"]} '
                f'xoffset={c["xoffset"]} yoffset={c["yoffset"]} '
                f'xadvance={c["xadvance"]} page={c["page"]} chnl={c["chnl"]}\n'
            )

    print(f"\n완료: {total}자 ({ascii_packed} ASCII + {ko_packed} 한국어+)")
    print(f"출력: {OUT_FONTS}/")


if __name__ == '__main__':
    main()
