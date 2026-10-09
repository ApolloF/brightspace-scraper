"""
Merge slides and transcripts for Hoorcollege 3:
- Module 3.1: Slides 1 to 15 (Topic 5940698)
- Module 3.2: Slides 16 to 43 (Topic 5940699)
"""

import os
import re
from pathlib import Path

VIDEOS_DIR = Path("downloads/videos")

# Module 3.1 slide mapping with exact transition timestamps (in seconds)
SLIDES_M31 = [
    {
        "slide": 1,
        "time": "00:00",
        "seconds": 0,
        "title": "Titelpagina: Module 3.1 - Organisatiecultuur en -waarden",
        "summary": "Introductie van Hoorcollege 3 door Jitse Duijsters: van harde structuurelementen naar de zachtere kant (cultuur, waarden, diversiteit en inclusie)."
    },
    {
        "slide": 2,
        "time": "00:35",
        "seconds": 35,
        "title": "Organisatiecultuur (Schein, 1985)",
        "summary": "Definitie Schein (1985): gedeelde assumpties geleerd bij externe adaptatie en interne integratie. Cultuur is aangeleerd door verandering én object van verandering. Prent: 'Moeder in het gezin en niet in de fabriek!'."
    },
    {
        "slide": 3,
        "time": "01:58",
        "seconds": 118,
        "title": "Wat zijn dan organisatiewaarden? (Bourne & Jenkins, 2013)",
        "summary": "Definitie organisatiewaarden: blijvende denkbeelden die gedrag sturen en evalueren. IJsberg-model (Artefacten vs Waarden vs Basisassumpties). Conformiteit aan waarden als alternatief voor bureaucratische controle."
    },
    {
        "slide": 4,
        "time": "04:02",
        "seconds": 242,
        "title": "Dynamische organisatiewaarden (Daft vs Bourne & Jenkins)",
        "summary": "Twee visies: traditioneel (Daft: eenduidig, vormvast & stabiel) vs dynamisch (Bourne & Jenkins: meervormig en dynamisch). Fokke & Sukke cartoon: 'En de cultuuromslag? Die is donderdag de 17e om half vier.'."
    },
    {
        "slide": 5,
        "time": "04:42",
        "seconds": 282,
        "title": "Vier typen organisatiewaarden (Bourne & Jenkins, 2013)",
        "summary": "2x2 Matrix: Levels of analysis (Collective vs Individual) x Temporal orientation (Embedded/Present vs Intended/Future). Onderscheid tussen: Attributed, Espoused, Shared en Aspirational values."
    },
    {
        "slide": 6,
        "time": "06:38",
        "seconds": 398,
        "title": "Casus Tony's Chocolonely: Introductie",
        "summary": "Foto van Tony's Chocolonely chocoladereep. Toepassing van het Bourne & Jenkins raamwerk op een waardengedreven organisatie."
    },
    {
        "slide": 7,
        "time": "08:26",
        "seconds": 506,
        "title": "Casus Tony's: Ben & Jerry's samenwerking & Missie",
        "summary": "'Chocolate Love A-Fair', 100% slaafvrij, strijd tegen illegale kinderarbeid. Espoused en aspirational values van Tony's Chocolonely."
    },
    {
        "slide": 8,
        "time": "09:21",
        "seconds": 561,
        "title": "Casus Tony's: Team Tony's (Mugshots medewerkers)",
        "summary": "Overzicht van medewerkers ('Master Control', 'Lucky Penny', etc.). Shared en attributed values binnen het team."
    },
    {
        "slide": 9,
        "time": "10:56",
        "seconds": 656,
        "title": "Waardenspanningen & Gaps (Bourne & Jenkins, 2013)",
        "summary": "Vier situaties: 1. Overlapping values, 2. Expectation gap (Present vs Future), 3. Dislocation gap (Collective vs Individual), 4. Leadership gap (Espoused vs de rest). Normative fragmentation."
    },
    {
        "slide": 10,
        "time": "13:46",
        "seconds": 826,
        "title": "Casus Ajax: Cultuurmanager aangesteld (Het Parool)",
        "summary": "Krantenartikel over de aanstelling van een programmamanager Cultuur bij Ajax na de affaire rond Marc Overmars."
    },
    {
        "slide": 11,
        "time": "14:32",
        "seconds": 872,
        "title": "Vraagstuk: Waar bevindt Ajax zich in het model?",
        "summary": "Analyse van Ajax aan de hand van de vier gaps. Bespreking van de spanning tussen heden/toekomst en leiderschap."
    },
    {
        "slide": 12,
        "time": "16:08",
        "seconds": 968,
        "title": "Casus RUG: Yantai campus China afgelast (De Volkskrant)",
        "summary": "Krantenartikel over het afzien van de RUG-campus in Yantai (China) wegens onvoldoende draagvlak."
    },
    {
        "slide": 13,
        "time": "17:26",
        "seconds": 1046,
        "title": "Vraagstuk: Waar bevindt de RUG zich in het model?",
        "summary": "Analyse van de RUG: Dislocation gap / Leadership gap tussen het College van Bestuur (top-down) en de universitaire gemeenschap (faculteiten/studenten)."
    },
    {
        "slide": 14,
        "time": "18:31",
        "seconds": 1111,
        "title": "Brug naar Diversiteit & Inclusie",
        "summary": "Cultuur en waarden als fundament voor diversiteit en inclusief management. Introductie naar Module 3.2."
    },
    {
        "slide": 15,
        "time": "18:48",
        "seconds": 1128,
        "title": "Afsluiting Module 3.1",
        "summary": "Einde van module 3.1."
    }
]

