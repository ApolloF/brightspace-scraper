"""
Generate synchronized slide-annotated transcripts for Hoorcollege 4:
  - Module 4.1: Besluitvorming (Slides 1 to 35)
  - Module 4.2: Leren & Bias (Slides 36 to 48)
  - Module 4.3: Conflict (Slides 49 to 63)
  - Module 4.4: Macht & Politiek (Slides 64 to 77)
"""

import os
import re
from pathlib import Path

VIDEOS_DIR = Path("downloads/videos")

# ==============================================================================
# SLIDE METADATA - MODULE 4.1: BESLUITVORMING (Slides 1 to 35)
# ==============================================================================
SLIDES_M41 = [
    {
        "slide": 1, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 4.1 - Besluitvorming",
        "summary": "Introductie van Hoorcollege 4 door Jitse Duijsters: Leren, Bias & Besluitvorming & Conflict, Macht & Politiek."
    },
    {
        "slide": 2, "time": "00:15", "seconds": 15,
        "title": "We hebben tot nu toe gezien...",
        "summary": "Organisaties zijn dynamisch en moeten zich blijven aanpassen om te overleven (life cycle, organisatievormen, waarden, diversiteit)."
    },
    {
        "slide": 3, "time": "01:10", "seconds": 70,
        "title": "We hebben tot nu toe gezien... Maar:",
        "summary": "Managers zijn niet dom. Waarom gaan er dan toch organisaties ten onder doordat ze zich onvoldoende aanpassen?"
    },
    {
        "slide": 4, "time": "01:45", "seconds": 105,
        "title": "Vandaag: Beperkte rationaliteit van managers",
        "summary": "Managers zijn mensen: niet perfect rationeel en geen toegang tot perfecte informatie. Focus op besluitvorming, leren, biases, conflict en macht."
    },
    {
        "slide": 5, "time": "02:35", "seconds": 155,
        "title": "Vooruitblik: Volgende week",
        "summary": "Koppeling naar volgende week: Hoe kunnen organisaties (toch) veranderen en innoveren?"
    },
    {
        "slide": 6, "time": "02:50", "seconds": 170,
        "title": "Agenda Hoorcollege 4",
        "summary": "De vier pijlers van college 4: 1. Besluitvorming, 2. Leren & biases, 3. Conflict, 4. Macht & Politiek."
    },
    {
        "slide": 7, "time": "03:20", "seconds": 200,
        "title": "Besluitvorming: Elementen van een definitie",
        "summary": "'Specific commitment to action' (Mintzberg et al., 1976), allocatie van schaarse middelen (onomkeerbaarheid), richtingkeuze met uitsluiting van andere."
    },
    {
        "slide": 8, "time": "04:50", "seconds": 290,
        "title": "Twee typen besluiten (Daft et al.)",
        "summary": "Programmed decisions (repetitief, gestructureerd) vs Non-programmed decisions (volledig nieuw, ongedefinieerd probleem en oplossing)."
    },
    {
        "slide": 9, "time": "07:00", "seconds": 420,
        "title": "Waarom is besluitvorming ingewikkeld?",
        "summary": "Veranderingen in omgeving leiden tot meer haast, grotere complexiteit en meer onzekerheid -> steeds meer 'non-programmed decisions'."
    },
    {
        "slide": 10, "time": "09:25", "seconds": 565,
        "title": "Typologie besluitvormingsprocessen",
        "summary": "Individueel (Rational, Bounded rationality, Intuitive) vs Organisatie (Management science, Carnegie, Incremental, Garbage can)."
    },
    {
        "slide": 11, "time": "10:20", "seconds": 620,
        "title": "Rational model (Klassiek economisch perspectief)",
        "summary": "Herbert Simon (1978): 'The rational man of economics is a maximizer'. Systematische probleemanalyse, selectie en implementatie (Management science approach)."
    },
    {
        "slide": 12, "time": "10:45", "seconds": 645,
        "title": "Rational model: De 8-stappen cyclus (Daft)",
        "summary": "Probleemidentificatie (stappen 1-4) en Probleemoplossing (stappen 5-8): monitor, define, specify, diagnose, develop, evaluate, choose, implement."
    },
    {
        "slide": 13, "time": "13:10", "seconds": 790,
        "title": "Casus: Space Shuttle Challenger - Disaster",
        "summary": "Foto van de ontploffing van de Challenger (1986). Een klassieke casus van falende besluitvorming bij NASA."
    },
    {
        "slide": 14, "time": "15:00", "seconds": 900,
        "title": "Casus Challenger: Technische opbouw & O-ringen",
        "summary": "Afbeelding shuttle met Solid Rocket Boosters en externe tank. Technische risico's van vriestemperaturen op de O-ringen."
    },
    {
        "slide": 15, "time": "16:00", "seconds": 960,
        "title": "Casus Challenger: Hoe kon dit gebeuren? (De Volkskrant)",
        "summary": "De lessen van Challenger: opbrengsten niet gemaximaliseerd en beste besluit niet gekozen ondanks beschikbare data. Waarom?"
    },
    {
        "slide": 16, "time": "16:55", "seconds": 1015,
        "title": "Wat speelt er nog meer? Rationeel vs Irrationeel",
        "summary": "Rationeel (1 beste uitkomst, gedeeld belang, objectieve kennis) vs Irrationeel (gebrek aan consensus, emotie, politiek, onzekerheid, waarden en normen)."
    },
    {
        "slide": 17, "time": "20:55", "seconds": 1255,
        "title": "Carnegie model: Wie & Wat?",
        "summary": "Carnegie School / Behavioral theory of the firm: Cyert, March & Simon ('50-'60). Realistisch model van besluitvorming in organisaties."
    },
    {
        "slide": 18, "time": "21:35", "seconds": 1295,
        "title": "Carnegie model: Vier pijlers (Gavetti et al., 2007)",
        "summary": "1. Bounded rationality & satisficing ipv maximizing; 2. Meerdere conflicterende belangen; 3. Gestandaardiseerde procedures; 4. Beslissingsstructuur & hiërarchie."
    },
    {
        "slide": 19, "time": "25:45", "seconds": 1545,
        "title": "Carnegie model: Het procesmodel",
        "summary": "Onzekerheid & Conflict -> Coalitievorming (discussie, prioriteiten) -> Search (lokaal/eenvoudig zoeken) -> Satisficing besluitvorming."
    },
    {
        "slide": 20, "time": "27:45", "seconds": 1665,
        "title": "Incremental model (Mintzberg et al., 1979)",
        "summary": "Fasering van strategische besluiten: Identification stage -> Development stage -> Selection stage. Interne en externe onderbrekingen (loops)."
    },
    {
        "slide": 21, "time": "28:50", "seconds": 1730,
        "title": "Incremental model: Link met Carnegie model",
        "summary": "Selectie via oordeel, onderhandeling of analyse. Aansluiting bij coalitievorming uit het Carnegie model."
    },
    {
        "slide": 22, "time": "29:50", "seconds": 1790,
        "title": "Incremental model: Integratie in lerende organisaties",
        "summary": "Probleemidentificatie verloopt vaak via Carnegie model (politiek/coalities); probleemoplossing via Incrementeel model (stapsgewijze trial-and-error)."
    },
    {
        "slide": 23, "time": "31:00", "seconds": 1860,
        "title": "Garbage can model: Extreem organisch",
        "summary": "Introductie van het vuilnisvatmodel (Cohen, March & Olsen): besluitvorming in georganiseerde anarchieën."
    },
    {
        "slide": 24, "time": "31:40", "seconds": 1900,
        "title": "Garbage can model: Kenmerken & Context",
        "summary": "Slecht gedefinieerde doelen, onduidelijke technologie/oorzaak-gevolg, fluïde participatie. Komt voor bij hoge onzekerheid en snelle verandering."
    },
    {
        "slide": 25, "time": "32:15", "seconds": 1935,
        "title": "Garbage can model: Vier onafhankelijke stromen",
        "summary": "Problemen, Oplossingen, Participanten en Keuzemomenten ontmoeten elkaar toevallig. Oplossingen op zoek naar een probleem."
    },
    {
        "slide": 26, "time": "33:15", "seconds": 1995,
        "title": "Intuïtie in besluitvorming",
        "summary": "Gebaseerd op diepe ervaring, patroonherkenning en oordeel. Niet irrationeel, maar snelle holistische synthese op individueel niveau."
    },
    {
        "slide": 27, "time": "34:30", "seconds": 2070,
        "title": "Typologie besluitvormingsprocessen (Herhaling)",
        "summary": "Samenvattend overzicht van alle 7 besluitvormingsmodellen op individueel en organisatieniveau."
    },
    {
        "slide": 28, "time": "34:55", "seconds": 2095,
        "title": "Contingentiemodel voor besluitvorming (Matrix)",
        "summary": "2x2 Matrix: Problem Consensus (Certain vs Uncertain) x Solution Knowledge (Certain vs Uncertain)."
    },
    {
        "slide": 29, "time": "35:15", "seconds": 2115,
        "title": "Contingentie Vak 1: Certain Consensus & Certain Knowledge",
        "summary": "Individueel: Rational approach / computation. Organisatie: Management Science."
    },
    {
        "slide": 30, "time": "35:45", "seconds": 2145,
        "title": "Contingentie Vak 2: Uncertain Consensus & Certain Knowledge",
        "summary": "Individueel: Bargaining / coalition formation. Organisatie: Carnegie model."
    },
    {
        "slide": 31, "time": "36:15", "seconds": 2175,
        "title": "Contingentie Vak 3: Certain Consensus & Uncertain Knowledge",
        "summary": "Individueel: Judgment / trial and error. Organisatie: Incremental Decision model."
    },
    {
        "slide": 32, "time": "36:45", "seconds": 2205,
        "title": "Contingentie Vak 4: Uncertain Consensus & Uncertain Knowledge",
        "summary": "Individueel: Bargaining & judgment, inspiration & imitation. Organisatie: Garbage Can model."
    },
    {
        "slide": 33, "time": "37:35", "seconds": 2255,
        "title": "Betere beslissingen? (The Devil's Advocate)",
        "summary": "Cartoon GAP: Your Perception vs Reality. De noodzaak van tegenspraak en kritische toetsing om blinde vlekken te vermijden."
    },
    {
        "slide": 34, "time": "37:45", "seconds": 2265,
        "title": "Handvatten voor betere beslissingen",
        "summary": "Selectie passend procestype, Game theory, Scenario planning, Devil's advocate, Diversiteit en Organisatie-leren. Randvoorwaarden: cultuur en macht."
    },
    {
        "slide": 35, "time": "40:50", "seconds": 2450,
        "title": "Afsluiting Module 4.1",
        "summary": "Afronding van Module 4.1 en brug naar Module 4.2 (Leren & Bias)."
    }
]

