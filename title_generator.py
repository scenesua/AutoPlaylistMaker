"""
타이틀 자동 생성기 - Auto Playlist Maker용
주제어 기반 고유 곡 제목 생성 및 파일명 대체
"""

import os
import re
import random
import shutil

THEMES = {
    "일렉트로닉": {
        "adj": ["Neon", "Digital", "Electric", "Synthetic", "Binary", "Phantom", "Virtual",
                 "Cyber", "Laser", "Pixel", "Glitch", "Crystal", "Hologram", "Cosmic",
                 "Quantum", "Prism", "Echo", "Pulse", "Shadow", "Ultra"],
        "noun": ["Wave", "Beat", "Dream", "Signal", "Circuit", "Frequency", "Pulse",
                 "Horizon", "Void", "Storm", "System", "Vector", "Droid", "Station",
                 "Nebula", "Grid", "Core", "Phase", "Code", "Drift"],
        "verb": ["Echo", "Pulse", "Drift", "Glide", "Fade", "Phase", "Warp",
                 "Shift", "Resonate", "Oscillate", "Reverb", "Loop", "Crash", "Slide"]
    },
    "힙합": {
        "adj": ["Urban", "Street", "Golden", "Dope", "Raw", "Chill", "Smooth",
                 "Hard", "Bold", "Fresh", "Cali", "Southside", "Eastside", "Dark",
                 "Real", "Thug", "Gangsta", "Funky", "Retro", "Gritty"],
        "noun": ["Flow", "Vibe", "Crew", "Block", "King", "Queen", "Beat",
                 "Mic", "Rhymer", "Groove", "Hustle", "Crown", "Legend", "Soul",
                 "Clique", "Empire", "Kingdom", "Night", "Swagger", "Boss"],
        "verb": ["Hustle", "Flow", "Rise", "Shine", "Ride", "Grind", "Ball",
                 "Flex", "Rule", "Spit", "Rep", "Rock", "Stomp", "Glow"]
    },
    "발라드": {
        "adj": ["Fading", "Tender", "Broken", "Bittersweet", "Gentle", "Starlit",
                 "Lovely", "Lonely", "Silent", "Warm", "Cold", "Empty", "Pure",
                 "Last", "First", "Beautiful", "Deep", "Distant", "Precious", "Soft"],
        "noun": ["Memory", "Tears", "Heart", "Promise", "Letter", "Star", "Rain",
                 "Embrace", "Moment", "Whisper", "Light", "Kiss", "Dream", "Love",
                 "Song", "Story", "Rose", "Night", "Smile", "Sadness"],
        "verb": ["Remember", "Wait", "Cry", "Love", "Hold", "Miss", "Wish",
                 "Promise", "Breathe", "Pray", "Call", "Believe", "Stay", "Fall"]
    },
    "락": {
        "adj": ["Rebel", "Wild", "Electric", "Loud", "Raging", "Burning", "Broken",
                 "Fighting", "Savage", "Thunder", "Fierce", "Free", "Restless", "Stormy",
                 "Crazy", "Blazing", "Ruthless", "Untamed", "Vicious", "Infernal"],
        "noun": ["Fire", "Storm", "Rebellion", "Guitar", "Thunder", "Riot", "Flame",
                 "Warrior", "Highway", "Hammer", "Chain", "Rage", "Bullet", "Wings",
                 "Demon", "Angel", "Soldier", "Nightmare", "Revolution", "Crowd"],
        "verb": ["Burn", "Fight", "Rise", "Crash", "Scream", "Break", "Rage",
                 "Roar", "Strike", "Shred", "Defy", "Charge", "Conquer", "Unleash"]
    },
    "재즈": {
        "adj": ["Blue", "Cool", "Smooth", "Midnight", "Smoky", "Mellow", "Groovy",
                 "Slow", "Hot", "Lazy", "Deep", "Velvet", "Golden", "Bluesy",
                 "Soulful", "Hazy", "Melancholy", "Quiet", "Dim", "Silky"],
        "noun": ["Moon", "Cafe", "Sax", "Night", "Mood", "Blues", "Rhythm",
                 "Melody", "Swing", "Smoke", "Piano", "Trumpet", "Bourbon", "Dream",
                 "Lounge", "Club", "Mist", "Breeze", "Rain", "Dusk"],
        "verb": ["Swing", "Croon", "Slide", "Drift", "Sigh", "Groove", "Jam",
                 "Whisper", "Wail", "Sway", "Stroll", "Glide", "Serenade", "Melt"]
    },
    "클래식": {
        "adj": ["Eternal", "Sacred", "Majestic", "Tragic", "Grand", "Serene",
                 "Solemn", "Celestial", "Mystic", "Symphonic", "Opulent", "Dramatic",
                 "Noble", "Harmonious", "Divine", "Melancholic", "Triumphant", "Luminous",
                 "Enchanted", "Glorious"],
        "noun": ["Sonata", "Nocturne", "Symphony", "Waltz", "Concerto", "Overture",
                 "Prelude", "Rhapsody", "Crescendo", "Elegy", "Fugue", "Etude",
                 "March", "Ballade", "Fantasia", "Requiem", "Serenade", "Cantata",
                 "Aria", "Movement"],
        "verb": ["Soar", "Resonate", "Transcend", "Unfold", "Enchant", "Illuminate",
                 "Awaken", "Flow", "Cascade", "Whisper", "Bloom", "Glide",
                 "Float", "Reverberate", "Ascend"]
    },
    "POP": {
        "adj": ["Dancing", "Electric", "Summer", "Candy", "Happy", "Shining",
                 "Catchy", "Party", "Sugar", "Sunny", "Sweet", "Bubble", "Neon",
                 "Sparkle", "Tropical", "Dreamy", "Golden", "Midnight", "Daydream", "Starlight"],
        "noun": ["Heart", "Dance", "Love", "Summer", "Party", "Night", "Star",
                 "Dream", "Girl", "Boy", "Magic", "Rhythm", "Song", "Cherry",
                 "Fantasy", "Melody", "Sunshine", "Candy", "Bubble", "Disco"],
        "verb": ["Dance", "Sing", "Shine", "Love", "Party", "Dream", "Jump",
                 "Twirl", "Sparkle", "Glow", "Celebrate", "Groove", "Smile", "Fly"]
    },
    "R&B": {
        "adj": ["Smooth", "Silky", "Velvet", "Slow", "Sexy", "Sweet", "Deep",
                 "Soulful", "Passionate", "Midnight", "Brown", "Honey", "Dripping",
                 "Tender", "Sublime", "Intimate", "Seductive", "Sultry", "Pure", "Sensual"],
        "noun": ["Soul", "Groove", "Passion", "Body", "Touch", "Skin", "Honey",
                 "Velvet", "Silk", "Rhythm", "Desire", "Embrace", "Whisper", "Sensation",
                 "Essence", "Motion", "Vibe", "Bliss", "Ecstasy", "Sugar"],
        "verb": ["Feel", "Touch", "Sway", "Groove", "Breathe", "Desire", "Caress",
                 "Whisper", "Melt", "Move", "Flow", "Yearn", "Surrender", "Entwine"]
    },
    "인디": {
        "adj": ["Fading", "Pale", "Quiet", "Strange", "Sunken", "Lost", "Glowing",
                 "Hollow", "Dreamy", "Hazy", "Frosted", "Withered", "Drifting",
                 "Shy", "Lazy", "Ghostly", "Cotton", "Silver", "Fragile", "Drowsy"],
        "noun": ["Cloud", "Pillow", "Ghost", "Forest", "River", "Window", "Road",
                 "Bicycle", "Balcony", "Paperback", "Lantern", "Meadow", "Moth",
                 "Basement", "Rooftop", "Overpass", "Cottage", "Mountain", "Comet", "Nest"],
        "verb": ["Drift", "Float", "Fade", "Wander", "Linger", "Sway", "Breathe",
                 "Dream", "Sail", "Bloom", "Drizzle", "Crawl", "Roam", "Sink"]
    }
}

