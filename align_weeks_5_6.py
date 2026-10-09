"""
Generate synchronized slide-annotated Dutch transcripts for Hoorcollege 5 and Hoorcollege 6:
  - Hoorcollege 5 (Slides 1 to 37):
      * Module 5.1: Organisatieverandering (Slides 1 to 25)
      * Module 5.2: Crisis (Slides 26 to 37)
  - Hoorcollege 6 (Slides 1 to 47):
      * Module 6.1: Interorganisational Relationships & Open Innovatie (Slides 1 to 37)
      * Module 6.2: Absorptive Capacity (Slides 38 to 47)
"""

import os
import re
from pathlib import Path

VIDEOS_DIR = Path("downloads/videos")

# ==============================================================================
# SLIDE METADATA - HOORCOLLEGE 5: MODULE 5.1 (Slides 1 to 25)
# ==============================================================================
SLIDES_M51 = [
    {
        "slide": 1, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 5.1 - Organisatieverandering",
        "summary": "Introductie van Hoorcollege 5 door Jitse Duijsters: Organisatieverandering & Crisis."
    },
    {
        "slide": 2, "time": "00:15", "seconds": 15,
        "title": "Agenda Hoorcollege 5",
        "summary": "De driedeling van college 5: 1. Introductie, 2. Het Wat & Hoe van Organisatieverandering (Daft), 3. Crisis! (Probst & Raisch)."
    },
    {
        "slide": 3, "time": "01:05", "seconds": 65,
        "title": "Introductie: Waarom moeten organisaties veranderen?",
        "summary": "Stilstand is achteruitgang; organisaties moeten wendbaar zijn om te overleven in dynamische markten."
    },
    {
        "slide": 4, "time": "01:25", "seconds": 85,
        "title": "Steeds complexere omgeving",
        "summary": "Toenemende marktsnelheid, digitalisering, globalisering en onvoorspelbaarheid dwingen tot continue aanpassing."
    },
    {
        "slide": 5, "time": "01:55", "seconds": 115,
        "title": "Wat is organisatieverandering? (Definities)",
        "summary": "Daft et al. (2020): 'The adoption of a new idea or behavior by an organization'. Deszca et al. (2020): 'Planned alterations of organizational components to improve effectiveness or efficiency'."
    },
    {
        "slide": 6, "time": "02:30", "seconds": 150,
        "title": "Wat is innovatie? (Verschil met verandering)",
        "summary": "Daft: adoptie van een idee dat nieuw is voor de industrie/omgeving. Damanpour & Wischnevsky: technische vs administratieve innovatie. Amabile: succesvolle implementatie van creatieve ideeën."
    },
    {
        "slide": 7, "time": "03:00", "seconds": 180,
        "title": "Agenda: Het Wat & Hoe van Organisatieverandering",
        "summary": "Start van blok 2: typen verandering, veranderdomeinen en het implementatieproces."
    },
    {
        "slide": 8, "time": "04:20", "seconds": 260,
        "title": "Typen organisatieverandering: Radical vs. Incremental change",
        "summary": "Radical change (doing something new, structureel/strategisch, snel, grote stappen) vs. Incremental change (doing the same thing better, geleidelijk, gefocust, continu)."
    },
    {
        "slide": 9, "time": "05:40", "seconds": 340,
        "title": "Koppeling: Exploration, Exploitation & Ambidexterity",
        "summary": "Radicale verandering = exploratie; incrementele verandering = exploitatie. Ambidexterity ('tweehandigheid') is het balanceren van beide binnen één organisatie."
    },
    {
        "slide": 10, "time": "06:00", "seconds": 360,
        "title": "Veranderdomeinen: Het WAT van verandering",
        "summary": "De vier domeinen van Daft: 1. Technologische verandering, 2. Producten & diensten, 3. Strategie & structuur, 4. Cultuur (& gedragsverandering)."
    },
    {
        "slide": 11, "time": "07:10", "seconds": 430,
        "title": "Veranderdomeinen: Samenspel en overzicht",
        "summary": "Onderlinge afhankelijkheid van de vier veranderobjecten bij integrale veranderingstrajecten."
    },
    {
        "slide": 12, "time": "07:15", "seconds": 435,
        "title": "Veranderdomein 1: Technologische (technische) verandering",
        "summary": "Productieprocessen en vaardigheden. Faciliterende structuren: ambidextrous approach, switching structures, creative departments, idea incubators, venture teams, idea champions. Richting: vaak bottom-up."
    },
    {
        "slide": 13, "time": "10:25", "seconds": 625,
        "title": "Veranderdomein 2: Veranderingen in producten & diensten",
        "summary": "Nieuwe of aangepaste producten/diensten. Time-based competition en het Horizontal Coordination Model (afstemming R&D, marketing, productie en boundary spanning). Richting: vaak bottom-up."
    },
    {
        "slide": 14, "time": "12:50", "seconds": 770,
        "title": "Veranderdomein 3: Strategie & structuur (Dual Core Approach)",
        "summary": "Administratieve domein (supervisie, governance, belonings- en controlesystemen). Dual core: technical core vs administrative core. Richting: top-down door management geïnitieerd."
    },
    {
        "slide": 15, "time": "15:15", "seconds": 915,
        "title": "Strategie & structuur: De Top-down Paradox",
        "summary": "Belangrijke les: zelfs structuren die bedoeld zijn om bottom-up verandering te faciliteren, moeten bijna altijd top-down worden ingevoerd."
    },
    {
        "slide": 16, "time": "15:25", "seconds": 925,
        "title": "Casus Thuiswerken (Verandering in toezicht & beleid)",
        "summary": "Praktijkvoorbeeld: verandering in administratieve controles en vertrouwen rondom structureel thuiswerken na de Covid-19 pandemie."
    },
    {
        "slide": 17, "time": "16:30", "seconds": 990,
        "title": "Veranderdomein 4: Cultuur (& gedragsverandering)",
        "summary": "Verandering in mind-set, waarden, houdingen en normen. Organization Development (OD). Richting: top-down of emergent; verloopt inherent langzaam en vraagt actieve participatie."
    },
    {
        "slide": 18, "time": "18:35", "seconds": 1115,
        "title": "Casus Cultuurproblemen (Ajax, Publieke Omroep, Corps)",
        "summary": "Praktijkvoorbeelden van grensoverschrijdend gedrag en toxische culturen: hoe moeilijk cultuurverandering is en waarom formele regels alleen niet volstaan."
    },
    {
        "slide": 19, "time": "19:05", "seconds": 1145,
        "title": "Participatieve aanpak: Organizational Development (OD)",
        "summary": "Participatief vs. unilateraal. Veranderen 'met' in plaats van 'voor' mensen (Burnes, 2014; Daft). Gedragsverandering ontstaat pas bij gezamenlijk eigenaarschap."
    },
    {
        "slide": 20, "time": "20:20", "seconds": 1220,
        "title": "Action Research binnen OD (Kurt Lewin)",
        "summary": "Drie pijlers: Understanding, Action taking en Participating. Vier cyclische stappen: Diagnose -> Plan -> Implement -> Evaluate & institutionalize."
    },
    {
        "slide": 21, "time": "22:15", "seconds": 1335,
        "title": "Het 'Hoe' van organisatieverandering: Fasering",
        "summary": "Drie fasen van veranderprocessen: 1. Diagnose (Exhibit 12.4), 2. Implementatie, 3. Bestendiging (institutionalisering)."
    },
    {
        "slide": 22, "time": "23:40", "seconds": 1420,
        "title": "Lineair perspectief op implementatie (Daft & Kotter)",
        "summary": "Zeven stappen: 1. Sense of urgency, 2. Coalition, 3. Vision & strategy, 4. Idea fitting need, 5. Overcome resistance, 6. Change teams, 7. Change champions."
    },
    {
        "slide": 23, "time": "25:30", "seconds": 1530,
        "title": "Overwinnen van weerstand tegen verandering",
        "summary": "Aanpakken van weerstand (stap 5): communicatie, psychologische veiligheid, afstemming van doelen, actieve participatie en in uiterste noodzaak dwang ('forcing/coercion')."
    },
    {
        "slide": 24, "time": "27:25", "seconds": 1645,
        "title": "De Veranderformule voor succes",
        "summary": "Formule: [Ontevredenheid huidige situatie (Need) + Enthousiasme over gewenste situatie (Visie) + Kans op succes (Plan)] > Kosten van verandering."
    },
    {
        "slide": 25, "time": "29:00", "seconds": 1740,
        "title": "Afsluiting Module 5.1 & Vooruitblik Crisis",
        "summary": "Samenvatting van het 'wat' en 'hoe' van organisatieverandering en introductie van Module 5.2 (Crisis bij succesvolle organisaties)."
    }
]

