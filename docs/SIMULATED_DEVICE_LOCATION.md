# Device-location feed: seeded demo data

**What it is.** A stand-in for a *future* access that lets a child-safety line receive a caller's device location.
**No such access exists today.** Android's Emergency Location Service and Apple's equivalent only send a phone's
location, directly to accredited emergency services, when an emergency number is dialled. A child-safety line is not
automatically one; that needs government and carrier designation (a long-term partnership goal). Nothing in this
feature reads anyone's phone. It returns pre-seeded positions for fictional children.

The dashboard does not badge it, because the presenter says it is simulated. The data still marks every fix
`simulated: true`, and this page and the module docstring say what it is. It must not be passed off as real access.

## What is real and what is seeded

| Signal | Source | Real? |
|---|---|---|
| Phone-network area | Twilio `From*` + number prefix | Real, coarse |
| What the caller said | Gemini tool, then a small gazetteer (`app/services/geo.py`) turns it into a map point | Real input, approximate area points |
| GPS link | One-tap page the child opens (iMessage via Photon) | **Real**, needs a smartphone and data |
| Device location service | `app/services/simulated_device_location.py` | **Seeded demo data** |
| Nearest help | `geo.HELP_CENTRES` | Real organisations, area-level positions, approximate |

## The cross-check
Sources "agree" when the gap between them is no bigger than their combined uncertainty (GPS accuracy, the feed's
accuracy, or the area radius of a spoken place). If any pair disagrees, the responder sees every source with the
distances. Nothing is picked or averaged. A SIM registered in one country but located in another gets the emergency
numbers for **where the child is**.

## Running the demo
* Dashboard: open a case, pick a profile on the **Device location service** card, press **Look up** (about 1.5 s).
  It works on any case, including ones from the intake simulator.
* Automatic: a call from a seeded number gets the lookup a moment after it connects.
  Fictional numbers: `+16095550101` (Princeton), `+2348012345001` (Surulere), `…002` (Yaba), `…003` (Mile 1, Port
  Harcourt), `…004` (device says Ikeja, so a spoken Surulere will DISAGREE).
* Your own phone: `SIM_DEMO_NUMBERS="+1XXXXXXXXXX=princeton_demo"` in `backend/.env` (never commit real numbers).
* Move the Princeton fix to where you are: `SIM_PRINCETON_LATLNG="40.3466,-74.6559"`.
* `SIM_LOCATION_DELAY_S` (default 1.5) and `SIM_LOCATION_AUTO=0` to turn the automatic lookup off.

## Limits
* The gazetteer is a seed of about 28 places (Lagos, Port Harcourt, Abuja, New Jersey). Each point is an area
  centroid good to a kilometre or two. Replace it with OpenStreetMap extracts or a curated list.
* It is deliberately **not** built from Google Maps data. Google's terms let you cache coordinates for only 30 days
  and describe emergency services as a high-risk use, so a stored gazetteer should come from other sources.
* The help-centre list is a demo directory. A real one needs review. Phone numbers appear only where verified.
