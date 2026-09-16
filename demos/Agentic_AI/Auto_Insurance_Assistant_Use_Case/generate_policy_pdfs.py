#!/usr/bin/env python3
"""
Generate the dummy Auto Insurance policy-wording PDFs used as the RAG corpus.

These are fictional documents for a TIBCO Flogo Agentic AI demo. They deliberately
contain the exact terms the demo prompts ask about (windshield excess, flood / water
ingress exclusion, driving other cars, territorial limits, no-claim discount
protection, roadside assistance, hire car, zero depreciation) so that the RAG
pipeline (OpenAI Vector Store -> vectorSearch) demonstrably retrieves them.

Usage:
    pip install fpdf2
    python generate_policy_pdfs.py

Output: ./policy_docs/*.pdf
"""

import os
from fpdf import FPDF

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policy_docs")

INSURER = "Meridian Auto Insurance (Demo)"
DISCLAIMER = (
    "This is a fictional specimen policy wording created solely for a software "
    "demonstration. It is not a real insurance contract and confers no cover."
)


class PolicyPDF(FPDF):
    def __init__(self, doc_title, doc_ref):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = doc_title
        self.doc_ref = doc_ref
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(20, 20, 20)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(90, 90, 90)
        half = self.epw / 2
        self.cell(half, 6, INSURER, align="L")
        self.cell(half, 6, self.doc_ref, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(20, 27, 190, 27)
        self.ln(6)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"{self.doc_title}  |  Specimen wording  |  Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def title_block(self, subtitle):
        self.set_font("Helvetica", "B", 18)
        self.multi_cell(0, 9, self.doc_title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_font("Helvetica", "I", 11)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 6, subtitle, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.multi_cell(0, 4.5, DISCLAIMER, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def section(self, heading):
        if self.get_y() > 250:
            self.add_page()
        self.ln(2)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 60, 120)
        self.multi_cell(0, 7, heading, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def subheading(self, text):
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def body(self, text):
        self.set_font("Helvetica", "", 10.5)
        self.multi_cell(0, 5.6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def bullets(self, items):
        self.set_font("Helvetica", "", 10.5)
        for it in items:
            self.multi_cell(0, 5.6, f"  -  {it}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)


def build(doc_title, doc_ref, subtitle, blocks, filename):
    pdf = PolicyPDF(doc_title, doc_ref)
    pdf.add_page()
    pdf.title_block(subtitle)
    for block in blocks:
        kind = block[0]
        if kind == "section":
            pdf.section(block[1])
        elif kind == "sub":
            pdf.subheading(block[1])
        elif kind == "body":
            pdf.body(block[1])
        elif kind == "bullets":
            pdf.bullets(block[1])
    path = os.path.join(OUT_DIR, filename)
    pdf.output(path)
    print(f"  wrote {path}")


# =====================================================================
# 1. Comprehensive Auto Policy Wording
# =====================================================================
comprehensive = [
    ("section", "1. Definitions"),
    ("body", "In this policy the following words carry the meanings shown below wherever they appear."),
    ("bullets", [
        "\"We\", \"Us\", \"Our\" means Meridian Auto Insurance, the insurer.",
        "\"You\", \"Your\" means the policyholder named in the schedule.",
        "\"Insured Vehicle\" means the motor vehicle described in the schedule by registration and VIN.",
        "\"Excess\" (also called the deductible) means the amount You must pay towards each and every claim before We pay the balance.",
        "\"Market Value\" means the cost of replacing the Insured Vehicle with one of the same make, model, age and condition immediately before the loss.",
        "\"No-Claim Discount (NCD)\" means the discount applied to Your premium for each consecutive year You do not make a claim.",
        "\"Territorial Limits\" means the geographic area within which cover applies.",
    ]),

    ("section", "2. What Is Covered"),
    ("sub", "2.1 Own Damage"),
    ("body", "We will pay for accidental loss of or damage to the Insured Vehicle, including damage caused by collision, overturning, fire, external explosion, self-ignition, lightning, burglary, housebreaking, theft, malicious acts, and while the vehicle is in transit. Payment is subject to the Own Damage excess shown in Your schedule and the vehicle's Market Value at the time of loss."),
    ("sub", "2.2 Third Party Liability"),
    ("body", "We will cover Your legal liability for death or bodily injury to third parties and for damage to third-party property arising out of an accident involving the Insured Vehicle, up to the limit shown in Your schedule. This cover is mandatory and always included."),
    ("sub", "2.3 Fire and Theft"),
    ("body", "We will pay for loss of or damage to the Insured Vehicle caused by fire, external explosion, self-ignition, lightning, burglary, housebreaking or theft, subject to the applicable excess."),
    ("sub", "2.4 Windshield and Glass"),
    ("body", "Accidental breakage of the windshield, windows and sunroof glass is covered. A separate, reduced Windshield excess (shown in Your schedule, typically USD 100) applies to glass-only claims, and a glass-only claim does NOT affect Your No-Claim Discount. If damage extends beyond the glass, the standard Own Damage excess applies instead."),
    ("sub", "2.5 Personal Accident"),
    ("body", "We provide a Personal Accident benefit to the driver for accidental death or permanent disability sustained while mounting, dismounting or travelling in the Insured Vehicle, up to the sum shown in Your schedule."),
    ("sub", "2.6 Driving Other Cars"),
    ("body", "If Your schedule shows the Driving Other Cars extension, You (the named policyholder only) are covered for Third Party Liability while driving a private car that You do not own and which is not hired to You under a hire-purchase agreement. This extension provides Third Party cover only; there is NO own-damage cover for the other car."),

    ("section", "3. Excess (Deductible)"),
    ("body", "For each and every claim You must contribute the excess amount shown in Your schedule. Where more than one excess could apply to a single incident, only the highest applicable excess is charged, except that the Windshield excess applies independently to glass-only claims. A voluntary excess, if selected, is added to the compulsory excess."),
    ("bullets", [
        "Own Damage excess: as shown in the schedule (commonly USD 500).",
        "Windshield / glass-only excess: as shown in the schedule (commonly USD 100).",
        "Young or inexperienced driver additional excess may apply as stated in the schedule.",
    ]),

    ("section", "4. General Exclusions"),
    ("body", "We will NOT pay for any of the following:"),
    ("bullets", [
        "Loss or damage caused by flood, storm surge, water ingress or submersion where the vehicle was knowingly driven through flood water. (Flood damage from an unavoidable event may be covered only if the Natural Catastrophe endorsement is shown in Your schedule.)",
        "Wear and tear, depreciation, mechanical or electrical breakdown, and gradual deterioration.",
        "Loss or damage while the vehicle is driven by any person not holding a valid licence, or by a driver under the influence of alcohol or drugs.",
        "Use of the vehicle outside the Use Class shown in the schedule (for example using a Social Only vehicle for hire or reward).",
        "Loss or damage arising from war, terrorism, nuclear risks, or while the vehicle is used in any motor sport, racing, speed testing or track day.",
        "Consequential loss, loss of use, and any reduction in the vehicle's value following repair.",
        "Damage to tyres by braking, punctures, cuts or bursts unless the vehicle is damaged at the same time.",
    ]),

    ("section", "5. No-Claim Discount (NCD)"),
    ("body", "For each consecutive year without a claim We increase Your No-Claim Discount up to the maximum scale. A claim (other than a glass-only claim or a claim where We recover our full outlay from a fully-at-fault third party) will reduce Your NCD at the next renewal."),
    ("sub", "5.1 NCD Protection"),
    ("body", "If Your schedule shows NCD Protection, You may make up to two claims in any three-year period without any reduction to Your No-Claim Discount. NCD Protection protects the discount but not the underlying premium, which may still rise. The following do NOT count against protected NCD: glass-only claims, claims fully recovered from an at-fault third party, and emergency roadside assistance."),

    ("section", "6. Territorial Limits and Use"),
    ("body", "Cover applies within the United States. Cover is extended to Canada for private touring for up to 60 days in any period of insurance. Cover does NOT apply outside these Territorial Limits unless a Foreign Use endorsement is shown in Your schedule. The Insured Vehicle must be used only within the Use Class shown in the schedule (Social Only, Social & Commuting, or Business Use)."),

    ("section", "7. Conditions"),
    ("bullets", [
        "You must take all reasonable steps to safeguard the Insured Vehicle and keep it in a roadworthy condition.",
        "You must tell Us as soon as reasonably possible about any accident, loss, theft or damage, and about any prosecution or claim from a third party.",
        "You must not admit fault or negotiate any settlement without Our written consent.",
        "You must tell Us about any change that affects this insurance, including a change of vehicle, address, use, or main driver.",
        "This policy is governed by the laws of the state shown in Your schedule.",
    ]),

    ("section", "8. How to Make a Claim"),
    ("body", "Report the incident through the policyholder assistant, Our app, or the 24-hour claims line. Provide Your policy number, the date and circumstances of the incident, and photographs where possible. See the separate Claims Procedure Guide for the documents required and the timelines that apply."),
]

# =====================================================================
# 2. Third Party Fire & Theft Wording
# =====================================================================
tpft = [
    ("section", "1. Purpose of This Cover"),
    ("body", "Third Party, Fire & Theft (TPFT) is a narrower level of cover than Comprehensive. It protects You against liability to others and against loss of the Insured Vehicle by fire or theft, but it does NOT cover accidental damage to Your own vehicle in a collision."),

    ("section", "2. What Is Covered"),
    ("bullets", [
        "Third Party Liability: death or injury to other people and damage to their property, up to the limit in Your schedule. Always included.",
        "Fire: loss of or damage to the Insured Vehicle by fire, external explosion, self-ignition or lightning, subject to the Fire & Theft excess.",
        "Theft: loss of or damage to the Insured Vehicle by burglary, housebreaking or theft, subject to the Fire & Theft excess.",
        "Emergency legal defence costs following an insured incident, where We agree in advance.",
    ]),

    ("section", "3. What Is NOT Covered"),
    ("body", "Because this is not Comprehensive cover, the following are excluded (this list is in addition to the General Exclusions):"),
    ("bullets", [
        "Accidental damage to Your own vehicle from a collision, overturning or vandalism. (This is only covered under a Comprehensive policy.)",
        "Windshield and glass breakage on a standalone basis (no glass cover under TPFT).",
        "Personal Accident benefit for the driver (available under Comprehensive only).",
        "Flood, storm and water-ingress damage to Your own vehicle.",
        "Any add-on such as Zero Depreciation, Hire Car or Roadside Assistance unless separately endorsed.",
    ]),

    ("section", "4. General Exclusions"),
    ("bullets", [
        "Driving without a valid licence or while under the influence of alcohol or drugs.",
        "Use outside the Use Class shown in the schedule, or for racing, speed testing or track use.",
        "War, terrorism and nuclear risks.",
        "Wear, tear, depreciation and mechanical or electrical breakdown.",
        "Vehicles knowingly driven through flood water.",
    ]),

    ("section", "5. Excess"),
    ("body", "A Fire & Theft excess (shown in Your schedule) applies to each fire or theft claim. There is no Own Damage excess because own accidental damage is not covered."),

    ("section", "6. No-Claim Discount and Territorial Limits"),
    ("body", "The No-Claim Discount scale and the Territorial Limits (United States, with Canada touring up to 60 days) apply exactly as set out in the Comprehensive wording. A fire or theft claim will reduce Your NCD at renewal unless NCD Protection is shown in Your schedule."),

    ("section", "7. Upgrading to Comprehensive"),
    ("body", "You may upgrade to Comprehensive cover at any time to add own-damage protection, windshield cover, personal accident benefit and eligibility for add-ons. Contact Us or ask the policyholder assistant to arrange a callback with a licensed advisor."),
]

# =====================================================================
# 3. Auto Endorsements and Add-Ons
# =====================================================================
addons = [
    ("section", "About Endorsements"),
    ("body", "Endorsements (add-ons) extend or vary the base policy. An endorsement applies only when it is listed in Your schedule and the additional premium has been paid. Where an endorsement conflicts with the base wording, the endorsement prevails for the matter it covers."),

    ("section", "1. Roadside Assistance"),
    ("body", "Provides 24-hour emergency help if the Insured Vehicle becomes immobilised by breakdown, flat battery, flat tyre, lost keys, or running out of fuel."),
    ("bullets", [
        "Roadside repair at the scene where possible.",
        "Recovery and towing to the nearest approved repairer if repair at the scene is not possible.",
        "Onward travel or overnight accommodation assistance after a covered breakdown away from home.",
        "Using Roadside Assistance does NOT count as a claim and does not affect Your No-Claim Discount.",
    ]),

    ("section", "2. Windshield / Glass Cover"),
    ("body", "Enhances the base glass cover. Repair of a chip is provided with no excess when carried out by an approved repairer; full glass replacement is subject to the reduced Windshield excess shown in Your schedule. Glass-only claims never affect Your No-Claim Discount."),

    ("section", "3. Hire Car (Courtesy Car)"),
    ("body", "If the Insured Vehicle cannot be driven following a covered claim, or is being repaired by an approved repairer, We will provide a hire car of a similar class."),
    ("bullets", [
        "Provided for up to the number of days shown in Your schedule (commonly up to 14 days).",
        "Available only following a valid, covered own-damage, fire or theft claim.",
        "Not available for routine servicing, mechanical breakdown, or glass-only repairs.",
        "Fuel, tolls and any additional driver charges on the hire car are Your responsibility.",
    ]),

    ("section", "4. Zero Depreciation (Bumper-to-Bumper)"),
    ("body", "At the time of a covered own-damage claim We normally deduct depreciation on replaced parts such as plastic, rubber and fibre-glass components. With the Zero Depreciation endorsement We waive that depreciation deduction, so You receive the full cost of replacement parts, subject to Your excess."),
    ("bullets", [
        "Typically available for vehicles up to five model years old.",
        "A limited number of Zero Depreciation claims may be made per period of insurance, as stated in the schedule.",
        "Consumables and normal wear-and-tear items remain excluded.",
    ]),

    ("section", "5. NCD Protection"),
    ("body", "Allows up to two claims in any three-year period without reducing Your No-Claim Discount. It protects the discount only; the base premium may still change at renewal. Glass-only claims, roadside assistance and claims fully recovered from an at-fault third party are never counted."),

    ("section", "6. Natural Catastrophe (Flood and Storm)"),
    ("body", "Extends Own Damage cover to include loss or damage caused by flood, storm, hurricane, hailstorm and water ingress from an unavoidable natural event. This endorsement does NOT cover damage where the vehicle was knowingly driven through flood water, which remains excluded under all covers."),

    ("section", "7. Personal Belongings"),
    ("body", "Covers accidental loss of or damage to personal effects in the Insured Vehicle following a covered incident, up to the modest limit shown in Your schedule. Money, documents, and electronic equipment used for business are excluded."),
]

# =====================================================================
# 4. Claims Procedure Guide
# =====================================================================
claims_guide = [
    ("section", "1. Immediately After an Incident"),
    ("bullets", [
        "Make sure everyone is safe and call emergency services if anyone is injured.",
        "Do not admit fault or agree to pay for anything at the scene.",
        "Take photographs of all vehicles, the damage, the location, and any road signs or signals.",
        "Exchange names, contact details, vehicle registrations and insurance details with any other party.",
        "Note the date, time, weather and a brief description of what happened.",
    ]),

    ("section", "2. How to File a Claim"),
    ("body", "You can start a claim in any of these ways. The fastest is through the policyholder assistant, which can file the claim for You once You confirm the details."),
    ("bullets", [
        "Ask the policyholder assistant to file a claim and provide the incident date, type and a short description.",
        "Use Our mobile app or customer portal.",
        "Call the 24-hour claims line shown on Your schedule.",
    ]),
    ("body", "When You file, have Your policy number ready (for example POL-AUTO-100001). We will create a claim reference (format CLM-YYYY-NNNN) that You can quote to check progress at any time."),

    ("section", "3. Documents Required"),
    ("bullets", [
        "Your policy number and the driver's licence of the person driving at the time.",
        "Photographs of the damage and, where relevant, the scene.",
        "A police report reference for theft, malicious damage, or any incident involving injury.",
        "Repair estimate(s) from an approved repairer where available.",
        "For theft: the vehicle keys and any tracking/immobiliser details.",
    ]),

    ("section", "4. Timelines"),
    ("bullets", [
        "Notify Us as soon as reasonably possible, and within 30 days of the incident at the latest.",
        "Acknowledgement of a new claim: within 1 business day.",
        "Assessment / surveyor allocation for own-damage claims: within 3 business days.",
        "Settlement of a straightforward, fully-documented claim: typically within 10 business days of approval.",
        "Theft claims are held for a mandatory investigation period (commonly up to 30 days) before settlement.",
    ]),

    ("section", "5. Claim Status Meanings"),
    ("bullets", [
        "Submitted: We have received Your claim and created a reference.",
        "Under Review: We are assessing liability, documents and the repair estimate.",
        "Approved: The claim is accepted; repair or payment is being arranged.",
        "Settled: Payment has been made or repairs completed.",
        "Rejected: The claim falls outside cover; We will explain why in writing.",
    ]),

    ("section", "6. What Can Void or Reduce a Claim"),
    ("bullets", [
        "Giving false or incomplete information, or staging or exaggerating a loss.",
        "Driving without a valid licence or while under the influence of alcohol or drugs.",
        "Using the vehicle outside the Use Class shown in the schedule.",
        "Knowingly driving through flood water (see the flood exclusion).",
        "Failing to notify Us within the required time or not cooperating with the assessment.",
        "Carrying out repairs before We have assessed the damage, without Our agreement.",
    ]),

    ("section", "7. The Excess You Pay"),
    ("body", "When a claim is settled You pay the excess shown in Your schedule and We pay the balance up to the covered limit. Glass-only claims attract the lower Windshield excess and do not affect Your No-Claim Discount. If You disagree with a decision You may ask for it to be reviewed through Our complaints process."),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Generating policy PDFs into", OUT_DIR)
    build(
        "Comprehensive Auto Policy Wording",
        "Ref: MAI-COMP-2026",
        "Full cover: own damage, third party, fire, theft, windshield and personal accident.",
        comprehensive,
        "Comprehensive_Auto_Policy_Wording.pdf",
    )
    build(
        "Third Party, Fire & Theft Wording",
        "Ref: MAI-TPFT-2026",
        "Liability to others plus fire and theft of your vehicle. No own-damage collision cover.",
        tpft,
        "Third_Party_Fire_Theft_Wording.pdf",
    )
    build(
        "Auto Endorsements and Add-Ons",
        "Ref: MAI-ADDON-2026",
        "Optional extensions: roadside assistance, windshield, hire car, zero depreciation and more.",
        addons,
        "Auto_Endorsements_and_AddOns.pdf",
    )
    build(
        "Claims Procedure Guide",
        "Ref: MAI-CLAIMS-2026",
        "How to file a claim, the documents needed, timelines, status meanings and what voids a claim.",
        claims_guide,
        "Claims_Procedure_Guide.pdf",
    )
    print("Done. 4 PDFs generated.")


if __name__ == "__main__":
    main()