# Module 3.2 slide mapping with exact transition timestamps (in seconds)
SLIDES_M32 = [
    {
        "slide": 16,
        "time": "00:00",
        "seconds": 0,
        "title": "Titelpagina: Module 3.2 - Diversiteit en Inclusie",
        "summary": "Introductie van module 3.2 door Jitse Duijsters: diversiteit en inclusie binnen organisaties."
    },
    {
        "slide": 17,
        "time": "00:23",
        "seconds": 23,
        "title": "Wie wil een manager worden? (Traditioneel rolmodel)",
        "summary": "Afbeelding van mannelijke manager met portretten van uitsluitend oudere blanke mannelijke bestuurders aan de muur. Impact van rolmodellen op aspiraties."
    },
    {
        "slide": 18,
        "time": "01:25",
        "seconds": 85,
        "title": "Wie wil een manager worden? (Diverser rolmodel)",
        "summary": "Portretten aangevuld met diverse leiders (Satya Nadella, vrouwelijke CEO's). Hoe representatie het beeld van een topmanager verandert."
    },
    {
        "slide": 19,
        "time": "02:01",
        "seconds": 121,
        "title": "Vrouwen aan de top: Hoogleraren universiteiten (Rathenau, 2021)",
        "summary": "Grafiek aandeel vrouwelijke hoogleraren: gemiddeld 26,7%, maar in economie slechts 16%."
    },
    {
        "slide": 20,
        "time": "02:27",
        "seconds": 147,
        "title": "Vrouwen aan de top: Amerikaanse beroepsbevolking (Catalyst)",
        "summary": "Piramide: 46,8% van totale workforce is vrouw, 40,5% management, 29,2% chief executives, 8,2% Fortune 500 CEO's."
    },
    {
        "slide": 21,
        "time": "03:26",
        "seconds": 206,
        "title": "Vrouwen aan de top: Fortune 500 CEO's (Investing.com)",
        "summary": "In 2023 is 10,2% van de Fortune 500 CEO's vrouw (52 vrouwelijke CEO's)."
    },
    {
        "slide": 22,
        "time": "03:32",
        "seconds": 212,
        "title": "Vrouwen aan de top: Extrapolatie naar 2045...",
        "summary": "Rode opdruk '2045...': het trage tempo van verandering richting gendergelijkheid aan de top."
    },
    {
        "slide": 23,
        "time": "04:48",
        "seconds": 288,
        "title": "Vraag: Om welke vormen van diversiteit gaat het hier?",
        "summary": "Vraagstelling over verschillende dimensies van diversiteit."
    },
    {
        "slide": 24,
        "time": "05:00",
        "seconds": 300,
        "title": "Vormen van diversiteit (Surface vs Deep level)",
        "summary": "Demografisch: leeftijd, etniciteit, gender. Functioneel/ervaring: educatie, functie, industriële, organisatorische en bestuurlijke ervaring."
    },
    {
        "slide": 25,
        "time": "06:21",
        "seconds": 381,
        "title": "Vraag: Waar wringt de schoen?",
        "summary": "Waarom is het realiseren en managen van diversiteit zo uitdagend?"
    },
    {
        "slide": 26,
        "time": "06:36",
        "seconds": 396,
        "title": "Problemen met diversiteit: Homophily ('Om het te worden')",
        "summary": "McPherson et al. (2001): 'Similarity breeds connection'. Homogene persoonlijke netwerken belemmeren toetreding van diverse groepen."
    },
    {
        "slide": 27,
        "time": "07:31",
        "seconds": 451,
        "title": "Problemen met diversiteit: Conflict & Paradox ('Om het te zijn')",
        "summary": "Bassett-Jones (2005): diversiteit kan leiden tot misverstanden, wantrouwen en conflict. De paradox tussen innovatie en harmonie."
    },
    {
        "slide": 28,
        "time": "08:42",
        "seconds": 522,
        "title": "Diversiteit ≠ Inclusie (Deloitte Insights)",
        "summary": "Diversiteit bereik je via selectie & promotie; inclusie vraagt om dagelijks management. Definitie inclusie (belongingness & uniqueness). Figuur equality vs equity vs barrières wegnemen."
    },
    {
        "slide": 29,
        "time": "09:41",
        "seconds": 581,
        "title": "Vraag: Is gebrek aan diversiteit nou zo erg?",
        "summary": "Argumenten voor diversiteit binnen organisaties."
    },
    {
        "slide": 30,
        "time": "09:48",
        "seconds": 588,
        "title": "Argument 1: Onethisch",
        "summary": "Ethische rechtvaardigheid en gelijke kansen."
    },
    {
        "slide": 31,
        "time": "10:02",
        "seconds": 602,
        "title": "Argument 2: Minder innovatie",
        "summary": "Homogene groepen genereren minder gevarieerde ideeën en perspectieven."
    },
    {
        "slide": 32,
        "time": "10:22",
        "seconds": 622,
        "title": "TMT Diversiteit & Innovatie (Talke, Salomo, & Rost, 2010)",
        "summary": "Model: Top Management Team diversiteit stimuleert specificatie van innovatievelden -> innovatiever productportfolio -> hogere ondernemingswaarde (Tobin's q)."
    },
    {
        "slide": 33,
        "time": "10:57",
        "seconds": 657,
        "title": "Vrouwen in topmanagement & Prestaties (Dezsö & Ross, 2012)",
        "summary": "Vrouwelijke representatie in topmanagement verbetert prestaties, mits de bedrijfsstrategie gericht is op innovatie."
    },
    {
        "slide": 34,
        "time": "12:38",
        "seconds": 758,
        "title": "Argument 3: Kwaliteit vs Identiteit? (NRC Opinie)",
        "summary": "Nadine Ridder in NRC: 'Identiteit of kwaliteit? Het is én-én'. Weerlegging van het idee dat diversiteit ten koste gaat van kwaliteit."
    },
    {
        "slide": 35,
        "time": "15:08",
        "seconds": 908,
        "title": "Vraag: Wat kunnen we dan doen?",
        "summary": "Praktische interventies tegen vooroordelen en uitsluiting."
    },
    {
        "slide": 36,
        "time": "15:15",
        "seconds": 915,
        "title": "Vier vormen van bias (Williams & Mihaylo, 2019)",
        "summary": "1. Bewijsdwang (Prove it again), 2. Koorddansen (Tightrope), 3. De mamamuur (Maternal wall), 4. Aftroef-oorlog (Tug-of-war)."
    },
    {
        "slide": 37,
        "time": "18:03",
        "seconds": 1083,
        "title": "Doorbreek de bias! (Interrumperen)",
        "summary": "Williams & Mihaylo (2019): Bias is moeilijk uit te roeien, maar wel direct te onderbreken (interrumperen)."
    },
    {
        "slide": 38,
        "time": "18:12",
        "seconds": 1092,
        "title": "Interrumperen van bias in processen (Link bureaucratie)",
        "summary": "Selectie: standaardiseer en objectiveer. Dagelijks management: toewijzing taken en meetings modereren. Personeelsontwikkeling: formalisatie en transparantie."
    },
    {
        "slide": 39,
        "time": "18:28",
        "seconds": 1108,
        "title": "Inclusief leiderschap (Randel, 2018; Carmeli, 2010)",
        "summary": "Definitie: gedrag dat uitnodiging en waardering toont voor ieders bijdrage. Dimensies: openness, availability, accessibility."
    },
    {
        "slide": 40,
        "time": "19:48",
        "seconds": 1188,
        "title": "Inclusief leiderschap & Innovatie: Model (Qi et al., 2019)",
        "summary": "Hypothesemodel: Inclusive leadership -> Perceived organizational support (POS) -> Employee innovative behavior."
    },
    {
        "slide": 41,
        "time": "20:05",
        "seconds": 1205,
        "title": "Inclusief leiderschap & Innovatie: Resultaten (Qi et al., 2019)",
        "summary": "Studie bij 15 Chinese organisaties. Conclusie: inclusief leiderschap versterkt gevoel van waardering en stimuleert innovatief gedrag."
    },
    {
        "slide": 42,
        "time": "20:38",
        "seconds": 1238,
        "title": "Recordaantal vrouwen als bestuurder (NRC / Female Board Index 2024)",
        "summary": "Krantenartikel over recente stijging van vrouwelijke bestuurders bij Nederlandse beursgenoteerde bedrijven."
    },
    {
        "slide": 43,
        "time": "21:05",
        "seconds": 1265,
        "title": "Afsluiting Module 3.2",
        "summary": "Afronding van Hoorcollege 3."
    }
]


