#!/usr/bin/env python3
"""
Texas Tows GMB Posting Script
Schedule: every 3 days at 9am CT (0 14 */3 * * UTC)
Pillar rotation: 8-slot weighted list (accident_recovery 3x).
Service area rotation independent.
Image: prefers real photos from Google Drive, falls back to AI generation.
"""

import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from gmb_post_lib import (
    get_access_token, post_to_gbp, strip_phone_numbers,
    check_dedup, record_post, load_state, save_state,
    generate_image, upload_to_github,
    list_drive_files, download_drive_file, convert_to_jpeg,
)

# ── Config ────────────────────────────────────────────────────────────────────

ACCOUNT_ID  = "115031750744438008488"
LOCATION_ID = "18091780695163001569"
CTA_TYPE    = "CALL"

DRIVE_FOLDER_ID = "1_zIizZ8rgvvKNz2-MEDp9gzWTCwTkYZ0"

GITHUB_REPO   = "stephen-huskytail/automation411"
GITHUB_SUBDIR = "gmb/texas-tows"

STATE_FILE = os.path.join(os.path.dirname(__file__), "state_texas_tows.json")

STATE_DEFAULTS = {
    "pillar_index": 0,
    "area_index": 0,
    "post_counts": {},
    "used_images": [],   # track used Drive file IDs to avoid repeats
    "last_post": None,
}

# Weighted pillar rotation — accident_recovery appears 3x
PILLAR_ROTATION = [
    "emergency_cta",
    "accident_recovery",
    "safety_tips",
    "accident_recovery",
    "service_spotlight",
    "trust_social_proof",
    "accident_recovery",
    "local_seasonal",
]

SERVICE_AREAS = [
    "Preston Hollow",
    "Lake Highlands",
    "North Dallas",
    "Lower Greenville",
    "Medical District",
    "SMU/University Park",
    "Uptown Dallas",
    "Oak Lawn",
    "Deep Ellum",
    "White Rock Lake",
    "Lakewood",
    "Garland Road",
]

# Image MIME types that are photos
PHOTO_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}

# ── Content templates ─────────────────────────────────────────────────────────