PATTERNS = [
    "{adj} {noun}",
    "{adj} {noun}",
    "{adj} {noun}",
    "The {adj} {noun}",
    "{noun} of {noun2}",
    "{noun} of the {adj}",
    "{verb} the {noun}",
    "{verb} in the {noun}",
    "{adj} {noun} of {noun2}",
    "{verb}ing {noun}",
    "{adj} {noun} ({verb})",
    "{noun} & {noun2}",
    "{verb} Me {adv}",
    "{adj} {noun} {adj2}",
    "Never {verb}",
    "{verb} Again",
]

ADVERBS = ["Tonight", "Forever", "Again", "Away", "Slowly", "Always", "Never", "Together"]


def _ensure_theme(theme):
    theme = theme.strip().lower()
    for key in THEMES:
        if key.lower() == theme or theme in key.lower():
            return key
    return None


def _pick(pool):
    return random.choice(pool)


def generate_titles(count=10, theme=None, max_attempts=200):
    if theme:
        key = _ensure_theme(theme)
        if not key:
            available = ", ".join(THEMES.keys())
            raise ValueError(f"테마 '{theme}'를 찾을 수 없습니다. 가능한 테마: {available}")
        word_pool = THEMES[key]
    else:
        word_pool = {
            "adj": [],
            "noun": [],
            "verb": [],
        }
        for t in THEMES.values():
            word_pool["adj"].extend(t["adj"])
            word_pool["noun"].extend(t["noun"])
            word_pool["verb"].extend(t["verb"])
        for k in word_pool:
            word_pool[k] = list(set(word_pool[k]))

    titles = set()
    attempts = 0
    while len(titles) < count and attempts < max_attempts:
        attempts += 1
        pattern = _pick(PATTERNS)
        kwargs = {
            "adj": _pick(word_pool["adj"]),
            "adj2": _pick(word_pool["adj"]),
            "noun": _pick(word_pool["noun"]),
            "noun2": _pick(word_pool["noun"]),
            "verb": _pick(word_pool["verb"]),
            "adv": _pick(ADVERBS),
        }
        title = pattern.format(**kwargs)
        if title not in titles:
            titles.add(title)

    return list(titles)[:count]