# ==============================================================================
# SLIDE METADATA - HOORCOLLEGE 5: MODULE 5.2 (Slides 26 to 37)
# ==============================================================================
SLIDES_M52 = [
    {
        "slide": 26, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 5.2 - Crisis",
        "summary": "Introductie van Module 5.2 door Jitse Duijsters: Organisatieverandering & Crisis (Probst & Raisch, 2005)."
    },
    {
        "slide": 27, "time": "00:35", "seconds": 35,
        "title": "Waarom crisis bij succesvolle bedrijven? (Probst & Raisch)",
        "summary": "Crisis overkomt niet alleen falende bedrijven aan het einde van hun levenscyclus, maar juist marktleiders op het toppunt van hun succes door blinde vlekken."
    },
    {
        "slide": 28, "time": "01:05", "seconds": 65,
        "title": "Twee faalsyndromen: Premature Aging & Burnout",
        "summary": "Introductie van de twee prototypische faalpaden uit Probst & Raisch: 1. Premature Aging Syndroom (inertie) vs. 2. Burnout Syndroom (overmoed)."
    },
    {
        "slide": 29, "time": "01:40", "seconds": 100,
        "title": "Karakteristieken van Premature Aging",
        "summary": "Uitgestelde besluitvorming, afwezigheid van ambitie, inertie, zelfgenoegzaamheid en vasthouden aan verouderde succesfactoren."
    },
    {
        "slide": 30, "time": "02:15", "seconds": 135,
        "title": "Premature Aging Syndroom: De Tupperware Casus",
        "summary": "Praktijkvoorbeeld: Tupperware bleef decennialang vasthouden aan het vertrouwde 'party-model', miste de online shift en raakte in ernstige financiële crisis."
    },
    {
        "slide": 31, "time": "03:25", "seconds": 205,
        "title": "Burnout Syndroom: Overmoed en Onbeheerste Expansie",
        "summary": "Overmoed (hubris), overmatige focus op snelle winst, onbeheersbare schaalvergroting, autocratisch leiderschap en uitputting van personeel en middelen."
    },
    {
        "slide": 32, "time": "04:40", "seconds": 280,
        "title": "Casus Ahold & Cees van der Hoeven (MT.nl)",
        "summary": "Iconisch burnout-voorbeeld: tomeloze overnamewedloop door CEO Cees van der Hoeven, controleverlies, grootschalige boekhoudfraude bij US Foodservice en de val van Ahold."
    },
    {
        "slide": 33, "time": "05:50", "seconds": 350,
        "title": "Vergelijking: Premature Aging vs. Burnout Syndroom",
        "summary": "Overzicht van het contrast: verstarring door gebrek aan vernieuwing (aging) versus zelfvernietiging door hypergroei en gebrek aan beheersing (burnout)."
    },
    {
        "slide": 34, "time": "07:55", "seconds": 475,
        "title": "Samenhang der faalfactoren: Losgezongen leiderschap",
        "summary": "Het fatale samenspel: te veel radicale veranderingen en overnames leiden ertoe dat medewerkers het niet bijbenen en het topmanagement losraakt van de werkvloer."
    },
    {
        "slide": 35, "time": "09:20", "seconds": 560,
        "title": "Het Vinden van de Juiste Balans (Probst & Raisch, p. 100)",
        "summary": "Balansmodel voor duurzaam succes: groei balanceren met consolidatie, verandering met identiteit, en visionair leiderschap met collegiaal toezicht."
    },
    {
        "slide": 36, "time": "10:10", "seconds": 610,
        "title": "Early Warning Systems & Corporate Governance",
        "summary": "Vier vuistregels: beheersbare groei, behoud van bedrijfsidentiteit, gedeelde macht (checks & balances) en een open vertrouwenscultuur in plaats van toxische rivaliteit."
    },
    {
        "slide": 37, "time": "11:20", "seconds": 680,
        "title": "Afsluiting Module 5.2 / Hoorcollege 5",
        "summary": "Conclusie van Hoorcollege 5: organisatieverandering en crisismanagement als twee kanten van dezelfde medaille. Afronding door Jitse Duijsters."
    }
]