def srt_time_to_seconds(ts_str):
    # format: 00:01:06,520
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

        # First slide header if at very start
        if num == "1" and current_slide_idx == 0:
            cur = slides_meta[0]
            lines.append(f"## 📊 Slide {cur['slide']}: {cur['title']}")
            lines.append(f"**Tijdstip in video:** `{cur['time']}` | **Kerninhoud:** *{cur['summary']}*\n")

        lines.append(f"**[{start_ts[:8]}]** {clean_text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated: {output_path}")


def main():
    s1 = VIDEOS_DIR / "5940698_MOT Hoorcollege 3 - module 3.1 (cultuur & waarden)_transcript_nl.srt"
    o1 = VIDEOS_DIR / "Hoorcollege_3_Module_3.1_Slide_Transcript.md"
    generate_annotated_transcript(s1, SLIDES_M31, o1, "Hoorcollege 3 - Module 3.1: Organisatiecultuur en -waarden")

    s2 = VIDEOS_DIR / "5940699_MOT Hoorcollege 3 - module 3.2 (D&I)_transcript_nl.srt"
    o2 = VIDEOS_DIR / "Hoorcollege_3_Module_3.2_Slide_Transcript.md"
    generate_annotated_transcript(s2, SLIDES_M32, o2, "Hoorcollege 3 - Module 3.2: Diversiteit en Inclusie")

    # Combined master file
    master = VIDEOS_DIR / "Hoorcollege_3_Complete_Slide_Annotated_Transcript.md"
    with open(master, "w", encoding="utf-8") as f_out:
        f_out.write("# Management & Organisatietheorie - Hoorcollege 3\n")
        f_out.write("## Volledige Transcriptie met Gekoppelde Slides (Jitse Duijsters)\n\n")
        f_out.write(open(o1, encoding="utf-8").read())
        f_out.write("\n\n" + "=" * 80 + "\n\n")
        f_out.write(open(o2, encoding="utf-8").read())
    print(f"Generated master: {master}")


if __name__ == "__main__":
    main()