def rename_files_by_title(directory, titles, ext_map=None, dry_run=True):
    if ext_map is None:
        ext_map = {".wav": ".wav", ".mp3": ".mp3", ".flac": ".flac",
                   ".ogg": ".ogg", ".m4a": ".m4a", ".wma": ".wma",
                   ".aac": ".aac", ".aiff": ".aiff"}

    files = []
    for f in os.listdir(directory):
        ext = os.path.splitext(f)[1].lower()
        if ext in ext_map:
            files.append(f)

    files.sort()
    if not files:
        print("[INFO] 변환할 오디오 파일이 디렉토리에 없습니다.")
        return

    if len(files) != len(titles):
        print(f"[WARN] 파일 수({len(files)})와 타이틀 수({len(titles)})가 다릅니다.")
        use_count = min(len(files), len(titles))
        files = files[:use_count]
        titles = titles[:use_count]

    safe_re = re.compile(r'[^\w\- ]')
    results = []
    for old_name, title in zip(files, titles):
        safe_title = safe_re.sub('', title).strip()
        ext = os.path.splitext(old_name)[1]
        new_name = f"{safe_title}{ext}"
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)

        if dry_run:
            results.append((old_name, new_name))
        else:
            if old_path == new_path:
                results.append((old_name, new_name))
                continue
            if os.path.exists(new_path):
                base, ext = os.path.splitext(new_name)
                idx = 2
                while os.path.exists(os.path.join(directory, f"{base}_{idx}{ext}")):
                    idx += 1
                new_name = f"{base}_{idx}{ext}"
                new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            results.append((old_name, new_name))

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto Playlist Maker - 타이틀 자동 생성기")
    parser.add_argument("-c", "--count", type=int, default=10, help="생성할 타이틀 수 (기본: 10)")
    parser.add_argument("-t", "--theme", type=str, default=None, help="테마 (일렉트로닉, 힙합, 발라드, 락, 재즈, 클래식, POP, R&B, 인디)")
    parser.add_argument("--list-themes", action="store_true", help="사용 가능한 테마 목록 출력")
    parser.add_argument("--rename", type=str, default=None, metavar="DIR",
                        help="지정한 디렉토리의 오디오 파일명을 생성된 타이틀로 변경")
    parser.add_argument("--dry-run", action="store_true",
                        help="--rename과 함께 사용: 실제 변경 없이 미리보기만 출력")
    parser.add_argument("--no-number", action="store_true", help="출력 시 번호 생략")

    args = parser.parse_args()

    if args.list_themes:
        print("사용 가능한 테마:")
        for name in THEMES:
            print(f"  - {name}")
        return

    try:
        titles = generate_titles(count=args.count, theme=args.theme)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    if args.rename:
        dir_path = args.rename
        if not os.path.isdir(dir_path):
            print(f"[ERROR] 디렉토리를 찾을 수 없습니다: {dir_path}")
            return
        results = rename_files_by_title(dir_path, titles, dry_run=args.dry_run)
        if not results:
            return
        if args.dry_run:
            print("[DRY RUN] 변경 예정:")
            for old, new in results:
                print(f"  {old}  ->  {new}")
            print(f"\n총 {len(results)}개 파일 변경 예정 (--dry-run 제거 시 실제 변경)")
        else:
            print("[OK] 파일명 변경 완료:")
            for old, new in results:
                print(f"  {old}  ->  {new}")
    else:
        for i, title in enumerate(titles, 1):
            prefix = f"{i}. " if not args.no_number else ""
            print(f"{prefix}{title}")
        print(f"\n총 {len(titles)}개 타이틀 생성됨 (테마: {args.theme or '혼합'})")


if __name__ == "__main__":
    main()
