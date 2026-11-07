"""Build the Nast Brain dataset: distill event->concept pairs (open-weight teacher).

  export OPENROUTER_API_KEY=sk-or-...
  python packs/nast/brain/build_dataset.py --n 250 --out packs/nast/data/brain/all.jsonl

Gold seeds are held out as the eval/test set (see plan Task 7); they are NOT merged here.
"""
import argparse, json, os, urllib.request
from pathlib import Path

SYSTEM = ("You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, "
          "respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the "
          "satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom.")
TEACHER = "deepseek/deepseek-chat"
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
REQUIRED = {"allegory_rationale", "image_prompt"}


def parse_pair(raw: str):
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[s.find("{"):s.rfind("}") + 1]
    try:
        obj = json.loads(s)
    except Exception:
        return None
    if not isinstance(obj, dict) or REQUIRED != set(obj):
        return None
    return {k: obj[k] for k in REQUIRED}


def to_message_row(event: str, pair: dict) -> dict:
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": event if event.startswith("Event:") else f"Event: {event}"},
        {"role": "assistant", "content": json.dumps(pair, ensure_ascii=False)},
    ]}


def _call(prompt: str) -> str:
    body = json.dumps({"model": TEACHER, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(OPENROUTER, data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


# Seed events the teacher translates into Nast concepts. ~50 distinct events spanning
# finance, big tech, municipal, press, elections, labor, healthcare, environment,
# housing, immigration, surveillance, monopolies, lobbying, and justice (Task 7).
SEED_EVENTS = [
    # Finance / Banking
    "A regulator quietly takes a lucrative job at the very bank it spent years overseeing.",
    "A central bank bails out reckless speculators while ordinary depositors lose their savings.",
    "A credit-rating agency gives its highest marks to bonds it secretly knows are worthless.",
    "A hedge fund shorts a company into bankruptcy, then acquires its assets for pennies.",
    "Bankers award themselves record bonuses the same week they accept a public rescue package.",
    "A payday lender charges triple-digit interest rates to workers with no other options.",
    "An investment firm lobbies to gut the consumer-protection agency investigating its practices.",
    # Big Tech / Monopoly
    "A platform quietly buries search results for rivals while promoting its own identical service.",
    "A single cloud-computing conglomerate acquires so many startups that engineers joke the industry has one employer.",
    "A social-media giant uses personal data harvested without consent to micro-target voters.",
    "A dominant app store demands a 30 percent cut of every transaction and bans outside payment links.",
    "A tech firm patents a basic human gesture to block competitors from building accessible tools.",
    "An advertising duopoly controls the pipes that fund journalism while siphoning off that revenue.",
    # Municipal / Local-Government Corruption
    "A mayor funnels city paving contracts to relatives while roads in poor neighborhoods remain potholed.",
    "A school-board official steers curriculum contracts to a firm whose founder financed the official's campaign.",
    "A city inspector signs off on unsafe buildings after accepting cash envelopes from developers.",
    "A public-housing authority demolishes affordable units, then sells the land to luxury builders.",
    "A county clerk purges voter rolls in opposition districts just weeks before an election.",
    "A police union blocks an independent oversight board from seeing misconduct records.",
    # Press / Free Speech
    "A media conglomerate fires investigative reporters and replaces them with sponsored content teams.",
    "An online platform claims neutrality while quietly down-ranking stories that embarrass its major advertisers.",
    "A government agency labels a journalist's leaked documents a threat to national security to avoid accountability.",
    "A billionaire buys a newspaper and transforms its editorial page into a personal political mouthpiece.",
    "A local TV station chain forces anchors to read identical political commentary scripts written at corporate headquarters.",
    # Elections / Democracy
    "A legislature draws district boundaries so tortured that one party is guaranteed to win every seat.",
    "A political committee floods an election with anonymous dark money routed through shell nonprofits.",
    "A demagogue claims an election was stolen the moment early returns show him losing.",
    "Voting machines are contracted to a firm whose executives publicly donated to one candidate's campaign.",
    "Lawmakers schedule polling places in opposition neighborhoods to close an hour after polls open.",
    # Labor / Workers
    "A warehouse employer fires workers who circulate a union petition, then hires replacements at lower wages.",
    "A gig-economy platform classifies drivers as independent contractors to avoid paying benefits, then lobbies to cement that classification in law.",
    "A factory outsources its workforce to a temp agency the day before pension rights would have vested.",
    "A meatpacking plant speeds up production lines until injuries spike, then pressures supervisors to misreport accidents.",
    "An employer requires workers to attend mandatory anti-union meetings but denies them a forum to hear the other side.",
    # Healthcare
    "A pharmaceutical firm acquires the patent on a life-saving drug and immediately raises the price four-hundredfold.",
    "An insurance company denies a claim for emergency surgery, citing a technicality buried in fine print.",
    "A hospital system merges with its only local competitor, then raises prices knowing patients have nowhere else to go.",
    "A nursing-home chain cuts staff ratios to minimum-wage skeleton crews while reporting record profits.",
    "A drug distributor floods rural counties with opioids while its compliance officers sign off on suspicious orders.",
    # Environment
    "An industrial plant dumps chemical waste upstream of a city's drinking-water intake, then disputes its own internal test results.",
    "A fossil-fuel lobby funds a network of think tanks to manufacture doubt about climate science.",
    "A developer drains a protected wetland after donating generously to the permitting board's reelection campaigns.",
    "A mining company leaves a poisoned tailings pond behind and declares bankruptcy to escape cleanup costs.",
    "A utility company charges ratepayers for the cost of lobbying against clean-energy regulations.",
    # Housing
    "An investment fund buys thousands of single-family homes and raises rents beyond what local workers can afford.",
    "A city council rezones a neighborhood for luxury towers but exempts itself from including any affordable units.",
    "A landlord lets a building fall into disrepair to force out rent-stabilized tenants and attract higher-paying ones.",
    # Immigration / Surveillance / Lobbying / Justice
    "A private prison company lobbies for mandatory-minimum sentencing laws that guarantee it a full occupancy rate.",
    "A government agency buys commercial data brokers' location records to track protesters without obtaining a warrant.",
    "An immigration detention contractor profits per bed filled, creating a financial incentive to maximize detentions.",
    "A lobbying firm representing foreign interests files as a domestic public-relations consultancy to avoid disclosure.",
    "A prosecutor charges indigent defendants with dozens of minor offenses simultaneously, knowing they cannot afford counsel for each.",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--out", default="packs/nast/data/brain/all.jsonl")
    a = ap.parse_args()

    import time
    events = (SEED_EVENTS * (a.n // len(SEED_EVENTS) + 1))[:a.n]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    kept = tried = 0
    # incremental write + skip-on-error so one transient API failure never loses progress
    with open(a.out, "w", encoding="utf-8") as f:
        for ev in events:
            tried += 1
            try:
                pair = parse_pair(_call(f"Event: {ev}"))
            except Exception as e:
                print(f"  call {tried} failed: {e}", flush=True)
                time.sleep(2)
                continue
            if pair:
                f.write(json.dumps(to_message_row(ev, pair), ensure_ascii=False) + "\n")
                f.flush()
                kept += 1
            if tried % 25 == 0:
                print(f"  progress {kept}/{tried} kept", flush=True)
            time.sleep(0.3)
    print(f"distilled {kept}/{tried} -> {a.out}")


if __name__ == "__main__":
    main()