CONTENT = {
    "emergency_cta": {
        "texts": [
            "Stuck on the side of the road in {area}? Texas Tows has you covered — 24 hours a day, 7 days a week.\n\nA real person answers every call. No bots. No hold music. Just fast dispatch and a tow truck on the way.\n\nBreakdown, flat tire, dead battery, or anything else — call Texas Tows. Dallas/Fort Worth's most reliable 24/7 towing service.",
            "When your car breaks down in {area}, you don't have time to wait.\n\nTexas Tows dispatches fast — we know DFW roads and we know how to get to you quickly. 24/7 towing, accident recovery, winch outs, lockouts, and more.\n\nKeep our number saved. One call, fast response.",
            "3am breakdown in {area}? We're still answering.\n\nTexas Tows runs 24 hours a day, 365 days a year — because roadside emergencies don't follow business hours. Real dispatchers, fast response, fair pricing.\n\nDallas/Fort Worth's trusted 24/7 tow service. Save our number now.",
        ],
        "image_prompts": [
            "Professional tow truck arriving at night to help a stranded driver on a Dallas highway, emergency lighting, reassuring and fast-response aesthetic, 16:9 aspect ratio",
            "24/7 towing service dispatch graphic with bold red and black colors, Dallas skyline background, urgent and reliable emergency service feel, 16:9",
            "Tow truck operator speaking with a relieved driver on a Texas highway at night, professional roadside assistance, warm safety lighting, 16:9",
        ],
    },
    "accident_recovery": {
        "texts": [
            "After an accident in {area}, the last thing you need is to fight with your towing service.\n\nTexas Tows operates insurance-friendly flatbed towing for collision-damaged vehicles — we document everything properly and work alongside your claim from the start.\n\nTDLR licensed. Certified operators. Dallas/Fort Worth accident recovery specialists.",
            "Flatbed towing is the safest way to move a vehicle after a collision.\n\nUnlike wheel-lift towing, flatbed protects all four wheels and prevents additional drivetrain damage to a car that's already been through an accident in {area}.\n\nTexas Tows specializes in post-collision recovery across Dallas/Fort Worth. Call us first — before the tow lot does.",
            "If your vehicle was in an accident in {area}, where it gets towed matters.\n\nTexas Tows provides certified accident recovery — TDLR licensed, insurance-coordinated, and flatbed equipped for collision-damaged vehicles. We protect your claim from the first call.\n\nDFW's accident recovery specialists. Available 24/7.",
        ],
        "image_prompts": [
            "Professional flatbed tow truck loading a collision-damaged vehicle after a highway accident near Dallas, daytime, safety cones visible, insurance-professional feel, 16:9 aspect ratio",
            "Texas Tows flatbed tow truck at accident scene on Dallas freeway, emergency lighting, TDLR certified professional look, 16:9",
            "Clean professional graphic showing accident recovery towing service with insurance coordination icons, Dallas skyline background, red and black brand colors, 16:9",
        ],
    },
    "safety_tips": {
        "texts": [
            "Breaking down on I-30 or US-75 near {area}? Here's what to do:\n\n1. Signal and move as far right as possible\n2. Turn on hazard lights immediately\n3. Stay in the vehicle if you can — exit only when safe\n4. Call for a tow before you call anyone else\n\nTexas Tows — Dallas/Fort Worth 24/7 emergency towing. Save our number.",
            "Texas summers hit hard. DFW heat is one of the top causes of roadside breakdowns near {area}.\n\nBefore temps spike: check coolant levels, battery charge, and tire pressure. Overinflated tires blow in extreme heat — and underinflated tires wear out fast.\n\nIf you do break down, Texas Tows responds fast, day or night.",
            "Highway safety tip for DFW drivers near {area}:\n\nIf you're in an accident and your car is drivable, move it out of travel lanes if possible — then stop and stay with the vehicle. Never stand on the highway itself.\n\nFor accidents where the vehicle can't move: call 911, then call Texas Tows for accident-scene recovery. We're TDLR licensed and insurance-ready.",
        ],
        "image_prompts": [
            "Road safety infographic with highway breakdown tips, Dallas/Fort Worth highway signs, clean bold graphic design, red and white safety colors, 16:9 aspect ratio",
            "Texas summer heat car breakdown prevention tips graphic, sun glare on highway, Dallas skyline, educational infographic style, red and orange, 16:9",
            "Dallas freeway safety guide graphic with emergency tips, professional clean design, bold typography, Texas road aesthetic, 16:9",
        ],
    },
    "service_spotlight": {
        "texts": [
            "Texas Tows handles more than just breakdowns in {area}.\n\nOur full service menu:\n✓ 24/7 emergency towing\n✓ Flatbed towing (accident and luxury vehicles)\n✓ Junk car removal — we pay cash\n✓ Winch outs (off-road, mud, ditch)\n✓ Lockout service\n✓ Accident recovery\n\nDallas/Fort Worth's complete roadside solution. One number for all of it.",
            "Got a junk car taking up space in {area}? Texas Tows will remove it — and we pay cash for qualifying vehicles.\n\nNo title required in many cases. Free tow, fast pickup, and you walk away with money instead of headaches.\n\nCall Texas Tows for junk car removal across the Dallas/Fort Worth area.",
            "Stuck in a ditch or off-road in {area}? Texas Tows runs winch-out recovery for vehicles that need more than a standard tow.\n\nMud, ditch, embankment, or rough terrain — our equipment and operators are built for recovery, not just towing.\n\n24/7 Dallas/Fort Worth. Call when standard towing won't cut it.",
        ],
        "image_prompts": [
            "Texas Tows service lineup infographic showing towing, flatbed, junk removal, winch out, and lockout icons, professional Texas red and black branding, Dallas backdrop, 16:9 aspect ratio",
            "Tow truck performing dramatic winch-out recovery pulling a stuck vehicle from a muddy Texas ditch, powerful equipment showcase, 16:9",
            "Clean graphic showing junk car removal service — old vehicle being loaded on flatbed in a residential Dallas neighborhood, cash-for-cars theme, 16:9",
        ],
    },
    "trust_social_proof": {
        "texts": [
            "309+ Google reviews. 4.9-star average. Every review from a real customer in the Dallas/Fort Worth area.\n\nTexas Tows has built that reputation in {area} and across DFW by doing one thing consistently: showing up fast, doing the job right, and treating every driver like a priority.\n\nTDLR licensed. First responder discount available. Dallas's most trusted towing service.",
            "4.9 stars from 309+ DFW customers doesn't happen by accident.\n\nIn {area} and across Dallas/Fort Worth, Texas Tows has earned its reputation through reliable dispatch, professional operators, and transparent pricing — every single call.\n\nTDLR licensed. First responder and military discounts. Save our number before you need it.",
            "When you call Texas Tows from {area}, you're calling a company with 309+ five-star reviews and a TDLR license backing every job.\n\nWe're not a middleman dispatch service. We're local Dallas/Fort Worth operators who take pride in the work.\n\nFirst responder discount. 24/7 availability. Real people. Call us.",
        ],
        "image_prompts": [
            "5-star towing company trust graphic with gold stars, 309+ reviews badge, TDLR licensed seal, Texas flag accent, professional and reliable aesthetic, 16:9 aspect ratio",
            "Trust and social proof graphic for Texas towing company — review count, star rating, licensed badge, Dallas/Fort Worth background, red and black brand colors, 16:9",
            "Professional tow operator giving thumbs up next to Texas Tows truck with 4.9-star rating overlay, Dallas skyline at dusk, warm and trustworthy visual, 16:9",
        ],
    },
    "local_seasonal": {
        "texts": [
            "I-30 and US-75 near {area} — if you've driven them, you know: Dallas highways don't forgive much.\n\nHigh-speed traffic, sudden weather changes, and heavy truck lanes make DFW breakdowns more dangerous than most cities. Texas Tows knows these roads and responds accordingly — fast, professional, and experienced.\n\n24/7 towing for Dallas, Fort Worth, and all surrounding areas.",
            "Dallas summers mean triple-digit heat, and that means your car battery is on borrowed time in {area}.\n\nExtreme heat kills car batteries faster than cold weather does. If yours is more than 3 years old, get it tested before it strands you.\n\nWhen it does go — and they often do without warning — Texas Tows is 24/7 and ready to get you moving again.",
            "From {area} to Downtown Dallas to Deep Ellum — Texas Tows covers all of DFW, not just the main corridors.\n\nWe know the back streets, the one-ways, and the shortcuts. That local knowledge means faster response when you're stuck and every minute counts.\n\nDFW's local towing specialists. 24/7, every day.",
        ],
        "image_prompts": [
            "Dallas/Fort Worth highway landscape graphic showing I-30 and local highway markers, tow truck in foreground, Texas big sky aesthetic, 16:9 aspect ratio",
            "Texas summer heat automotive breakdown prevention graphic, scorching Dallas sun, car battery and coolant check infographic, bold Texas red and yellow, 16:9",
            "Aerial view of Dallas highway interchange at sunset with a Texas Tows truck responding, local towing service geographic reach, 16:9",
        ],
    },
}