# ==============================================================================
# SLIDE METADATA - MODULE 4.2: LEREN & BIAS (Slides 36 to 48)
# ==============================================================================
SLIDES_M42 = [
    {
        "slide": 36, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 4.2 - Leren & Bias",
        "summary": "Introductie van Module 4.2: Hoe organisaties leren en hoe cognitieve biases dit proces belemmeren."
    },
    {
        "slide": 37, "time": "00:30", "seconds": 30,
        "title": "Informatie, Kennis & Leren (Cartoon Gapingvoid)",
        "summary": "Visualisatie van de keten: losse datapunten -> geordende informatie -> onderling verbonden kennisnetwerk."
    },
    {
        "slide": 38, "time": "00:40", "seconds": 40,
        "title": "Definities: Data, Informatie, Kennis & Leren",
        "summary": "Data ('10') -> Informatie ('het is 10 graden') -> Kennis ('dan moet je een jas aan') -> Leren ('moet ik ook een jas aan als...')."
    },
    {
        "slide": 39, "time": "01:40", "seconds": 100,
        "title": "Leren op verschillende niveaus (Senge, 1990)",
        "summary": "Vier niveaus van organisatieleren: Individu (personal mastery & mental models) -> Team (dialogue) -> Organisatie (shared vision) -> Inter-organisatorisch."
    },
    {
        "slide": 40, "time": "03:05", "seconds": 185,
        "title": "Typen organisatieleren: Exploration vs Exploitation",
        "summary": "Exploration (experimenteren met nieuwe routines) vs Exploitation (verfijnen van bestaande routines). Ambidexterity ('tweehandigheid')."
    },
    {
        "slide": 41, "time": "05:00", "seconds": 300,
        "title": "Leren & Innovatie (Anderson & Tushman, 1990)",
        "summary": "Quantum change (radicaal, revolutionair, blue ocean) vs Incremental change (gradueel, evolutionair, red ocean, verdieping)."
    },
    {
        "slide": 42, "time": "05:55", "seconds": 355,
        "title": "Waarom leren organisaties moeilijk? (Barrières)",
        "summary": "Inzichten uit het verleden hinderen nieuw leren: inertie, biases, rigiditeit/bureaucratie en exploitatie-overheersing."
    },
    {
        "slide": 43, "time": "07:10", "seconds": 430,
        "title": "Inertia (Verstarring): Interne oorzaken",
        "summary": "Sunk costs (gedane investeringen), gebrekkige informatie, gevestigde machtsbelangen, en collectieve mentale modellen/wereldbeelden."
    },
    {
        "slide": 44, "time": "09:30", "seconds": 570,
        "title": "Inertia (Verstarring): Externe oorzaken",
        "summary": "Onoverzichtelijke turbulente omgeving, wettelijke barrières, formalisering (kwaliteitssystemen) en drang naar legitimiteit."
    },
    {
        "slide": 45, "time": "11:05", "seconds": 665,
        "title": "Cognitieve biases in organisaties (Jones, 2013)",
        "summary": "Vier belangrijke biases: Illusie van controle, Cognitieve dissonantie, Ego-defensief gedrag en Escalatie van commitment."
    },
    {
        "slide": 46, "time": "14:20", "seconds": 860,
        "title": "Organizational decline & besluitvorming: De spanning",
        "summary": "Inertia (verstarring) botst met de eisen van de hedendaagse turbulente omgeving die snellere en flexibelere besluitvorming vereist."
    },
    {
        "slide": 47, "time": "15:10", "seconds": 910,
        "title": "De 5 fasen van neergang (Weitzel & Jonsson, 1989)",
        "summary": "Stage 1 Blinded -> Stage 2 Inaction -> Stage 3 Faulty Action -> Stage 4 Crisis -> Stage 5 Dissolution. Het gevaar van 'muddling through'."
    },
    {
        "slide": 48, "time": "15:45", "seconds": 945,
        "title": "Afsluiting Module 4.2",
        "summary": "Samenvatting van leren & bias en introductie naar Module 4.3 (Conflict)."
    }
]

