"""'The Woods of the West' — film script as data. Dialogue is verbatim from the comic."""

CHARACTERS = {
    "shakes": ("Shakes: scruffy grey-bearded old prospector, battered tan cowboy hat, "
               "gap-toothed, wiry, jabbing a bony finger; comic-relief informant"),
    "pringle": ("Sheriff Pringle: tall gaunt lawman, very long pointed nose, droopy "
                "half-lidded eyes, light shirt with tie, star-badge cowboy hat; deadpan"),
    "cal": ("Cal Dalton: lean villain, tall black stovepipe top hat, handlebar mustache, "
            "dark vest and trousers, weathered glare"),
}

STYLES = {
    "ballpoint": ("hand-drawn ballpoint-pen sketch on lined notebook paper, wobbly ink "
                  "lines, faint blue horizontal rule lines, white paper texture, crude "
                  "charming doodle style"),
    "cartoon": ("clean flat 2D cartoon, bold black outlines, simple cel shading, limited "
                "color palette, Saturday-morning animation look"),
    "cinematic": ("painterly stylized western illustration, warm dusty palette, dramatic "
                  "golden-hour light, cinematic depth, hand-painted texture"),
}

# phase: "bakeoff" = the signature beat rendered in all 3 styles; also part of the full film.
SHOTS = [
    {"id": 1, "beat": "cold_open", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "black screen fading to a distant steam train on the horizon at dusk, wide desert",
     "motion": "slow push-in, heat shimmer, faint smoke drifting"},
    {"id": 2, "beat": "cold_open", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "the 4:55 steam train hissing into a dusty wooden depot, steam billowing across the platform",
     "motion": "steam billows toward camera, train wheels slow to a stop"},
    {"id": 3, "beat": "cold_open", "phase": "film", "speaker": None, "line": None,
     "characters": ["cal"], "visual": "a stovepipe-top-hat silhouette (Cal Dalton) stepping down from the train onto the platform",
     "motion": "boot lands, dust puffs, the figure straightens to full height"},
    {"id": 4, "beat": "warning", "phase": "film", "speaker": "shakes",
     "line": "Sheriff!! Ol' Cal Dalton just arrived on the 4:55, says he's got an old score to settle with you!!",
     "characters": ["shakes"], "visual": "jail office interior, Shakes bursting through the door pointing urgently",
     "motion": "Shakes lurches forward, arm jabbing, mouth moving"},
    {"id": 5, "beat": "warning", "phase": "film", "speaker": "pringle",
     "line": "Well, Shakes, I guess the time has come to play this hand...",
     "characters": ["pringle"], "visual": "Sheriff Pringle at the office window, deadpan, looking out at the street",
     "motion": "slow turn of the head toward the window, faint squint"},
    {"id": 6, "beat": "walk", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "empty dusty main street, shutters closing, a tumbleweed rolling through",
     "motion": "tumbleweed rolls across frame, a shutter bangs closed"},
    {"id": 7, "beat": "walk", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "tight insert of spurred boots and a ticking wall clock reading near 5",
     "motion": "spur rowel spins, clock pendulum swings"},
    {"id": 8, "beat": "walk", "phase": "film", "speaker": "cal",
     "line": "Sheriff Pringle... well well...",
     "characters": ["cal", "pringle"], "visual": "wide two-shot down the street: Cal facing Sheriff Pringle at a distance",
     "motion": "Cal walks slowly forward, coat shifting in the wind"},
    {"id": 9, "beat": "walk", "phase": "film", "speaker": "pringle",
     "line": "H'lo, Cal...",
     "characters": ["pringle"], "visual": "medium of Sheriff Pringle, hand resting near his holster, calm",
     "motion": "slight nod, eyes narrowing"},
    {"id": 10, "beat": "faceoff", "phase": "film", "speaker": "cal",
     "line": "It's been a while, but now it's payback time...",
     "characters": ["cal"], "visual": "close-up of Cal Dalton, menacing under the top hat brim",
     "motion": "lips curl into a sneer, mustache twitches"},
    {"id": 11, "beat": "faceoff", "phase": "film", "speaker": "pringle",
     "line": "You wouldn't shoot me, Cal...",
     "characters": ["pringle"], "visual": "close-up of Sheriff Pringle, unbothered, droopy-eyed",
     "motion": "tiny smirk forming"},
    {"id": 12, "beat": "faceoff", "phase": "film", "speaker": "cal",
     "line": "Oh yeah? Why's that?",
     "characters": ["cal"], "visual": "close-up of Cal, eyebrow raised, gun hand twitching",
     "motion": "head tilts, eyes flick down then up"},
    # --- signature beat (bake-off) ---
    {"id": 13, "beat": "punchline", "phase": "bakeoff", "speaker": "pringle",
     "line": "You wouldn't shoot a man with serious wood...",
     "characters": ["cal", "pringle"], "visual": "two-shot standoff, Sheriff Pringle smug and confident facing Cal",
     "motion": "Pringle's smug grin widens, slight hip shift"},
    {"id": 14, "beat": "punchline", "phase": "bakeoff", "speaker": None, "line": None,
     "characters": ["cal", "pringle"], "visual": "the faithful comic reveal — a lumpy cartoon outline at the sheriff's trousers, framed exactly like the strip; Cal recoils",
     "motion": "Cal's eyes bulge, he flinches back; Pringle stands proud"},
    {"id": 15, "beat": "punchline", "phase": "bakeoff", "speaker": None, "line": None,
     "characters": ["cal"], "visual": "wide shot of Cal Dalton alone in the dusty street, flabbergasted and "
     "defeated, slowly lowering his pistol — a full scene in the town, NOT a character sheet, no labels or text",
     "motion": "gun hand droops, shoulders slump"},
    {"id": 16, "beat": "end", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "freeze on the dusty street, hand-lettered 'END' card over the frame",
     "motion": "gentle freeze, slight film-grain flicker"},
]


def shots_for_phase(phase: str) -> list:
    if phase == "bakeoff":
        return [sh for sh in SHOTS if sh["phase"] == "bakeoff"]
    if phase == "film":
        return list(SHOTS)
    raise ValueError(f"unknown phase: {phase!r} (use 'bakeoff' or 'film')")


def style_prefix(style: str) -> str:
    return STYLES[style]
