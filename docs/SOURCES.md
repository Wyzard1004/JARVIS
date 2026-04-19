# Sources and Rationale

This document captures the public-source research that should shape how JARVIS talks, parses, and presents itself to judges from military and national-security backgrounds.

The intent is not to turn the repo into a doctrinal system. The intent is to make the terminology, operator flow, and command vocabulary sound grounded, disciplined, and credible.

## Core Position

The strongest message from the research is:

- operators should speak short, named control measures
- exact coordinates should usually live in the machine layer
- destructive actions should require explicit confirmation
- the UI and parser should use radio language that sounds familiar to military operators

That maps well onto the current codebase, which already has:

- a constrained command schema in [base_station/core/ai_bridge.py](</C:/Users/richa/OneDrive - PennO365/JARVIS/JARVIS/base_station/core/ai_bridge.py:1>)
- a direct operator-to-parser path through `/api/transcribe-command` in [base_station/api/main.py](</C:/Users/richa/OneDrive - PennO365/JARVIS/JARVIS/base_station/api/main.py:1>)
- a button-driven voice flow through [base_station/headless/serial_ptt_listener.py](</C:/Users/richa/OneDrive - PennO365/JARVIS/JARVIS/base_station/headless/serial_ptt_listener.py:1>)

## What The Sources Support

### 1. Named sectors and control measures are better spoken than raw coordinates

Recommended speaking style:

- `Sector Bravo 3`
- `Phase Line Blue`
- `TRP 234`

Recommended machine-layer location support:

- named sectors and sub-sectors for voice
- MGRS or lat/lon internally for precision

Why:

- long alphanumeric coordinate strings are fragile under STT
- public doctrine consistently uses named control measures for operator communication
- named areas are far easier to brief, display, and confirm back to a human

Primary sources:

- [ACP 125(G) Radiotelephone Procedures](https://orwg.cap.gov/media/cms/ACP125GRadioTelephoneProceduresNOV2_EFFE1A51BA783.pdf)
- [ATP 2-01.3 Intelligence Preparation of the Battlefield](https://home.army.mil/wood/application/files/8915/5751/8365/ATP_2-01.3_Intelligence_Preparation_of_the_Battlefield.pdf)
- [ATP 3-21.8 Infantry Platoon and Squad](https://infantrydrills.com/manuals/fm-atp-3-21-8-infantry-rifle-platoon-squad-2024/offense/conduct-offense/)
- [NGA MGRS Technical Document](https://mgrs-data.org/data/documents/nga_mgrs_doc.pdf)
- [NATO IST-031 Speech Processing in Battlefield Environments](https://stephanepigeon.com/Docs/TR-IST-031-ALL.pdf)

### 2. Radio-style command grammar matters

Recommended pattern:

```text
[CALLSIGN] [ACTION] [LOCATION] [QUALIFIER?] OVER
```

Examples:

- `JARVIS, move to Sector Bravo 3, over.`
- `JARVIS, hold at Phase Line Blue, over.`
- `JARVIS, all units, abort, out.`

Why:

- it sounds familiar to military judges
- it gives the parser a stable beginning, middle, and end
- terminal prowords like `OVER` and `OUT` help reduce partial-utterance ambiguity

Primary sources:

- [ACP 125(G) Radiotelephone Procedures](https://orwg.cap.gov/media/cms/ACP125GRadioTelephoneProceduresNOV2_EFFE1A51BA783.pdf)
- [ATP 6-02.53 Techniques for Tactical Radio Operations](https://rdl.train.army.mil/catalog-ws/view/100.ATSC/0C45D378-25E0-438E-8881-749EF51DE080-1452191121290/atp6_02x53.pdf)
- [MCRP 3-25B Multi-Service Brevity Codes](https://www.militarynewbie.com/wp-content/uploads/2013/11/US-Marine-Corps-Multi-Service-Brevity-Codes-MCRP-3-25B.pdf)

### 3. Human approval should gate attack commands

Recommended behavior:

- recon / movement / hold can execute directly
- attack / engage should stage first
- operator confirms with `EXECUTE`
- system can be canceled with `ABORT` or `DISREGARD`

Why:

- it is a much more credible control loop in front of defense-oriented judges
- it mirrors public doctrine around human judgment in use-of-force decisions
- it gives the demo a clean dramatic beat: recommendation, read-back, execute

Primary sources:

- [DoD Directive 3000.09](https://www.esd.whs.mil/portals/54/documents/dd/issuances/dodd/300009p.pdf)
- [JP 3-09.3 Close Air Support](https://www.bits.de/NRANEU/others/jp-doctrine/jp3_09_3(09c).pdf)
- [JP 3-60 Joint Targeting](https://jfsc.ndu.edu/Portals/72/Documents/JC2IOS/Additional_Reading/1F4_jp3-60.pdf)

### 4. Swarm networking parameters should be defensible

Recommended baseline direction:

- fanout around 3
- max hops around 5
- short leases and explicit retries
- simple priority tiers
- link quality should eventually replace purely static range

Why:

- judges will ask why those numbers were chosen
- public MANET, FANET, and distributed-systems literature gives you a defendable answer

Primary sources:

- [Demers et al. — Epidemic Algorithms](https://dl.acm.org/doi/10.1145/41840.41841)
- [Leitao et al. — HyParView](https://asc.di.fct.unl.pt/~jleitao/pdf/dsn07-leitao.pdf)
- [Bekmezci et al. — FANET Survey](https://dl.acm.org/doi/10.1016/j.adhoc.2012.12.004)
- [RFC 3561 AODV](https://datatracker.ietf.org/doc/html/rfc3561)
- [RFC 3626 OLSR](https://datatracker.ietf.org/doc/html/rfc3626)
- [RFC 6298 TCP RTO](https://datatracker.ietf.org/doc/html/rfc6298)
- [RFC 2474 DSCP](https://datatracker.ietf.org/doc/html/rfc2474)
- [Gray and Cheriton — Leases](https://www.semanticscholar.org/paper/Leases:-an-efficient-fault-tolerant-mechanism-for-Gray-Cheriton/8965057405c1de742346eba16f20eaca2612f576)

## Recommended Vocabulary To Adopt

These are the highest-value terms to use in code, UI, demos, and judging conversations:

- `callsign`
- `sector`
- `phase line`
- `TRP`
- `SITREP`
- `SPOTREP`
- `hold`
- `loiter`
- `mark`
- `track`
- `engage`
- `execute`
- `abort`
- `standby`
- `roger`
- `wilco`

These make the system sound like command-and-control software rather than a generic voice assistant.

## ARMA / Milsim Inspiration

Simulation sources are useful for phrasing and UI tone, but they should never be presented as doctrine.

Good inspiration areas:

- callsign flavor
- color/state conventions
- command-menu structure
- read-back / execute cadence

Suggested label in presentations:

`ARMA-style interaction polish, grounded in public doctrine and radio procedures`

Simulation references:

- [Task Force Reaper milsim SOP](https://taskforcereaper.weebly.com/communication-procedures.html)
- [ShackTac Callsign wiki](https://shacktac.fandom.com/wiki/Callsign)
- [Armed Assault Wiki — UAV Terminal](https://armedassault.fandom.com/wiki/UAV_Terminal)
- [ACE3 Interaction Menu Framework](https://ace3.acemod.org/wiki/framework/interactionmenu-framework)

## Use This In Judge Q&A

If asked why the language looks the way it does, the strongest short answer is:

> We moved toward short radio-style commands, named control measures, and explicit execute gating because that is more resilient for speech recognition, more credible for DDIL command and control, and more aligned with public doctrine than reading raw coordinates into a microphone.