# ==============================================================================
# SLIDE METADATA - MODULE 4.3: CONFLICT (Slides 49 to 63)
# ==============================================================================
SLIDES_M43 = [
    {
        "slide": 49, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 4.3 - Conflict",
        "summary": "Introductie van Module 4.3: Intergroepsconflict binnen organisaties."
    },
    {
        "slide": 50, "time": "00:35", "seconds": 35,
        "title": "Intergroup conflict: Definitie (Daft et al.)",
        "summary": "Gedrag dat ontstaat wanneer groepen zich identificeren en ervaren dat andere groepen hun doelen of verwachtingen blokkeren."
    },
    {
        "slide": 51, "time": "01:10", "seconds": 70,
        "title": "Twee organisatiebeelden: Arena vs Sociaal Systeem",
        "summary": "Arena (Politiek model: strijd, conflicterende belangen, hordelopers) vs Sociaal systeem (Rationeel model: gedeelde doelen, harmonie, roeiers)."
    },
    {
        "slide": 52, "time": "02:15", "seconds": 135,
        "title": "Bronnen van conflict (Jones, Hs 7)",
        "summary": "1. Goal incompatibility, 2. Differentiation (cognitief & emotioneel), 3. Task interdependence, 4. Limited resources."
    },
    {
        "slide": 53, "time": "04:30", "seconds": 270,
        "title": "Het conflict-optimum (Omgekeerde U-curve)",
        "summary": "Te weinig conflict leidt tot apathie en inertie; te veel conflict tot chaos; een optimaal niveau stimuleert innovatie en kritisch denken."
    },
    {
        "slide": 54, "time": "06:25", "seconds": 385,
        "title": "Rol van structuur & cultuur op conflict (Pfeffer, 1981)",
        "summary": "Arbeidsverdeling en differentiatie leiden tot taakafhankelijkheid, subdoelen en sub-unit oriëntatie -> competitie en conflict."
    },
    {
        "slide": 55, "time": "08:00", "seconds": 480,
        "title": "Vraag: Waar passen Macht en Politiek?",
        "summary": "Koppeling van het structurele conflictmodel aan machtsverhoudingen en organisatiepolitiek."
    },
    {
        "slide": 56, "time": "09:15", "seconds": 555,
        "title": "Volledig model: Van Conflict naar Politiek gedrag",
        "summary": "Pfeffer (1981): Conflict + Schaarste + Machtsbalans activeert politiek gedrag tussen afdelingen."
    },
    {
        "slide": 57, "time": "10:30", "seconds": 630,
        "title": "Conflictmanagement: Interventies",
        "summary": "Wegnemen van tegenstellingen via structuurverandering (integratiemechanismen, platte hiërarchie) of cultuurverandering (participatie, rotatie, vervanging leiders)."
    },
    {
        "slide": 58, "time": "12:30", "seconds": 750,
        "title": "Conflicthanteringsstijlen: Assenkruis (Thomas & Kilmann, 1974)",
        "summary": "Dimensies: Assertiveness (eigen belang nastreven) vs Cooperativeness (belang van de ander behartigen)."
    },
    {
        "slide": 59, "time": "12:50", "seconds": 770,
        "title": "Vijf stijlen van conflicthantering",
        "summary": "Competition (win-lose), Collaboration (win-win), Compromise (middelweg), Avoidance (ontwijken), Accommodation (toegeven)."
    },
    {
        "slide": 60, "time": "13:40", "seconds": 820,
        "title": "Dynamiek tussen conflicthanteringsstijlen",
        "summary": "Hoe stijlen verschuiven afhankelijk van urgentie, belangen en machtsverhoudingen."
    },
    {
        "slide": 61, "time": "14:25", "seconds": 865,
        "title": "Avoidance in de praktijk: Arbeidsconflicten & Verzuim",
        "summary": "Conflict is geen ziekte, maar 70.000-100.000 ziekmeldingen per jaar ontstaan door onopgeloste conflicten (wegblijven als vlucht)."
    },
    {
        "slide": 62, "time": "15:05", "seconds": 905,
        "title": "Belangrijkste punten: Conflict samengevat",
        "summary": "Kernboodschappen: noodzaak vs risico, bronnen, invloed van structuur en hanteringsstrategieën."
    },
    {
        "slide": 63, "time": "15:55", "seconds": 955,
        "title": "Afsluiting Module 4.3",
        "summary": "Brug naar Module 4.4 (Macht & Politiek)."
    }
]