def get_drive_image(token: str, state: dict) -> bytes | None:
    """Try to get an unused image from the Texas Tows Google Drive folder."""
    try:
        files = list_drive_files(DRIVE_FOLDER_ID, token)
        photo_files = [f for f in files if f.get("mimeType") in PHOTO_MIMES]
        used = set(state.get("used_images", []))
        unused = [f for f in photo_files if f["id"] not in used]

        if not unused:
            # All used — reset the tracking and start over
            print("[Texas Tows GMB] All Drive images used — resetting tracker.")
            state["used_images"] = []
            unused = photo_files

        if not unused:
            print("[Texas Tows GMB] No photos found in Drive folder.")
            return None

        selected = unused[0]
        print(f"[Texas Tows GMB] Downloading Drive image: {selected['name']} ({selected['id']})")
        raw_bytes = download_drive_file(selected["id"], token)
        jpeg_bytes = convert_to_jpeg(raw_bytes)

        # Record as used
        state["used_images"] = state.get("used_images", []) + [selected["id"]]
        return jpeg_bytes

    except Exception as e:
        print(f"[Texas Tows GMB] Drive image fetch failed: {e}")
        return None


def main():
    # ── Load secrets ──────────────────────────────────────────────────────────
    client_id     = os.environ.get("HERMES_GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("HERMES_GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("HERMES_GOOGLE_REFRESH_TOKEN")
    openai_key    = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API")
    github_token  = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

    for name, val in [
        ("HERMES_GOOGLE_CLIENT_ID", client_id),
        ("HERMES_GOOGLE_CLIENT_SECRET", client_secret),
        ("HERMES_GOOGLE_REFRESH_TOKEN", refresh_token),
        ("OPENAI_API_KEY / OPENAI_API", openai_key),
        ("GITHUB_TOKEN / GITHUB_PAT", github_token),
    ]:
        if not val:
            print(f"[ERROR] Missing env var: {name}")
            sys.exit(1)

    # ── Load state ────────────────────────────────────────────────────────────
    state = load_state(STATE_FILE, STATE_DEFAULTS)

    # ── Dedup guard ───────────────────────────────────────────────────────────
    if not check_dedup(state, guard_hours=20):
        sys.exit(0)

    # ── Select pillar + area ──────────────────────────────────────────────────
    pillar_idx = state["pillar_index"] % len(PILLAR_ROTATION)
    area_idx   = state["area_index"] % len(SERVICE_AREAS)
    pillar     = PILLAR_ROTATION[pillar_idx]
    area       = SERVICE_AREAS[area_idx]
    content    = CONTENT[pillar]

    post_num = state["post_counts"].get(pillar, 0)
    text_raw = content["texts"][post_num % len(content["texts"])]
    ai_prompt = content["image_prompts"][post_num % len(content["image_prompts"])]

    # Strip phone numbers, inject area
    text = strip_phone_numbers(text_raw.format(area=area))

    print(f"[Texas Tows GMB] Pillar: {pillar} | Area: {area}")
    print(f"[Texas Tows GMB] Text preview: {text[:80]}...")

    # ── Get access token ──────────────────────────────────────────────────────
    print("[Texas Tows GMB] Refreshing Google access token...")
    token = get_access_token(client_id, client_secret, refresh_token)

    # ── Image: try Drive first, fall back to AI ───────────────────────────────
    jpeg_bytes = get_drive_image(token, state)
    image_source = "drive"
    if jpeg_bytes is None:
        print("[Texas Tows GMB] Falling back to AI image generation...")
        jpeg_bytes = generate_image(ai_prompt, openai_key)
        image_source = "ai"

    # ── Upload to GitHub ──────────────────────────────────────────────────────
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
    filename  = f"texas-tows-{pillar}-{timestamp}.jpg"
    repo_path = f"{GITHUB_SUBDIR}/{filename}"

    print(f"[Texas Tows GMB] Uploading image ({image_source}) to GitHub: {repo_path}")
    cdn_url = upload_to_github(
        jpeg_bytes, GITHUB_REPO, repo_path, github_token,
        commit_message=f"Texas Tows GMB image ({image_source}): {filename}"
    )
    print(f"[Texas Tows GMB] CDN URL: {cdn_url}")

    # ── Post to GBP ───────────────────────────────────────────────────────────
    print("[Texas Tows GMB] Posting to Google Business Profile...")
    result = post_to_gbp(
        token=token,
        account_id=ACCOUNT_ID,
        location_id=LOCATION_ID,
        text=text,
        cta_type=CTA_TYPE,
        cta_url=None,  # CALL CTA — no URL
        media_url=cdn_url,
    )
    print(f"[Texas Tows GMB] Post created: {result.get('name', 'unknown')}")

    # ── Advance state ─────────────────────────────────────────────────────────
    state["pillar_index"] = (pillar_idx + 1) % len(PILLAR_ROTATION)
    state["area_index"]   = (area_idx + 1) % len(SERVICE_AREAS)
    state["post_counts"][pillar] = post_num + 1
    record_post(state)
    save_state(STATE_FILE, state)

    next_pillar = PILLAR_ROTATION[state["pillar_index"]]
    next_area   = SERVICE_AREAS[state["area_index"]]
    print(f"[Texas Tows GMB] Done. Next: pillar={next_pillar}, area={next_area}. State saved.")


if __name__ == "__main__":
    main()
