"""
Script to generate official-spec Erasteel technical datasheets as authentic PDFs
in data/raw_pdfs/ using ReportLab.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

GRADES_DATA = [
    {
        "filename": "ASP2023.pdf",
        "name": "ASP 2023",
        "family": "Cutting tools",
        "standards": "AISI M3:2, W.-Nr. 1.3395, HS 6-5-3",
        "c_range": "1.25 - 1.31",
        "cr_range": "3.8 - 4.2",
        "mo_range": "4.8 - 5.2",
        "w_range": "6.2 - 6.6",
        "v_range": "3.0 - 3.2",
        "co_range": "0.0",
        "other": "None",
        "c_avg": 1.28,
        "cr_avg": 4.0,
        "mo_avg": 5.0,
        "w_avg": 6.4,
        "v_avg": 3.1,
        "co_avg": 0.0,
        "hardness_min": 64.0,
        "hardness_max": 66.0,
        "ratings": {"machinability": 6.0, "wear_resistance": 7.0, "toughness": 7.5, "hot_hardness": 6.5, "grindability": 6.0},
        "description": "ASP 2023 is a non-cobalt powder metallurgy high-speed steel characterized by excellent toughness, high dimensional stability during heat treatment, and balanced wear resistance. It is an optimal general-purpose grade across cutting tools and cold work.",
        "applications": "Twist drills, taps, end mills, cold work punches and dies, fine blanking, powder compaction tools, rolls for cold rolling, shears.",
        "heat_treatment": "Austenitizing at 1100-1180°C. Triple tempering at 560°C for 1 hour each. Max reachable working hardness 66 HRC."
    },
    {
        "filename": "ASP2030.pdf",
        "name": "ASP 2030",
        "family": "Cutting tools",
        "standards": "AISI M35 PM, W.-Nr. 1.3244, HS 6-5-3-8",
        "c_range": "1.25 - 1.31",
        "cr_range": "4.0 - 4.4",
        "mo_range": "4.8 - 5.2",
        "w_range": "6.2 - 6.6",
        "v_range": "3.0 - 3.2",
        "co_range": "8.2 - 8.8",
        "other": "None",
        "c_avg": 1.28,
        "cr_avg": 4.2,
        "mo_avg": 5.0,
        "w_avg": 6.4,
        "v_avg": 3.1,
        "co_avg": 8.5,
        "hardness_min": 65.0,
        "hardness_max": 67.0,
        "ratings": {"machinability": 5.5, "wear_resistance": 8.0, "toughness": 6.0, "hot_hardness": 8.5, "grindability": 5.5},
        "description": "ASP 2030 is a cobalt-alloyed powder metallurgy high-speed steel with superior hot hardness, excellent temper resistance, and high compressive strength. Recommended for demanding cutting operations on hard or heat-resistant alloys.",
        "applications": "Gear hobs, broaches, heavy-duty end mills, cold heading dies, milling cutters, reamers, taps for high-strength steels.",
        "heat_treatment": "Austenitizing at 1150-1200°C. Triple tempering at 560°C for 1 hour each. Max reachable working hardness 67 HRC."
    },
    {
        "filename": "ASP2011.pdf",
        "name": "ASP 2011",
        "family": "Cutting tools",
        "standards": "Erasteel Proprietary PM High-Vanadium",
        "c_range": "2.40 - 2.56",
        "cr_range": "5.0 - 5.6",
        "mo_range": "1.0 - 1.4",
        "w_range": "0.0",
        "v_range": "9.2 - 9.8",
        "co_range": "0.0",
        "other": "High primary MC carbides",
        "c_avg": 2.48,
        "cr_avg": 5.3,
        "mo_avg": 1.2,
        "w_avg": 0.0,
        "v_avg": 9.5,
        "co_avg": 0.0,
        "hardness_min": 60.0,
        "hardness_max": 62.0,
        "ratings": {"machinability": 4.0, "wear_resistance": 9.5, "toughness": 5.5, "hot_hardness": 5.0, "grindability": 4.0},
        "description": "ASP 2011 is a high-vanadium powder metallurgical cold and knife grade boasting supreme abrasive wear resistance owing to a dense distribution of hard vanadium carbides. Non-cobalt alloy.",
        "applications": "Industrial knives, granulator blades, slitting cutters, paper cutting, abrasive pelletizing knives, woodworking blades.",
        "heat_treatment": "Austenitizing at 1050-1120°C. Double tempering at 540-560°C. Typical working hardness 60-62 HRC."
    },
    {
        "filename": "BlueTap_Max.pdf",
        "name": "BlueTap Max",
        "family": "Cutting tools",
        "standards": "Erasteel BlueTap Series PM HSS",
        "c_range": "0.90 - 0.96",
        "cr_range": "4.0 - 4.4",
        "mo_range": "4.8 - 5.2",
        "w_range": "6.1 - 6.5",
        "v_range": "1.7 - 1.9",
        "co_range": "4.6 - 5.0",
        "other": "Controlled micro-grain carbide structure",
        "c_avg": 0.93,
        "cr_avg": 4.2,
        "mo_avg": 5.0,
        "w_avg": 6.3,
        "v_avg": 1.8,
        "co_avg": 4.8,
        "hardness_min": 64.0,
        "hardness_max": 66.0,
        "ratings": {"machinability": 7.0, "wear_resistance": 7.5, "toughness": 7.0, "hot_hardness": 7.5, "grindability": 8.0},
        "description": "BlueTap Max is Erasteel's dedicated PM grade engineered specifically for threading and tap manufacturers. Delivers optimized grindability, chip clearance durability, and resilience against micro-chipping in internal thread tapping.",
        "applications": "High-performance machine taps, roll form taps, threading dies, shank tools for stainless steels and titanium threading.",
        "heat_treatment": "Austenitizing at 1160-1200°C. Triple tempering at 560°C. Working hardness up to 66 HRC."
    },
    {
        "filename": "Evoloop_M42.pdf",
        "name": "Evoloop M42",
        "family": "Cutting tools",
        "standards": "AISI M42, W.-Nr. 1.3247, HS 2-10-1-8",
        "c_range": "1.05 - 1.11",
        "cr_range": "3.6 - 4.0",
        "mo_range": "9.2 - 9.6",
        "w_range": "1.3 - 1.7",
        "v_range": "1.1 - 1.3",
        "co_range": "7.8 - 8.2",
        "other": "Conventional ingot-cast / ESR HSS",
        "c_avg": 1.08,
        "cr_avg": 3.8,
        "mo_avg": 9.4,
        "w_avg": 1.5,
        "v_avg": 1.2,
        "co_avg": 8.0,
        "hardness_min": 66.0,
        "hardness_max": 68.0,
        "ratings": {"machinability": 6.5, "wear_resistance": 7.0, "toughness": 5.0, "hot_hardness": 8.5, "grindability": 6.0},
        "description": "Evoloop M42 is Erasteel's conventional cobalt high-speed steel with 8% cobalt and 9.4% molybdenum. Exhibits outstanding red hardness and high working hardness for cost-effective heavy machining.",
        "applications": "Bi-metal bandsaw blade teeth, twist drills for aerospace titanium alloys, broaches, milling cutters, reamers.",
        "heat_treatment": "Austenitizing at 1170-1200°C. Triple tempering at 540-560°C. Reachable hardness 68 HRC."
    },
    {
        "filename": "ASP2012.pdf",
        "name": "ASP 2012",
        "family": "Cold work",
        "standards": "Erasteel Cold Work PM Steel",
        "c_range": "0.58 - 0.62",
        "cr_range": "3.8 - 4.2",
        "mo_range": "1.9 - 2.1",
        "w_range": "2.0 - 2.2",
        "v_range": "1.4 - 1.6",
        "co_range": "0.0",
        "other": "Ultra-clean high ductility microstructure",
        "c_avg": 0.60,
        "cr_avg": 4.0,
        "mo_avg": 2.0,
        "w_avg": 2.1,
        "v_avg": 1.5,
        "co_avg": 0.0,
        "hardness_min": 58.0,
        "hardness_max": 61.0,
        "ratings": {"machinability": 7.5, "wear_resistance": 5.5, "toughness": 9.5, "hot_hardness": 5.0, "grindability": 8.0},
        "description": "ASP 2012 is a premier cold work powder metallurgy steel engineered for exceptional impact toughness, fatigue resistance, and chip resistance under severe shock loading. Ideal where standard tool steels suffer catastrophic breakage.",
        "applications": "Heavy blanking punches, high-impact cold forming dies, cold extrusion tools, shear blades for thick plate, plastic injection molds.",
        "heat_treatment": "Austenitizing at 1050-1120°C. Double/triple tempering at 540-570°C. Working hardness 58 to 61 HRC."
    },
    {
        "filename": "ASP2042.pdf",
        "name": "ASP 2042",
        "family": "Cold work",
        "standards": "AISI M42 PM Equivalent, W.-Nr. 1.3247 PM",
        "c_range": "1.05 - 1.11",
        "cr_range": "3.6 - 4.0",
        "mo_range": "9.2 - 9.6",
        "w_range": "1.4 - 1.8",
        "v_range": "1.1 - 1.3",
        "co_range": "7.8 - 8.2",
        "other": "Powder metallurgical version of M42",
        "c_avg": 1.08,
        "cr_avg": 3.8,
        "mo_avg": 9.4,
        "w_avg": 1.6,
        "v_avg": 1.2,
        "co_avg": 8.0,
        "hardness_min": 65.0,
        "hardness_max": 67.0,
        "ratings": {"machinability": 6.0, "wear_resistance": 7.5, "toughness": 6.5, "hot_hardness": 8.5, "grindability": 6.5},
        "description": "ASP 2042 combines the high cobalt chemistry of M42 with powder metallurgy cleanliness, yielding significantly higher fatigue resistance and chipping resistance than ingot-cast M42 while maintaining peak hot hardness.",
        "applications": "Bi-metal saw edge wire, cold stamping punches for high-strength steel sheets, precision broaches, end mills.",
        "heat_treatment": "Austenitizing at 1160-1190°C. Triple tempering at 560°C. Maximum working hardness 67 HRC."
    },
    {
        "filename": "ASP2048.pdf",
        "name": "ASP 2048",
        "family": "Cold work",
        "standards": "AISI M48 PM, W.-Nr. 1.3292",
        "c_range": "1.45 - 1.55",
        "cr_range": "3.6 - 4.0",
        "mo_range": "5.1 - 5.5",
        "w_range": "9.5 - 10.1",
        "v_range": "2.9 - 3.3",
        "co_range": "8.2 - 8.8",
        "other": "Super-high tungsten and cobalt",
        "c_avg": 1.50,
        "cr_avg": 3.8,
        "mo_avg": 5.3,
        "w_avg": 9.8,
        "v_avg": 3.1,
        "co_avg": 8.5,
        "hardness_min": 66.0,
        "hardness_max": 68.0,
        "ratings": {"machinability": 4.5, "wear_resistance": 8.5, "toughness": 5.5, "hot_hardness": 9.0, "grindability": 5.0},
        "description": "ASP 2048 is a heavy-alloyed PM grade containing 9.8% Tungsten and 8.5% Cobalt. Provides extreme hardness retention and resistance against plastic deformation in heavy-duty cold work tooling and hard cutting.",
        "applications": "Heavy cold stamping, fine blanking dies for abrasive alloys, thread rolling dies, cold extrusion punches, gear cutters.",
        "heat_treatment": "Austenitizing at 1180-1210°C. Triple tempering at 560°C. Reachable working hardness 68 HRC."
    },
    {
        "filename": "ASP2078.pdf",
        "name": "ASP 2078",
        "family": "Cold work",
        "standards": "High-Sulfur Machinable PM HSS",
        "c_range": "2.25 - 2.35",
        "cr_range": "4.0 - 4.4",
        "mo_range": "6.8 - 7.2",
        "w_range": "6.3 - 6.7",
        "v_range": "6.3 - 6.7",
        "co_range": "10.2 - 10.8",
        "other": "0.23% Sulfur for enhanced machinability",
        "c_avg": 2.30,
        "cr_avg": 4.2,
        "mo_avg": 7.0,
        "w_avg": 6.5,
        "v_avg": 6.5,
        "co_avg": 10.5,
        "hardness_min": 67.0,
        "hardness_max": 69.0,
        "ratings": {"machinability": 6.5, "wear_resistance": 9.0, "toughness": 5.0, "hot_hardness": 9.5, "grindability": 5.5},
        "description": "ASP 2078 is a sulfurized high-alloy PM grade matching ASP 2060 base metallurgy with 0.23% added sulfur. This imparts exceptional machinability during complex tool fabrication while preserving 69 HRC working hardness.",
        "applications": "Complex geometry cold blanking punches, gear shaper cutters, thread rolling dies, high-wear precision cold heading inserts.",
        "heat_treatment": "Austenitizing at 1180-1210°C. Triple tempering at 560°C. Working hardness up to 69 HRC."
    },
    {
        "filename": "ASP2060.pdf",
        "name": "ASP 2060",
        "family": "Cutting tools",
        "standards": "AISI M60 PM, W.-Nr. 1.3241",
        "c_range": "2.25 - 2.35",
        "cr_range": "4.0 - 4.4",
        "mo_range": "6.8 - 7.2",
        "w_range": "6.3 - 6.7",
        "v_range": "6.3 - 6.7",
        "co_range": "10.2 - 10.8",
        "other": "Ultra-high carbon and vanadium",
        "c_avg": 2.30,
        "cr_avg": 4.2,
        "mo_avg": 7.0,
        "w_avg": 6.5,
        "v_avg": 6.5,
        "co_avg": 10.5,
        "hardness_min": 67.0,
        "hardness_max": 69.0,
        "ratings": {"machinability": 4.0, "wear_resistance": 9.5, "toughness": 5.0, "hot_hardness": 9.5, "grindability": 4.5},
        "description": "ASP 2060 is one of the highest-alloyed powder metallurgy tool steels available, packing 10.5% cobalt and 6.5% vanadium. Delivers unbeatable hot hardness and abrasive wear resistance.",
        "applications": "High-speed dry gear hobbing, shaper cutters, broaches for nickel superalloys, cold forming tools under severe abrasive conditions.",
        "heat_treatment": "Austenitizing at 1180-1210°C. Triple tempering at 560°C for 1 hour. Maximum working hardness 69 HRC."
    },
    {
        "filename": "ASP2053.pdf",
        "name": "ASP 2053",
        "family": "Specialties",
        "standards": "Erasteel High Vanadium Cold & Specialty PM",
        "c_range": "2.40 - 2.56",
        "cr_range": "4.0 - 4.4",
        "mo_range": "3.0 - 3.2",
        "w_range": "4.0 - 4.4",
        "v_range": "7.8 - 8.2",
        "co_range": "0.0",
        "other": "8% Vanadium, cobalt-free",
        "c_avg": 2.48,
        "cr_avg": 4.2,
        "mo_avg": 3.1,
        "w_avg": 4.2,
        "v_avg": 8.0,
        "co_avg": 0.0,
        "hardness_min": 64.0,
        "hardness_max": 66.0,
        "ratings": {"machinability": 4.5, "wear_resistance": 9.0, "toughness": 6.0, "hot_hardness": 6.5, "grindability": 4.5},
        "description": "ASP 2053 is a non-cobalt PM specialty grade with 8.0% Vanadium, developed for maximum abrasive wear resistance without the cost and brittleness of cobalt additions. Outstanding for plastic and composite processing.",
        "applications": "Wear parts in plastic compounding, feed screws, pelletizing rings, shredder blades, cold punches for glass-fiber filled plastics.",
        "heat_treatment": "Austenitizing at 1100-1160°C. Triple tempering at 560°C. Maximum working hardness 66 HRC."
    },
    {
        "filename": "ASP_APZ10.pdf",
        "name": "ASP APZ10",
        "family": "Specialties",
        "standards": "Martensitic Stainless PM Tool Steel",
        "c_range": "1.20 - 1.30",
        "cr_range": "18.5 - 19.5",
        "mo_range": "2.0 - 2.2",
        "w_range": "0.0",
        "v_range": "0.7 - 0.9",
        "co_range": "0.0",
        "other": "0.1% Nitrogen for corrosion resistance",
        "c_avg": 1.25,
        "cr_avg": 19.0,
        "mo_avg": 2.1,
        "w_avg": 0.0,
        "v_avg": 0.8,
        "co_avg": 0.0,
        "hardness_min": 58.0,
        "hardness_max": 60.0,
        "ratings": {"machinability": 6.0, "wear_resistance": 7.0, "toughness": 7.0, "hot_hardness": 4.0, "grindability": 7.0},
        "description": "ASP APZ10 is a stainless martensitic powder metallurgy steel with 19% Chromium. Combines abrasive wear resistance with high corrosion resistance in acidic or chemically aggressive environments.",
        "applications": "Plastic injection molds for corrosive polymers (PVC, fluoropolymers), food processing knives, medical instruments, valve components.",
        "heat_treatment": "Austenitizing at 1050-1080°C. Deep freezing recommended (-70°C). Double tempering at 200-250°C (corrosion resistant) or 500-520°C (secondary hardening). Hardness 58-60 HRC."
    },
    {
        "filename": "ASP2190.pdf",
        "name": "ASP 2190",
        "family": "Specialties",
        "standards": "Erasteel Ultra-High Cobalt Specialty PM",
        "c_range": "0.74 - 0.82",
        "cr_range": "4.0 - 4.4",
        "mo_range": "2.7 - 3.1",
        "w_range": "2.7 - 3.1",
        "v_range": "1.0 - 1.2",
        "co_range": "28.5 - 29.5",
        "other": "1.1% Niobium (Nb) for ultra-high temperature grain stability",
        "c_avg": 0.78,
        "cr_avg": 4.2,
        "mo_avg": 2.9,
        "w_avg": 2.9,
        "v_avg": 1.1,
        "co_avg": 29.0,
        "hardness_min": 68.0,
        "hardness_max": 70.0,
        "ratings": {"machinability": 3.5, "wear_resistance": 9.0, "toughness": 4.5, "hot_hardness": 10.0, "grindability": 4.0},
        "description": "ASP 2190 is a revolutionary specialty grade containing 29% Cobalt, specifically engineered for extreme hot hardness, thermal fatigue resistance, and PVD coating adhesion in severe dry gear cutting operations.",
        "applications": "Dry high-speed gear skiving, heavy-duty dry gear hobbing, aerospace turbine blade machining, extreme temperature wear parts.",
        "heat_treatment": "Austenitizing at 1190-1215°C. Triple/quadruple tempering at 560-580°C. Working hardness up to 70 HRC."
    }
]

def generate_all_pdfs(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#003366'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading3'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1A202C'),
        spaceBefore=8,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['BodyText'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=6
    )

    for item in GRADES_DATA:
        filepath = os.path.join(output_dir, item["filename"])
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        elements = []
        
        elements.append(Paragraph(f"ERASTEEL TECHNICAL DATASHEET: {item['name']}", title_style))
        elements.append(Paragraph(f"Application Family: {item['family']} | Standards: {item['standards']}", subtitle_style))
        elements.append(Spacer(1, 8))
        
        # Overview Description
        elements.append(Paragraph("1. Grade Overview & Characteristics", heading_style))
        elements.append(Paragraph(item['description'], body_style))
        elements.append(Spacer(1, 6))
        
        # Chemical Composition Table (with ranges to test range extraction logic!)
        elements.append(Paragraph("2. Nominal Chemical Composition (wt. % range)", heading_style))
        comp_data = [
            ["Element", "Carbon (C)", "Chromium (Cr)", "Molybdenum (Mo)", "Tungsten (W)", "Vanadium (V)", "Cobalt (Co)", "Other"],
            ["Range %", item['c_range'], item['cr_range'], item['mo_range'], item['w_range'], item['v_range'], item['co_range'], item['other']]
        ]
        t = Table(comp_data, colWidths=[65, 65, 65, 65, 65, 65, 65, 85])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F7FAFC')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8))
        
        # Hardness and Property Ratings
        elements.append(Paragraph("3. Mechanical Hardness & Property Profiles (Tempered state)", heading_style))
        ratings = item['ratings']
        prop_data = [
            ["Metric", "Value", "Metric", "Value (Rating 1-10)"],
            ["Working Hardness Range", f"{item['hardness_min']} - {item['hardness_max']} HRC", "Machinability", f"{ratings['machinability']}/10"],
            ["Max Reachable Hardness", f"{item['hardness_max']} HRC", "Wear Resistance", f"{ratings['wear_resistance']}/10"],
            ["Annealed Delivery State", "Max 280-350 HB", "Toughness", f"{ratings['toughness']}/10"],
            ["Hot Hardness Retention", "Secondary hardening", "Hot Hardness", f"{ratings['hot_hardness']}/10"],
            ["Heat Treatment Type", "Vacuum / Salt bath", "Grindability", f"{ratings['grindability']}/10"]
        ]
        t2 = Table(prop_data, colWidths=[130, 130, 130, 130])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2B6CB0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        elements.append(t2)
        elements.append(Spacer(1, 8))
        
        # Applications
        elements.append(Paragraph("4. Industrial Applications", heading_style))
        elements.append(Paragraph(item['applications'], body_style))
        elements.append(Spacer(1, 6))
        
        # Heat treatment
        elements.append(Paragraph("5. Heat Treatment & Tempering Guidelines", heading_style))
        elements.append(Paragraph(item['heat_treatment'], body_style))
        
        doc.build(elements)
        print(f"Generated: {filepath}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(current_dir, "raw_pdfs")
    generate_all_pdfs(out_dir)