# ==============================================================================
# SLIDE METADATA - MODULE 4.4: MACHT & POLITIEK (Slides 64 to 77)
# ==============================================================================
SLIDES_M44 = [
    {
        "slide": 64, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 4.4 - Macht & Politiek",
        "summary": "Introductie van Module 4.4: De rol van macht en politieke processen in organisaties."
    },
    {
        "slide": 65, "time": "00:35", "seconds": 35,
        "title": "Macht: Definitie & Karakteristieken",
        "summary": "Het vermogen van A om gedrag van B te sturen. Macht als sociaal fenomeen, relationeel en relatief ('electrical power' om dingen gedaan te krijgen)."
    },
    {
        "slide": 66, "time": "01:40", "seconds": 100,
        "title": "Macht, Afhankelijkheid & Beïnvloeding",
        "summary": "Cartoon kat en vis: Macht = potentieel vermogen; Afhankelijkheid = B heeft nodig wat A bezit; Beïnvloeden = macht in actie."
    },
    {
        "slide": 67, "time": "02:45", "seconds": 165,
        "title": "Macht in relatie tot andere concepten",
        "summary": "Koppeling aan ethiek, stakeholders, strategische besluitvorming (Carnegie-model) en organisatiepolitiek."
    },
    {
        "slide": 68, "time": "04:00", "seconds": 240,
        "title": "Macht in de organisatiepiramide (Robbins & Barnwell)",
        "summary": "Invloed van contingenties per organisatieniveau: strategie en omgeving bij de top, technologie bij de basis, en macht door de hele organisatie."
    },
    {
        "slide": 69, "time": "04:40", "seconds": 280,
        "title": "Macht, Structuur & Autoriteit",
        "summary": "Authority: legitieme macht verankerd in de formele en culturele basis van de organisatie. Erkend gezag en formele bevoegdheid."
    },
    {
        "slide": 70, "time": "06:30", "seconds": 390,
        "title": "Machtsbronnen: Individueel vs Organisatieniveau",
        "summary": "Individueel (French & Raven: legitiem, beloning, dwang, expertise, referentie). Organisatie: verticaal (positie, middelen, besluitvorming) vs horizontaal (strategic contingencies, onvervangbaarheid)."
    },
    {
        "slide": 71, "time": "11:05", "seconds": 665,
        "title": "Individuele machtsbronnen & Effect op Houding",
        "summary": "Legitiem & Beloning leiden tot naleving (compliance); Dwingend leidt tot weerstand (resistance); Referentie & Expertise leiden tot toewijding (commitment)."
    },
    {
        "slide": 72, "time": "11:50", "seconds": 710,
        "title": "Organisatiepolitiek & De casus OpenAI",
        "summary": "Daft definitie: inzet van macht om besluiten te sturen richting gewenste uitkomsten. Stakeholder-map van OpenAI (Sam Altman, board, Microsoft, medewerkers)."
    },
    {
        "slide": 73, "time": "13:35", "seconds": 815,
        "title": "Oorzaken van organisatiepolitiek",
        "summary": "Onduidelijke of conflicterende doelen, schaarste aan middelen, en een organisatiecultuur gekenmerkt door wantrouwen of traditie."
    },
    {
        "slide": 74, "time": "14:20", "seconds": 860,
        "title": "Vormen van politiek gedrag",
        "summary": "Magneet cartoon: Verplichtingen creëren, Netwerken opbouwen, Informatie controleren, Coalities vormen."
    },
    {
        "slide": 75, "time": "15:40", "seconds": 940,
        "title": "Politieke tactieken (Daft et al.)",
        "summary": "1. Vergroten machtsbasis (onzekerheid reduceren, schaarste bieden); 2. Inzetten macht (coalities, loyale mensen); 3. Samenwerking bevorderen (superordinate goals, rotatie)."
    },
    {
        "slide": 76, "time": "17:25", "seconds": 1045,
        "title": "Vooruitblik: Volgende week (Verandering & Innovatie)",
        "summary": "Afsluitende synthese: hoe macht en politiek de overgang vormen naar organisatieverandering en innovatie."
    },
    {
        "slide": 77, "time": "21:30", "seconds": 1290,
        "title": "Afsluiting Hoorcollege 4: OpenAI casus & Synthese",
        "summary": "Einde van Hoorcollege 4. Jitse Duijsters sluit af met reflectie op de OpenAI bestuursstrijd en praktische tips voor de werkcolleges."
    }
]


