"""10분 본편에서 핵심 장면만 이어 3분 하이라이트와 포스터 이미지를 만든다 (GitHub Pages 포트폴리오용).

    .venv/Scripts/python docs/video/tools/highlight3.py

- 장면 단위로 잘라(문장이 중간에 끊기지 않게) 0.25초 페이드로 잇고, 1280x720 · H.264 · AAC 로 인코딩
- 결과: docs/video/3조_highlight_3min.mp4, assets/img/poster-full.jpg · poster-highlight.jpg (본편 실제 프레임)
"""

from common import ROOT, VIDEO, duration, run, scene_starts
from video_scenes import SCENES

FINAL = VIDEO / "3조_final.mp4"
OUT = VIDEO / "3조_highlight_3min.mp4"
IMG = ROOT / "assets" / "img"
PICK = ["p01", "d03", "d04", "d05", "d06", "d07", "d10", "a00", "a04", "c00"]
FADE = 0.25


def main() -> None:
    starts, dur = scene_starts(SCENES), {s["id"]: s["dur"] for s in SCENES}
    inputs, chains = [], []
    for i, sid in enumerate(PICK):
        d = dur[sid]
        inputs += ["-ss", starts[sid], "-t", d, "-i", FINAL]
        chains.append(f"[{i}:v]scale=1280:720,setsar=1,fps=30,fade=in:st=0:d={FADE},fade=out:st={d - FADE}:d={FADE},setpts=PTS-STARTPTS[v{i}]")
        chains.append(f"[{i}:a]afade=in:st=0:d={FADE},afade=out:st={d - FADE}:d={FADE},asetpts=PTS-STARTPTS[a{i}]")
    pairs = "".join(f"[v{i}][a{i}]" for i in range(len(PICK)))
    chains.append(f"{pairs}concat=n={len(PICK)}:v=1:a=1[v][a]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p", "-b:v", "1100k", "-maxrate", "2200k",
         "-bufsize", "4400k", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-metadata:s:a:0", "language=kor",
         "-metadata", "title=datapick 3분 하이라이트", "-movflags", "+faststart", OUT])
    print(f"highlight: {OUT.name} {duration(OUT):.1f}s {OUT.stat().st_size / 1e6:.1f}MB  ({' → '.join(PICK)})")

    IMG.mkdir(parents=True, exist_ok=True)
    for name, t in (("poster-full", starts["p01"] + 6), ("poster-highlight", starts["d04"] + 6)):
        run(["ffmpeg", "-y", "-ss", t, "-i", FINAL, "-frames:v", 1, "-vf", "scale=1280:-2", "-q:v", 3, IMG / f"{name}.jpg"])
    print("posters:", ", ".join(p.name for p in sorted(IMG.glob("poster-*.jpg"))))


if __name__ == "__main__":
    main()