# ==============================================================================
# SLIDE METADATA - HOORCOLLEGE 6: MODULE 6.1 (Slides 1 to 37)
# ==============================================================================
SLIDES_M61 = [
    {
        "slide": 1, "time": "00:00", "seconds": 0,
        "title": "Titelpagina: Module 6.1 - Open Innovatie & Interorganisational Relationships",
        "summary": "Introductie van Hoorcollege 6 door Jitse Duijsters: Interorganisational Relationships (IORs), Open Innovatie, Ecosystemen en Organisatietheorieën."
    },
    {
        "slide": 2, "time": "00:25", "seconds": 25,
        "title": "Agenda Hoorcollege 6",
        "summary": "Het programma van college 6: 1. Open Innovation & Ecosystems, 2. Resource Dependence, 3. Collaborative Networks, 4. Populatie-ecologie, 5. Institutionele theorie, 6. Absorptive Capacity."
    },
    {
        "slide": 3, "time": "00:45", "seconds": 45,
        "title": "Het Closed Innovation Model (Voordelen & Nadelen)",
        "summary": "Traditionele R&D: voordelen (volledige controle, beheersing van intellectueel eigendom) vs. nadelen (hoge R&D-kosten, faalrisico volledig intern, beperkt tot eigen personeel)."
    },
    {
        "slide": 4, "time": "01:25", "seconds": 85,
        "title": "Closed Innovation: Het Trechtermodel (Funnel)",
        "summary": "De klassieke innovatietrechter: ideeën ontstaan binnen het eigen lab, worden intern gefilterd en bereiken uitsluitend via de eigen organisatie de markt."
    },
    {
        "slide": 5, "time": "02:05", "seconds": 125,
        "title": "Closed Innovation: Grondbeginselen en Aannames",
        "summary": "Kernprincipes: 'De slimste mensen werken voor ons', 'First-mover voordeel is doorslaggevend', 'We moeten onze intellectuele eigendom strikt afschermen om te winnen'."
    },
    {
        "slide": 6, "time": "02:45", "seconds": 165,
        "title": "Wat is er veranderd in de omgeving?",
        "summary": "Waarom het gesloten model niet meer volstaat: toegenomen kwaliteit van universitair onderzoek, hoge mobiliteit van toptalent, venture capital en kortere productlevenscycli."
    },
    {
        "slide": 7, "time": "03:20", "seconds": 200,
        "title": "Het Open Innovation Model (Henry Chesbrough, 2003)",
        "summary": "Kennis en ideeën stromen vrij in en uit de onderneming via samenwerking met lead users, toeleveranciers, universiteiten en zelfs concurrenten; hogere novelty en snelheid."
    },
    {
        "slide": 8, "time": "04:45", "seconds": 285,
        "title": "Open Innovation: De Poreuze Trechter",
        "summary": "Visuele weergave: de wanden van de innovatietrechter zijn poreus (inbound en outbound stromen, spin-offs, licenties en externe commercialisering)."
    },
    {
        "slide": 9, "time": "05:25", "seconds": 325,
        "title": "Open Innovation: Nieuwe Grondbeginselen",
        "summary": "Nieuwe aannames: niet alle slimme mensen werken voor ons; externe R&D benutten; een superieur businessmodel is belangrijker dan als eerste zijn; andermans IP kopen en eigen IP licentiëren."
    },
    {
        "slide": 10, "time": "06:25", "seconds": 385,
        "title": "Organizational Ecosystems (Definitie & Kenmerken)",
        "summary": "Organisaties als onderling afhankelijke gemeenschappen die gezamenlijk evolueren; vervagen van de grenzen tussen pure concurrentie en coöperatie."
    },
    {
        "slide": 11, "time": "07:20", "seconds": 440,
        "title": "Voorbeeld Ecosysteem: De Apple App Store",
        "summary": "Apple brengt miljoenen onafhankelijke app-ontwikkelaars, consumenten, betalingsproviders en toezichthouders bijeen in een bloeiend, zelfregulerend ecosysteem."
    },
    {
        "slide": 12, "time": "08:10", "seconds": 490,
        "title": "Waarom werken organisaties samen? (Centrale Vraag)",
        "summary": "De kern van Hoorcollege 6: welke theorieën verklaren waarom bedrijven relaties aangaan (Interorganisational Relationships - IORs) en hoe die functioneren?"
    },
    {
        "slide": 13, "time": "09:00", "seconds": 540,
        "title": "De 4 Perspectieven op IORs (Daft et al., p. 185)",
        "summary": "Vierledige typologiematrix: Resource Dependence vs Collaborative Network (dissimilar) en Population Ecology vs Institutional Theory (similar) gekruist met competitief vs coöperatief."
    },
    {
        "slide": 14, "time": "09:15", "seconds": 555,
        "title": "Agenda: Perspectief 1 - Resource Dependence",
        "summary": "Start van de bespreking van de vier perspectieven met het Resource Dependence model (Pfeffer & Salancik / Daft)."
    },
    {
        "slide": 15, "time": "09:30", "seconds": 570,
        "title": "1. Resource Dependence Perspectief",
        "summary": "Samenwerken om omgevingsafhankelijkheid van schaarse hulpbronnen te minimaliseren; paradox: samenwerking creëert vaak nieuwe afhankelijkheden en asymmetrische macht."
    },
    {
        "slide": 16, "time": "12:20", "seconds": 740,
        "title": "2. Collaborative Network Perspectief",
        "summary": "Definitie: organisaties kiezen er bewust voor om wederzijds afhankelijk te worden om gezamenlijk hogere productiviteit en waarde te realiseren."
    },
    {
        "slide": 17, "time": "12:45", "seconds": 765,
        "title": "Collaborative Networks: Netwerkstructuren (Jay van Zyl)",
        "summary": "Bedrijven zijn verknoopt in dichte ecosystemen van toeleveranciers en partners (bv. Amazon-platformnetwerk)."
    },
    {
        "slide": 18, "time": "13:10", "seconds": 790,
        "title": "Collaborative Network: Waarom samenwerken?",
        "summary": "Motieven: risicospreiding, kostenverlaging, gezamenlijke innovatie, profilering en snelle toegang tot wereldwijde afzetmarkten."
    },
    {
        "slide": 19, "time": "13:35", "seconds": 815,
        "title": "Collaborative Network: Hoe samenwerken? ('Coopetition')",
        "summary": "Gelijktijdig optreden van concurrentie en samenwerking (coopetition); dynamische partnerships; verschuiving van vijandsbeeld naar langdurig bondgenootschap."
    },
    {
        "slide": 20, "time": "14:25", "seconds": 865,
        "title": "3. Populatie-ecologie (Charles Darwin, 1859)",
        "summary": "Biologische evolutieleer toegepast op organisaties: de omgeving selecteert welke organisatievormen overleven en floreren."
    },
    {
        "slide": 21, "time": "14:45", "seconds": 885,
        "title": "Populatie-ecologie: Definitie & Populatiedynamiek",
        "summary": "Verklaren van de snelheid waarmee nieuwe organisatievormen ('soorten') ontstaan en uitsterven binnen een populatie met gelijke hulpbronnen."
    },
    {
        "slide": 22, "time": "15:20", "seconds": 920,
        "title": "Populatieverandering: Het Evolutieproces",
        "summary": "Het ontstaan en verdwijnen van organisatievormen als gevolg van omgevingsdruk en technologische revoluties."
    },
    {
        "slide": 23, "time": "16:20", "seconds": 980,
        "title": "Evolutie van Nieuwe Vormen: Platforms & Tech",
        "summary": "Opkomst van netwerkorganisaties en webplatforms (Apple, Google, Amazon, Spotify, Booking, Airbnb) als dominante nieuwe organisatiesoorten."
    },
    {
        "slide": 24, "time": "17:20", "seconds": 1040,
        "title": "Het Drietrapsproces van Natuurlijke Selectie",
        "summary": "De motor van evolutie: 1. Variatie (nieuwe ideeën/startups), 2. Selectie (omgeving toetst levensvatbaarheid), 3. Retentie (succesvolle vormen bestendigen)."
    },
    {
        "slide": 25, "time": "18:35", "seconds": 1115,
        "title": "Overlevingsstrategieën: r-strategen vs. K-strategen",
        "summary": "Vroege/dynamische markt: veel, klein, lage levensverwachting (r-strategie) vs. late/stabiele markt: weinig, groot, hoge levensverwachting (K-strategie)."
    },
    {
        "slide": 26, "time": "19:35", "seconds": 1175,
        "title": "Specialists vs. Generalists",
        "summary": "Specialist: scherpe niche, superieur competitief binnen de niche, maar kwetsbaar bij verandering. Generalist: breed portfolio, robuust tegen marktschokken."
    },
    {
        "slide": 27, "time": "20:10", "seconds": 1210,
        "title": "4. Institutionele Theorie: Introductie",
        "summary": "Organisaties overleven en floreren door congruentie te waarborgen tussen hun gedrag en de verwachtingen, normen en waarden uit hun maatschappelijke omgeving (legitimiteit)."
    },
    {
        "slide": 28, "time": "21:10", "seconds": 1270,
        "title": "Scott (2005) & Daft: Instituties Legitimeren Gedrag",
        "summary": "Onderzoek naar hoe regels en routines gezaghebbende gedragsnormen worden; handelen moet als 'desirable, proper and appropriate' worden ervaren."
    },
    {
        "slide": 29, "time": "22:15", "seconds": 1335,
        "title": "Assumpties van de Institutionele Theorie",
        "summary": "Historische pad-afhankelijkheid (oude structuren beperken nieuwe), inertie en stabiliteit, en legitimatie als primaire overlevingsstrategie in bestuur."
    },
    {
        "slide": 30, "time": "23:30", "seconds": 1410,
        "title": "Wat zijn Instituties? (Wetmatigheden en Routines)",
        "summary": "Gevestigde wetten, sociale mechanismen en stabiele, gewaardeerde gedragspatronen die orde en betekenis geven aan sociaal handelen (Oxford, Huntington, Turner)."
    },
    {
        "slide": 31, "time": "24:15", "seconds": 1455,
        "title": "Organizational Isomorphism (Gareth Jones, Hs 4)",
        "summary": "Het proces waardoor organisaties binnen dezelfde populatie steeds meer op elkaar gaan lijken; de drie pijlers van DiMaggio & Powell."
    },
    {
        "slide": 32, "time": "25:10", "seconds": 1510,
        "title": "Isomorfisme 1: Coercive Isomorphism (Dwingend)",
        "summary": "Conformiteit afgedwongen door wetgeving, toezichthouders en overheidsregulering (bv. corporate governance codes, verplichte audits, privacywetgeving)."
    },
    {
        "slide": 33, "time": "25:30", "seconds": 1530,
        "title": "Isomorfisme 2: Mimetic Isomorphism (Mimetisch / Imitatie)",
        "summary": "Bij hoge onzekerheid kopiëren organisaties automatisch toonaangevende succesvolle concurrenten (bv. impact factors, ranglijsten, benchmarking)."
    },
    {
        "slide": 34, "time": "27:10", "seconds": 1630,
        "title": "Isomorfisme 3: Normative Isomorphism (Normatief)",
        "summary": "Gedrag gestuurd door professionele standaarden, beroepsethiek, universitaire curricula en integriteitscodes (bv. artseneed, bankierseed)."
    },
    {
        "slide": 35, "time": "27:30", "seconds": 1650,
        "title": "Casus Legitimiteit & Boetes (ING & Rabobank)",
        "summary": "Wat gebeurt er als normen worden geschonden? Miljoenenboetes wegens falend witwastoezicht tasten de legitimiteit van de gehele bankensector aan."
    },
    {
        "slide": 36, "time": "28:20", "seconds": 1700,
        "title": "Synthese van Isomorfe Druk in Industrieën",
        "summary": "Waarom organisaties in volwassen markten zo uniform worden door de gecombineerde werking van dwang, imitatie en normatieve standaarden."
    },
    {
        "slide": 37, "time": "28:25", "seconds": 1705,
        "title": "Eindoverzicht: De 4 IOR-Perspectieven (Daft Matrix)",
        "summary": "Complete synthese van de 4 kwadranten (Resource Dependence, Collaborative Network, Population Ecology, Institutional Theory) en overgangsvraag naar Module 6.2."
    }
]