def srt_time_to_seconds(ts_str):
    parts = ts_str.strip().replace(',', '.').split(':')
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


def generate_annotated_transcript(srt_path, slides_meta, output_path, module_title):
    content = open(srt_path, encoding="utf-8").read()
    blocks = re.findall(r'(\d+)\n([\d:,]+) --> ([\d:,]+)\n(.*?)(?=\n\n|\Z)', content, re.DOTALL)
    
    current_slide_idx = 0
    lines = []
    lines.append(f"# {module_title}\n")
    lines.append(f"> **Totaal aantal slides:** {len(slides_meta)}\n")
    lines.append("---\n")

    for num, start_ts, end_ts, text in blocks:
        start_sec = srt_time_to_seconds(start_ts)
        clean_text = " ".join(text.strip().split())

        # Check if we transitioned to one or more subsequent slides
        while (current_slide_idx < len(slides_meta) - 1 and 
               start_sec >= slides_meta[current_slide_idx + 1]["seconds"]):
            current_slide_idx += 1
            cur = slides_meta[current_slide_idx]
            lines.append(f"\n\n## 📊 Slide {cur['slide']}: {cur['title']}")
            lines.append(f"**Tijdstip in video:** `{cur['time']}` | **Kerninhoud:** *{cur['summary']}*\n")

        # First slide header at start
        if num == "1" and current_slide_idx == 0:
            cur = slides_meta[0]
            lines.append(f"## 📊 Slide {cur['slide']}: {cur['title']}")
            lines.append(f"**Tijdstip in video:** `{cur['time']}` | **Kerninhoud:** *{cur['summary']}*\n")

        lines.append(f"**[{start_ts[:8]}]** {clean_text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated: {output_path.name}")


