"""
Prepare Step-2 cross-domain expansion artifacts for LexEval-India.

Outputs:
1) evaluation/lexeval_india_cross_domain_queries.csv (exact 100 rows)
2) evaluation/ground_truth_verified_393.xlsx (293 existing + 100 new)
3) data/cross_domain_acts/*.txt (plain-text act sources for loader)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evaluation"
DATA_DIR = ROOT / "data" / "cross_domain_acts"


def build_queries() -> list[dict]:
    rows = []

    def add(domain: str, act: str, section: str, query_text: str):
        rows.append(
            {
                "domain": domain,
                "act_name": act,
                "query_text": query_text,
                "expected_section": str(section),
            }
        )

    # Civil Law (40)
    act = "Code of Civil Procedure 1908"
    add("Civil Law", act, "9", "Under CPC Section 9, when can a civil court entertain a suit of civil nature?")
    add("Civil Law", act, "10", "What is the test for stay of suit under Section 10 CPC?")
    add("Civil Law", act, "11", "What are the ingredients of res judicata under Section 11 CPC?")
    add("Civil Law", act, "20", "Under Section 20 CPC, how is territorial jurisdiction determined for filing a suit?")
    add("Civil Law", act, "24", "When can transfer of suit be ordered by a High Court under Section 24 CPC?")
    add("Civil Law", act, "26", "What does Section 26 CPC require at the stage of institution of suits?")
    add("Civil Law", act, "80", "Is a prior notice mandatory before suing Government under Section 80 CPC?")
    add("Civil Law", act, "96", "What is the scope of first appeal under Section 96 CPC?")
    add("Civil Law", act, "100", "When is a second appeal maintainable under Section 100 CPC?")
    add("Civil Law", act, "115", "In what circumstances can revision be invoked under Section 115 CPC?")

    act = "Specific Relief Act 1963"
    add("Civil Law", act, "10", "Under Section 10 of the Specific Relief Act, when can specific performance be enforced?")
    add("Civil Law", act, "11", "What obligation is covered by Section 11 of the Specific Relief Act for trustees?")
    add("Civil Law", act, "14", "Which contracts are not specifically enforceable under Section 14 of the Specific Relief Act?")
    add("Civil Law", act, "16", "What personal bars to relief are listed in Section 16 of the Specific Relief Act?")
    add("Civil Law", act, "19", "Against whom can specific performance be enforced under Section 19 of the Specific Relief Act?")
    add("Civil Law", act, "20", "What discretion does the court retain under Section 20 of the Specific Relief Act?")
    add("Civil Law", act, "31", "When can a written instrument be cancelled under Section 31 of the Specific Relief Act?")
    add("Civil Law", act, "34", "What is required to seek declaratory relief under Section 34 of the Specific Relief Act?")
    add("Civil Law", act, "36", "What does Section 36 of the Specific Relief Act say about preventive relief?")
    add("Civil Law", act, "38", "When is a perpetual injunction granted under Section 38 of the Specific Relief Act?")

    act = "Transfer of Property Act 1882"
    add("Civil Law", act, "5", "How is transfer of property defined under Section 5 of the Transfer of Property Act?")
    add("Civil Law", act, "6", "What kinds of property cannot be transferred under Section 6 of the Transfer of Property Act?")
    add("Civil Law", act, "8", "What rights pass to the transferee under Section 8 of the Transfer of Property Act?")
    add("Civil Law", act, "52", "What is the doctrine of lis pendens under Section 52 of the Transfer of Property Act?")
    add("Civil Law", act, "53A", "What protection does Section 53A of the Transfer of Property Act give under part performance?")
    add("Civil Law", act, "54", "How does Section 54 of the Transfer of Property Act distinguish sale from contract for sale?")
    add("Civil Law", act, "55", "What are seller and buyer duties under Section 55 of the Transfer of Property Act?")
    add("Civil Law", act, "58", "What forms of mortgage are recognised under Section 58 of the Transfer of Property Act?")
    add("Civil Law", act, "105", "How is lease defined under Section 105 of the Transfer of Property Act?")
    add("Civil Law", act, "111", "On what grounds can lease be determined under Section 111 of the Transfer of Property Act?")

    act = "Limitation Act 1963"
    add("Civil Law", act, "3", "What is the court's duty under Section 3 of the Limitation Act when a suit is time-barred?")
    add("Civil Law", act, "4", "How does Section 4 of the Limitation Act operate when limitation ends on a court holiday?")
    add("Civil Law", act, "5", "When can delay be condoned under Section 5 of the Limitation Act?")
    add("Civil Law", act, "6", "What disability is contemplated under Section 6 of the Limitation Act?")
    add("Civil Law", act, "12", "How is time excluded under Section 12 of the Limitation Act for obtaining copies?")
    add("Civil Law", act, "14", "What conditions must be met for exclusion of time under Section 14 of the Limitation Act?")
    add("Civil Law", act, "17", "How does fraud affect limitation under Section 17 of the Limitation Act?")
    add("Civil Law", act, "18", "What is the effect of acknowledgment under Section 18 of the Limitation Act?")
    add("Civil Law", act, "19", "What is the effect of part payment under Section 19 of the Limitation Act?")
    add("Civil Law", act, "22", "How does Section 22 of the Limitation Act apply to continuing breaches?")

    # Corporate Law (30)
    act = "Companies Act 2013"
    add("Corporate Law", act, "2", "Under Section 2 of the Companies Act, what is meant by a private company?")
    add("Corporate Law", act, "7", "What documents are mandatory for incorporation under Section 7 of the Companies Act?")
    add("Corporate Law", act, "12", "What does Section 12 of the Companies Act require regarding registered office?")
    add("Corporate Law", act, "73", "When can a company accept deposits under Section 73 of the Companies Act?")
    add("Corporate Law", act, "92", "What is the annual return requirement under Section 92 of the Companies Act?")
    add("Corporate Law", act, "134", "What does Section 134 of the Companies Act require in Board's report?")
    add("Corporate Law", act, "135", "When does CSR obligation trigger under Section 135 of the Companies Act?")
    add("Corporate Law", act, "139", "How are auditors appointed under Section 139 of the Companies Act?")
    add("Corporate Law", act, "164", "What are director disqualifications under Section 164 of the Companies Act?")
    add("Corporate Law", act, "248", "When can Registrar remove company name under Section 248 of the Companies Act?")

    act = "Arbitration and Conciliation Act 1996"
    add("Corporate Law", act, "7", "What constitutes a valid arbitration agreement under Section 7 of the Arbitration Act?")
    add("Corporate Law", act, "8", "When must a judicial authority refer parties to arbitration under Section 8?")
    add("Corporate Law", act, "9", "What interim measures can be sought from court under Section 9 of the Arbitration Act?")
    add("Corporate Law", act, "11", "How is appointment of arbitrators handled under Section 11 of the Arbitration Act?")
    add("Corporate Law", act, "12", "What disclosure requirements are imposed on arbitrators under Section 12?")
    add("Corporate Law", act, "16", "What is the kompetenz-kompetenz rule under Section 16 of the Arbitration Act?")
    add("Corporate Law", act, "17", "What interim powers does the arbitral tribunal have under Section 17?")
    add("Corporate Law", act, "34", "On what grounds can an arbitral award be set aside under Section 34?")
    add("Corporate Law", act, "36", "When does an arbitral award become enforceable under Section 36?")
    add("Corporate Law", act, "37", "Which orders are appealable under Section 37 of the Arbitration Act?")

    act = "Negotiable Instruments Act 1881"
    add("Corporate Law", act, "138", "What are the essential ingredients of offence under Section 138 NI Act?")
    add("Corporate Law", act, "139", "What presumption does Section 139 NI Act create in cheque bounce cases?")
    add("Corporate Law", act, "140", "What defences are barred under Section 140 NI Act?")
    add("Corporate Law", act, "141", "How is vicarious liability fixed for companies under Section 141 NI Act?")
    add("Corporate Law", act, "142", "What are the cognizance conditions under Section 142 NI Act?")
    add("Corporate Law", act, "143", "How does Section 143 NI Act provide summary trial for cheque dishonour?")
    add("Corporate Law", act, "143A", "When can interim compensation be awarded under Section 143A NI Act?")
    add("Corporate Law", act, "145", "How is evidence by affidavit treated under Section 145 NI Act?")
    add("Corporate Law", act, "147", "Is compounding permitted under Section 147 NI Act?")
    add("Corporate Law", act, "148", "What power does appellate court have under Section 148 NI Act?")

    # Family Law (30)
    act = "Hindu Marriage Act 1955"
    add("Family Law", act, "5", "What are conditions for a valid Hindu marriage under Section 5 HMA?")
    add("Family Law", act, "7", "What ceremonies are recognised under Section 7 HMA for solemnization?")
    add("Family Law", act, "8", "What is the legal effect of registration under Section 8 HMA?")
    add("Family Law", act, "9", "When can restitution of conjugal rights be sought under Section 9 HMA?")
    add("Family Law", act, "10", "What is judicial separation under Section 10 HMA?")
    add("Family Law", act, "12", "On what grounds is a marriage voidable under Section 12 HMA?")
    add("Family Law", act, "13", "What are the divorce grounds under Section 13 HMA?")
    add("Family Law", act, "13B", "What statutory conditions apply to mutual consent divorce under Section 13B HMA?")
    add("Family Law", act, "24", "When can interim maintenance be granted under Section 24 HMA?")
    add("Family Law", act, "25", "How is permanent alimony dealt with under Section 25 HMA?")

    act = "Protection of Women from Domestic Violence Act 2005"
    add("Family Law", act, "2", "Who is an aggrieved person under Section 2 of the Domestic Violence Act?")
    add("Family Law", act, "3", "How is domestic violence defined under Section 3 of the Domestic Violence Act?")
    add("Family Law", act, "12", "How is an application to Magistrate made under Section 12 of the Domestic Violence Act?")
    add("Family Law", act, "17", "What residence right is protected under Section 17 of the Domestic Violence Act?")
    add("Family Law", act, "18", "What protection orders can be passed under Section 18 of the Domestic Violence Act?")
    add("Family Law", act, "19", "What residence orders are available under Section 19 of the Domestic Violence Act?")
    add("Family Law", act, "20", "What monetary relief can be ordered under Section 20 of the Domestic Violence Act?")
    add("Family Law", act, "22", "When can compensation be granted under Section 22 of the Domestic Violence Act?")
    add("Family Law", act, "23", "What interim and ex parte orders are allowed under Section 23 of the Domestic Violence Act?")
    add("Family Law", act, "31", "What is the consequence of breach of protection order under Section 31 of the Domestic Violence Act?")

    act = "Protection of Children from Sexual Offences Act 2012"
    add("Family Law", act, "2", "How does Section 2 POCSO define child and key terms?")
    add("Family Law", act, "3", "What acts amount to penetrative sexual assault under Section 3 POCSO?")
    add("Family Law", act, "4", "What is punishment for penetrative sexual assault under Section 4 POCSO?")
    add("Family Law", act, "5", "When does penetrative sexual assault become aggravated under Section 5 POCSO?")
    add("Family Law", act, "7", "What is sexual assault under Section 7 POCSO?")
    add("Family Law", act, "8", "What is punishment for sexual assault under Section 8 POCSO?")
    add("Family Law", act, "19", "What mandatory reporting duty is imposed by Section 19 POCSO?")
    add("Family Law", act, "24", "How must police record child statement under Section 24 POCSO?")
    add("Family Law", act, "29", "What presumption is created under Section 29 POCSO during trial?")
    add("Family Law", act, "33", "What are Special Court powers and child safeguards under Section 33 POCSO?")

    assert len(rows) == 100
    for i, row in enumerate(rows, start=294):
        row["query_id"] = f"Q{i:03d}"
    return rows


def build_section_sources() -> dict[str, dict]:
    """Compact plain-text sources for section-level ingestion."""
    return {
        "Code of Civil Procedure 1908": {
            "short_name": "CPC",
            "sections": {
                "9": ("Jurisdiction of civil courts", "Civil courts shall try all suits of a civil nature except suits expressly or impliedly barred."),
                "10": ("Stay of suit", "No court shall proceed with trial of a suit where the matter in issue is directly and substantially in issue in a previously instituted suit between the same parties."),
                "11": ("Res judicata", "No court shall try any suit or issue in which the matter directly and substantially in issue has been directly and substantially in issue in a former suit between the same parties and finally decided."),
                "20": ("Institution where defendants reside or cause arises", "Subject to statutory limitations, a suit may be instituted where defendant resides or carries on business, or where cause of action wholly or partly arises."),
                "24": ("General power of transfer and withdrawal", "High Court or District Court may transfer, withdraw, and try suits, appeals, or other proceedings pending in subordinate courts."),
                "26": ("Institution of suits", "Every suit shall be instituted by presentation of plaint or in such other manner as may be prescribed."),
                "80": ("Notice", "No suit shall be instituted against Government or public officer for acts done in official capacity unless prior notice is delivered in the prescribed manner."),
                "96": ("Appeal from original decree", "Save where otherwise expressly provided, an appeal shall lie from every decree passed by any court exercising original jurisdiction."),
                "100": ("Second appeal", "Second appeal lies to High Court only if the case involves a substantial question of law."),
                "115": ("Revision", "High Court may revise orders of subordinate courts where jurisdictional error is shown and no appeal lies."),
            },
        },
        "Specific Relief Act 1963": {
            "short_name": "SRA",
            "sections": {
                "10": ("Specific performance in respect of contracts", "Specific performance may be enforced subject to provisions of Chapter II and where statutory conditions are met."),
                "11": ("Cases where specific performance enforceable", "Contracts connected with trust obligations may be specifically enforced."),
                "14": ("Contracts not specifically enforceable", "Contracts dependent on personal qualifications, determinable contracts, and contracts requiring continuous supervision are generally not specifically enforceable."),
                "16": ("Personal bars to relief", "Specific performance cannot be enforced in favor of a person who fails to aver and prove readiness and willingness, among other bars."),
                "19": ("Relief against parties and persons claiming under them", "Specific performance may be enforced against either party and certain transferees except bona fide transferee for value without notice."),
                "20": ("Substituted performance", "A party suffering breach may obtain substituted performance under statutory conditions and may then be barred from specific performance for same breach."),
                "31": ("When cancellation may be ordered", "A written instrument may be adjudged void or voidable and ordered delivered up and cancelled where serious injury is apprehended."),
                "34": ("Discretion of court as to declaration", "Any person entitled to legal character or right as to property may seek declaration where defendant denies or is interested to deny title."),
                "36": ("Preventive relief", "Preventive relief is granted at court discretion by injunction, temporary or perpetual."),
                "38": ("Perpetual injunction", "Perpetual injunction may be granted to prevent breach of obligation existing in favor of plaintiff."),
            },
        },
        "Transfer of Property Act 1882": {
            "short_name": "TPA",
            "sections": {
                "5": ("Transfer of property defined", "Transfer of property means an act by which a living person conveys property in present or future to one or more living persons or to himself and one or more other living persons."),
                "6": ("What may be transferred", "Property of any kind may be transferred except interests expressly excluded, including mere right to sue and other statutory exceptions."),
                "8": ("Operation of transfer", "A transfer passes forthwith to transferee all interest transferor is capable of passing with legal incidents unless contrary intention appears."),
                "52": ("Transfer pending suit relating thereto", "During pendency of litigation, property cannot be transferred to affect rights of other party under decree except under authority of court."),
                "53A": ("Part performance", "Where transferee has taken possession in part performance and is willing to perform contract, transferor is debarred from enforcing rights inconsistent with contract."),
                "54": ("Sale defined", "Sale is transfer of ownership in exchange for price paid or promised; contract for sale by itself does not create interest in or charge on property."),
                "55": ("Rights and liabilities of buyer and seller", "Section 55 sets reciprocal duties and rights of seller and buyer before and after completion of sale."),
                "58": ("Mortgage defined", "Mortgage is transfer of interest in specific immovable property to secure payment of money advanced, existing or future debt, or performance of engagement."),
                "105": ("Lease defined", "Lease is transfer of right to enjoy immovable property for certain time in consideration of price paid or promised, money, share of crops, service, or other value."),
                "111": ("Determination of lease", "A lease determines by efflux of time, happening of event, termination of lessor's interest, surrender, forfeiture, or notice to quit."),
            },
        },
        "Limitation Act 1963": {
            "short_name": "LA",
            "sections": {
                "3": ("Bar of limitation", "Every suit, appeal, and application instituted after prescribed period shall be dismissed although limitation has not been set up as defence."),
                "4": ("Expiry when court closed", "If prescribed period expires when court is closed, filing on reopening day is treated as within limitation."),
                "5": ("Extension in certain cases", "Delay in appeal or application may be condoned on sufficient cause, except where statute excludes such condonation."),
                "6": ("Legal disability", "Where person entitled is under disability at commencement, suit or application may be instituted within same period after disability ceases."),
                "12": ("Exclusion of time in legal proceedings", "In computing limitation, day from which period is reckoned and time required for obtaining copies may be excluded."),
                "14": ("Exclusion of time of proceeding bona fide in court without jurisdiction", "Time spent with due diligence in bona fide prior proceeding in wrong forum may be excluded."),
                "17": ("Effect of fraud or mistake", "Where suit is based on fraud or right is concealed by fraud, period begins when fraud is discovered or could with reasonable diligence be discovered."),
                "18": ("Effect of acknowledgment in writing", "Fresh period of limitation starts from acknowledgment signed by party before expiry of prescribed period."),
                "19": ("Effect of payment on account of debt or interest", "Fresh period starts when payment is made before expiry and acknowledged in writing signed by payer."),
                "22": ("Continuing breaches and torts", "For continuing breach or tort, fresh limitation period begins to run at every moment while breach or tort continues."),
            },
        },
        "Companies Act 2013": {
            "short_name": "CA",
            "sections": {
                "2": ("Definitions", "Section 2 defines key terms including company, private company, public company, and related expressions used in the Act."),
                "7": ("Incorporation of company", "Memorandum, articles, declarations, and prescribed particulars must be filed for incorporation; false information attracts consequences."),
                "12": ("Registered office", "Company must have registered office capable of receiving communications and must verify and disclose the same in prescribed manner."),
                "73": ("Prohibition on acceptance of deposits from public", "Company shall not invite, accept, or renew deposits from public except in manner provided by the Act and rules."),
                "92": ("Annual return", "Every company shall prepare annual return in prescribed form containing particulars as on close of financial year."),
                "134": ("Financial statement and Board's report", "Board's report and financial statements must be approved and signed as required; directors' responsibility statement is mandatory."),
                "135": ("Corporate social responsibility", "Specified companies meeting net worth, turnover, or net profit thresholds must constitute CSR committee and spend prescribed amount."),
                "139": ("Appointment of auditors", "Every company shall appoint an individual or firm as auditor at first AGM for prescribed tenure, subject to ratification and eligibility conditions."),
                "164": ("Disqualifications for appointment of director", "Section 164 lists personal and compliance-based grounds on which a person is disqualified from being appointed as director."),
                "248": ("Power of Registrar to remove name", "Registrar may remove company name from register where statutory grounds exist including failure to commence business or carry on operations."),
            },
        },
        "Arbitration and Conciliation Act 1996": {
            "short_name": "ACA",
            "sections": {
                "7": ("Arbitration agreement", "Arbitration agreement is an agreement by parties to submit disputes to arbitration and must be in writing in forms recognised by the Act."),
                "8": ("Power to refer parties to arbitration", "Judicial authority shall refer parties to arbitration if action is brought in a matter covered by arbitration agreement and conditions are satisfied."),
                "9": ("Interim measures by court", "Court may grant interim measures before, during, or after arbitral proceedings but before enforcement in accordance with Section 36."),
                "11": ("Appointment of arbitrators", "Parties are free to agree appointment procedure; failing agreement, court or designated authority may appoint under statute."),
                "12": ("Grounds for challenge", "Prospective arbitrator must disclose circumstances likely to give rise to justifiable doubts as to independence or impartiality."),
                "16": ("Competence of arbitral tribunal", "Arbitral tribunal may rule on its own jurisdiction including objections with respect to existence or validity of arbitration agreement."),
                "17": ("Interim measures ordered by arbitral tribunal", "Arbitral tribunal may order interim measures and such orders are enforceable as if they were orders of court."),
                "34": ("Application for setting aside arbitral award", "An arbitral award may be set aside only on grounds specified in Section 34 within prescribed limitation period."),
                "36": ("Enforcement", "Where time for setting aside has expired or challenge is refused, award shall be enforced as if it were a decree of the court."),
                "37": ("Appealable orders", "Appeals lie only from specific orders under Section 37, including certain orders under Sections 9, 34, and 17."),
            },
        },
        "Negotiable Instruments Act 1881": {
            "short_name": "NIA",
            "sections": {
                "138": ("Dishonour of cheque for insufficiency", "Where cheque is returned unpaid for insufficiency and drawer fails to pay within statutory notice period, offence under Section 138 is made out."),
                "139": ("Presumption in favour of holder", "It shall be presumed unless contrary is proved that holder received cheque for discharge of debt or liability."),
                "140": ("Defence not allowed", "In prosecution under Section 138, it is not a defence that drawer had no reason to believe cheque may be dishonoured at presentation."),
                "141": ("Offences by companies", "Persons in charge of and responsible to company for conduct of business are deemed guilty, subject to statutory defences."),
                "142": ("Cognizance of offences", "Court takes cognizance only on complaint by payee or holder in due course filed within prescribed limitation before competent magistrate."),
                "143": ("Power of court to try cases summarily", "Offences under Chapter XVII may be tried summarily and endeavour shall be made to conclude trial expeditiously."),
                "143A": ("Power to direct interim compensation", "Court trying offence under Section 138 may order drawer to pay interim compensation up to prescribed proportion of cheque amount."),
                "145": ("Evidence on affidavit", "Complainant evidence may be given by affidavit and may be read in evidence, subject to court summoning and examination."),
                "147": ("Offences to be compoundable", "Notwithstanding CrPC, every offence punishable under this Act shall be compoundable."),
                "148": ("Power of appellate court", "In appeal against conviction under Section 138, appellate court may order deposit of minimum percentage of fine or compensation awarded."),
            },
        },
        "Hindu Marriage Act 1955": {
            "short_name": "HMA",
            "sections": {
                "5": ("Conditions for a Hindu marriage", "Marriage may be solemnized between two Hindus if statutory conditions regarding monogamy, mental capacity, age, and prohibited relationships are fulfilled."),
                "7": ("Ceremonies", "A Hindu marriage may be solemnized in accordance with customary rites and ceremonies of either party; saptapadi completes marriage where applicable."),
                "8": ("Registration", "State may provide for registration of Hindu marriages; failure to register does not by itself affect validity of marriage."),
                "9": ("Restitution of conjugal rights", "Where one spouse withdraws from society of other without reasonable excuse, aggrieved party may seek decree for restitution of conjugal rights."),
                "10": ("Judicial separation", "Either spouse may seek judicial separation on grounds specified in statute, suspending obligation to cohabit while marriage subsists."),
                "12": ("Voidable marriages", "A marriage may be annulled as voidable on grounds including impotence, lack of valid consent, or pregnancy by another at marriage time."),
                "13": ("Divorce", "Any marriage solemnized may be dissolved by decree of divorce on statutory grounds enumerated in Section 13."),
                "13B": ("Divorce by mutual consent", "Parties living separately for prescribed period and unable to live together may jointly present petition for dissolution by mutual consent."),
                "24": ("Maintenance pendente lite", "Court may order interim maintenance and litigation expenses where applicant has no independent income sufficient for support and proceeding costs."),
                "25": ("Permanent alimony", "Court may grant permanent alimony and maintenance at decree stage or subsequently, considering income, conduct, and circumstances."),
            },
        },
        "Protection of Women from Domestic Violence Act 2005": {
            "short_name": "PWDVA",
            "sections": {
                "2": ("Definitions", "Section 2 defines key terms including aggrieved person, domestic relationship, respondent, shared household, and protection officer."),
                "3": ("Definition of domestic violence", "Domestic violence includes physical, sexual, verbal, emotional, and economic abuse and related conduct as described in Section 3."),
                "12": ("Application to Magistrate", "Aggrieved person, Protection Officer, or other authorised person may present application to Magistrate seeking one or more reliefs under Act."),
                "17": ("Right to reside", "Every woman in domestic relationship has right to reside in shared household whether or not she has title or beneficial interest."),
                "18": ("Protection orders", "Magistrate may pass protection order prohibiting respondent from committing, aiding, or communicating acts of domestic violence."),
                "19": ("Residence orders", "Magistrate may pass residence orders including restraining dispossession, directing respondent to remove himself, or securing alternate accommodation."),
                "20": ("Monetary reliefs", "Magistrate may direct monetary relief for loss of earnings, medical expenses, property damage, and maintenance."),
                "22": ("Compensation orders", "Magistrate may direct respondent to pay compensation and damages for injuries including mental torture and emotional distress."),
                "23": ("Interim and ex parte orders", "Magistrate may grant interim or ex parte relief on prima facie satisfaction based on affidavit and material on record."),
                "31": ("Penalty for breach", "Breach of protection order or interim protection order is an offence and is punishable under Section 31."),
            },
        },
        "Protection of Children from Sexual Offences Act 2012": {
            "short_name": "POCSO",
            "sections": {
                "2": ("Definitions", "Section 2 defines child and key expressions used in the Act."),
                "3": ("Penetrative sexual assault", "Section 3 specifies acts constituting penetrative sexual assault on a child."),
                "4": ("Punishment for penetrative sexual assault", "Section 4 prescribes punishment for penetrative sexual assault under Section 3."),
                "5": ("Aggravated penetrative sexual assault", "Section 5 sets out aggravated circumstances where penetrative sexual assault is treated as aggravated offence."),
                "7": ("Sexual assault", "Section 7 defines sexual assault involving sexual intent and physical contact without penetration."),
                "8": ("Punishment for sexual assault", "Section 8 prescribes punishment for sexual assault as defined in Section 7."),
                "19": ("Reporting offences", "Any person having apprehension or knowledge of offence under POCSO has duty to report to Special Juvenile Police Unit or local police."),
                "24": ("Recording statement of child", "Statement of child shall be recorded at residence or place of choice in child-friendly manner by police officer not below prescribed rank."),
                "29": ("Presumption", "Where person is prosecuted for specified offences under the Act, Special Court shall presume commission unless contrary is proved."),
                "33": ("Procedure and powers of Special Court", "Special Court shall ensure child-friendly trial process and may take measures to protect dignity, privacy, and welfare of child."),
            },
        },
    }


def write_query_csv(rows: list[dict], csv_path: Path):
    out = pd.DataFrame(rows)[["query_id", "domain", "act_name", "query_text", "expected_section"]]
    out.to_csv(csv_path, index=False)
    print(f"[ok] wrote {len(out)} rows -> {csv_path}")


def write_ground_truth_393(rows: list[dict], gt_in: Path, gt_out: Path):
    gt = pd.read_excel(gt_in, sheet_name="Ground Truth Dataset")
    if "domain" not in gt.columns:
        gt["domain"] = "Criminal Law"

    new_rows = []
    for r in rows:
        new_rows.append(
            {
                "query_id": r["query_id"],
                "category": "Section Lookup",
                "query_text": r["query_text"],
                "correct_answer_summary": f"Refer {r['act_name']} Section {r['expected_section']}.",
                "correct_act": r["act_name"],
                "correct_section": str(r["expected_section"]),
                "correct_citation": f"{r['act_name']} Section {r['expected_section']}",
                "amendment_applies": "no",
                "amendment_detail": "",
                "overruling_applies": "no",
                "overruled_by": "",
                "bns_bnss_transition_applies": "no",
                "bns_bnss_detail": "",
                "difficulty_level": "medium",
                "verified_by_lawyer": "cross-domain synthetic set (pending lawyer verification)",
                "lawyer_notes": "Added for cross-domain benchmark expansion.",
                "domain": r["domain"],
            }
        )

    add_df = pd.DataFrame(new_rows)
    merged = pd.concat([gt, add_df], ignore_index=True)

    # Keep deterministic order by numeric query id
    merged["_qnum"] = merged["query_id"].astype(str).str.extract(r"(\d+)").astype(int)
    merged = merged.sort_values("_qnum").drop(columns=["_qnum"]).reset_index(drop=True)

    with pd.ExcelWriter(gt_out, engine="openpyxl") as writer:
        merged.to_excel(writer, sheet_name="Ground Truth Dataset", index=False)

    print(f"[ok] wrote ground truth -> {gt_out} ({len(merged)} rows)")


def write_plain_text_sources(section_sources: dict[str, dict], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for act_name, payload in section_sources.items():
        short = payload["short_name"]
        sections = payload["sections"]
        fp = out_dir / f"{short}.txt"
        lines = [
            f"ACT_NAME: {act_name}",
            f"SHORT_NAME: {short}",
            "",
        ]
        for sec, (title, text) in sections.items():
            lines.append(f"[SECTION {sec}] {title}")
            lines.append(text)
            lines.append("")
        fp.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        print(f"[ok] wrote source text -> {fp}")


def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    rows = build_queries()
    section_sources = build_section_sources()

    write_query_csv(rows, EVAL_DIR / "lexeval_india_cross_domain_queries.csv")
    write_ground_truth_393(
        rows,
        EVAL_DIR / "ground_truth_verified.xlsx",
        EVAL_DIR / "ground_truth_verified_393.xlsx",
    )
    write_plain_text_sources(section_sources, DATA_DIR)


if __name__ == "__main__":
    main()