# ==============================================================================
# SLIDE METADATA - HOORCOLLEGE 6: MODULE 6.2 (Slides 38 to 47)
# ==============================================================================
SLIDES_M62 = [
    {
        "slide": 38, "time": "00:00", "seconds": 0,
        "title": "De Kernvraag: Waarom nog interne R&D?",
        "summary": "Als samenwerken en open innovatie zo voordelig zijn, waarom besteden organisaties dan nog altijd miljarden aan eigen laboratoria en interne innovatie?"
    },
    {
        "slide": 39, "time": "00:15", "seconds": 15,
        "title": "Koppeling: IORs en Interne Capaciteiten",
        "summary": "Overgang van externe netwerken naar interne bekwaamheden en het samenspel daartussen."
    },
    {
        "slide": 40, "time": "00:20", "seconds": 20,
        "title": "Titelpagina: Module 6.2 - Absorptive Capacity",
        "summary": "Introductie van de afsluitende inhoudelijke module door Jitse Duijsters: Absorptive Capacity."
    },
    {
        "slide": 41, "time": "01:15", "seconds": 75,
        "title": "Complementariteit: Interne & Externe Kennis (Cassiman & Veugelers, 2006)",
        "summary": "Interne en externe kennis zijn geen vervangers (substituten) maar vullen elkaar aan (complementen): interne R&D verhoogt de effectiviteit van externe kennisbenutting."
    },
    {
        "slide": 42, "time": "04:10", "seconds": 250,
        "title": "De Dubbele Rol van Interne R&D",
        "summary": "R&D produceert niet alleen directe nieuwe uitvindingen, maar bouwt de interne kennisbasis op die nodig is om externe technologieën überhaupt te begrijpen."
    },
    {
        "slide": 43, "time": "05:55", "seconds": 355,
        "title": "Definitie Absorptive Capacity (Cohen & Levinthal, 1990)",
        "summary": "'The ability of a firm to recognize the economic value of new, external information, assimilate this information, and apply it to commercial ends' (en Mowery & Oxley, 1995)."
    },
    {
        "slide": 44, "time": "06:50", "seconds": 410,
        "title": "Waarom Bedrijven Absorptive Capacity Nodig Hebben",
        "summary": "Bedrijven zonder ACAP vinden geen veelbelovende partners, kiezen de verkeerde technologieën en slagen er niet in om externe kennis om te zetten in winstgevende producten."
    },
    {
        "slide": 45, "time": "08:50", "seconds": 530,
        "title": "Typen Absorptive Capacity: Het Model van Zahra & George (2002)",
        "summary": "Fundamenteel onderscheid: Potentiële Absorptive Capacity (PACAP: verwerving en assimilatie) vs. Gerealiseerde Absorptive Capacity (RACAP: transformatie en exploitatie)."
    },
    {
        "slide": 46, "time": "09:30", "seconds": 570,
        "title": "De Vier Dimensies en Social Integration Mechanisms",
        "summary": "Het volledige proces: Acquisition -> Assimilation -> Transformation -> Exploitation. De cruciale rol van sociale integratiemechanismen en de efficiency ratio."
    },
    {
        "slide": 47, "time": "10:25", "seconds": 625,
        "title": "Afsluiting Module 6.2 & Hoorcollegereeks M&OT",
        "summary": "Einde van Hoorcollege 6 en afronding van de theoretische modules door Jitse Duijsters. Vooruitblik naar Hoorcollege 7 (Examentraining, tips en cursusrecap)."
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
    lines.append(f"> **Totaal aantal slides in deze module:** {len(slides_meta)}\n")
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
    # ==========================================================================
    # WEEK 5 ALIGNMENT
    # ==========================================================================
    s51 = VIDEOS_DIR / "5977053_M&OT Hoorcollege 5 - Module 5.1 (Organisatieverandering)_transcript_nl.srt"
    o51 = VIDEOS_DIR / "Hoorcollege_5_Module_5.1_Slide_Transcript.md"
    generate_annotated_transcript(s51, SLIDES_M51, o51, "Hoorcollege 5 - Module 5.1: Organisatieverandering")

    s52 = VIDEOS_DIR / "5977054_M&OT Hoorcollege 5 - Module 5.2 (Crisis)_transcript_nl.srt"
    o52 = VIDEOS_DIR / "Hoorcollege_5_Module_5.2_Slide_Transcript.md"
    generate_annotated_transcript(s52, SLIDES_M52, o52, "Hoorcollege 5 - Module 5.2: Crisis")

    master5 = VIDEOS_DIR / "Hoorcollege_5_Complete_Slide_Annotated_Transcript.md"
    with open(master5, "w", encoding="utf-8") as f_out:
        f_out.write("# Management & Organisatietheorie - Hoorcollege 5\n")
        f_out.write("## Volledige Transcriptie met Gekoppelde Slides (Jitse Duijsters)\n")
        f_out.write("### Thema's: Organisatieverandering & Crisis (Slides 1 - 37)\n\n")
        f_out.write(open(o51, encoding="utf-8").read())
        f_out.write("\n\n" + "=" * 80 + "\n\n")
        f_out.write(open(o52, encoding="utf-8").read())
    print(f"Generated master: {master5.name}")

    # ==========================================================================
    # WEEK 6 ALIGNMENT
    # ==========================================================================
    s61 = VIDEOS_DIR / "5981787_M&OT Hoorcollege 6 - Module 6.1 (IORs & OI)_transcript_nl.srt"
    o61 = VIDEOS_DIR / "Hoorcollege_6_Module_6.1_Slide_Transcript.md"
    generate_annotated_transcript(s61, SLIDES_M61, o61, "Hoorcollege 6 - Module 6.1: Interorganisational Relationships & Open Innovatie")

    s62 = VIDEOS_DIR / "5981789_M&OT Hoorcollege 6 - Module 6.2 (ACAP)_transcript_nl.srt"
    o62 = VIDEOS_DIR / "Hoorcollege_6_Module_6.2_Slide_Transcript.md"
    generate_annotated_transcript(s62, SLIDES_M62, o62, "Hoorcollege 6 - Module 6.2: Absorptive Capacity")

    master6 = VIDEOS_DIR / "Hoorcollege_6_Complete_Slide_Annotated_Transcript.md"
    with open(master6, "w", encoding="utf-8") as f_out:
        f_out.write("# Management & Organisatietheorie - Hoorcollege 6\n")
        f_out.write("## Volledige Transcriptie met Gekoppelde Slides (Jitse Duijsters)\n")
        f_out.write("### Thema's: Interorganisational Relationships, Open Innovatie & Absorptive Capacity (Slides 1 - 47)\n\n")
        f_out.write(open(o61, encoding="utf-8").read())
        f_out.write("\n\n" + "=" * 80 + "\n\n")
        f_out.write(open(o62, encoding="utf-8").read())
    print(f"Generated master: {master6.name}")


if __name__ == "__main__":
    main()