def main():
    s1 = VIDEOS_DIR / "5970124_M&OT Hoorcollege 4 - Module 4.1 (Besluitvorming) - Management- en Organisatietheorie [Semester 1a]_transcript_nl.srt"
    o1 = VIDEOS_DIR / "Hoorcollege_4_Module_4.1_Slide_Transcript.md"
    generate_annotated_transcript(s1, SLIDES_M41, o1, "Hoorcollege 4 - Module 4.1: Besluitvorming")

    s2 = VIDEOS_DIR / "5970125_M&OT Hoorcollege 4 - Module 4.2 (Leren & Bias) - Management- en Organisatietheorie [Semester 1a]_transcript_nl.srt"
    o2 = VIDEOS_DIR / "Hoorcollege_4_Module_4.2_Slide_Transcript.md"
    generate_annotated_transcript(s2, SLIDES_M42, o2, "Hoorcollege 4 - Module 4.2: Leren & Bias")

    s3 = VIDEOS_DIR / "5970126_M&OT Hoorcollege 4 - Module 4.3 (Conflict) - Management- en Organisatietheorie [Semester 1a]_transcript_nl.srt"
    o3 = VIDEOS_DIR / "Hoorcollege_4_Module_4.3_Slide_Transcript.md"
    generate_annotated_transcript(s3, SLIDES_M43, o3, "Hoorcollege 4 - Module 4.3: Conflict")

    s4 = VIDEOS_DIR / "5970127_M&OT Hoorcollege 4 - Module 4.4 (Macht & Politiek) - Management- en Organisatietheorie [Semester 1a]_transcript_nl.srt"
    o4 = VIDEOS_DIR / "Hoorcollege_4_Module_4.4_Slide_Transcript.md"
    generate_annotated_transcript(s4, SLIDES_M44, o4, "Hoorcollege 4 - Module 4.4: Macht & Politiek")

    master = VIDEOS_DIR / "Hoorcollege_4_Complete_Slide_Annotated_Transcript.md"
    with open(master, "w", encoding="utf-8") as f_out:
        f_out.write("# Management & Organisatietheorie - Hoorcollege 4\n")
        f_out.write("## Volledige Transcriptie met Gekoppelde Slides (Jitse Duijsters)\n")
        f_out.write("### Thema's: Besluitvorming, Leren & Bias, Conflict, Macht & Politiek (Slides 1 - 77)\n\n")
        f_out.write(open(o1, encoding="utf-8").read())
        f_out.write("\n\n" + "=" * 80 + "\n\n")
        f_out.write(open(o2, encoding="utf-8").read())
        f_out.write("\n\n" + "=" * 80 + "\n\n")
        f_out.write(open(o3, encoding="utf-8").read())
        f_out.write("\n\n" + "=" * 80 + "\n\n")
        f_out.write(open(o4, encoding="utf-8").read())
    print(f"Generated master: {master.name}")


if __name__ == "__main__":
    main()
