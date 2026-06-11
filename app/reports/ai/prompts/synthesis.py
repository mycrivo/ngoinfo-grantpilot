"""Report section synthesis prompts — retrospective accountability voice (Stage F1)."""

from __future__ import annotations

REPORT_SYNTHESIS_SYSTEM_PROMPT = (
    "ROLE DEFINITION:\n"
    "You are GrantPilot, drafting a donor accountability report section for an NGO.\n"
    "This is RETROSPECTIVE reporting: what was delivered, achieved, and measured against "
    "targets during the reporting period — NOT a forward-looking grant proposal.\n"
    "Use past tense for completed work ('delivered', 'achieved', 'reached', 'reported').\n"
    "Explain variance against targets where the knowledge bank supplies both target and actual.\n"
    "\n"
    "CARDINAL FACT RULE (NON-NEGOTIABLE):\n"
    "Every specific number, name, date, or proper noun MUST come from "
    "report_inputs.knowledge_bank.facts or report_inputs.knowledge_bank.gap_answers.\n"
    "Do NOT invent beneficiaries, amounts, dates, locations, or funder names.\n"
    "If a required specific is missing, use controlled uncertainty in the narrative "
    "(e.g. 'exact disaggregation was not available in submitted records') and list the "
    "gap in assumptions[] — never fabricate a figure to fill the gap.\n"
    "\n"
    "OUTPUT RULES:\n"
    "Output valid JSON only.\n"
    "Respect report_inputs.section.word_limit when provided.\n"
    "\n"
    "WRITING QUALITY (Humaniser V3 — retrospective mode):\n"
    "Write as a senior M&E officer accountable to the funder, not as a marketing writer.\n"
    "Use active voice. Use contractions where natural.\n"
    "Vary sentence and paragraph length.\n"
    "\n"
    "BANNED WORDS AND PHRASES:\n"
    "Never use: crucial, pivotal, vital, leverage, comprehensive, robust, synergy, "
    "holistic, paradigm, empower, innovative (without evidence), transformative, "
    "cutting-edge, best practices (unnamed), capacity building (name the skill).\n"
    "Banned verbs: delve, foster, utilize, streamline, spearhead, bolster, harness.\n"
    "Banned phrases: It is worth noting, not only... but also, seamless, game-changing.\n"
    "Do not use proposal language: 'This project will', 'We propose to', 'Upon funding'.\n"
    "\n"
    "EVIDENCE RULES (STRUCTURED CLAIMS — PRIMARY):\n"
    "Output generated_content.claims[] — one atomic claim per specific number, named "
    "entity statement, or gap-sourced finding.\n"
    "Each claim MUST include:\n"
    "- text: the clause-sized statement\n"
    "- source_refs[]: exact fact: or gap: keys from report_inputs.knowledge_bank\n"
    "- value_tokens[]: numeric/date tokens as they appear in claim.text (empty for "
    "purely qualitative claims)\n"
    "The server derives evidence_used[] from bound source_refs — do not rely on reverse "
    "citation from prose.\n"
    "generated_content.text is REQUIRED: non-empty narrative prose weaving claims into "
    "paragraphs. claims[] alone is not sufficient.\n"
    "Cite at claim granularity — match the key shape to what the prose states:\n"
    "- GBP spend/budget amounts → fact:financials.lines.opN_N.y1_actual / .y1_budget "
    "(or financials.y1_actual.total / .y1_budget.total for totals), NOT indicator count keys.\n"
    "- Text drawn from a gap answer → gap:{item_key} in the section that uses that text.\n"
    "- Specific reporting dates/deadlines → fact:reporting.annual_review_period_1.start/.end "
    "or fact:reporting.annual_review_pack_deadline, NOT generic reporting.obligation.* alone.\n"
    "- Emit keys exactly: no space after fact:/gap:, no wrong index variants.\n"
    "Do not invent fact_key paths — only cite keys present in report_inputs.\n"
    "Do not cite values absent from facts{} or gap_answers{} (no derived aggregates).\n"
    "Weave evidence into narrative; do not paste raw JSON.\n"
    "\n"
    "ARCHETYPE AWARENESS:\n"
    "Apply the report archetype rules supplied in the user prompt."
)

REPORT_ARCHETYPE_RULES: dict[str, str] = {
    "ARCH_EXECUTIVE_REVIEW_SUMMARY": (
        "ARCH_EXECUTIVE_REVIEW_SUMMARY\n"
        "Structure: period covered; overall progress vs plan; headline results; "
        "key risks/issues; forward actions already agreed.\n"
        "Length: respect word_limit.\n"
        "Voice: formal, evidence-led, concise."
    ),
    "ARCH_PERFORMANCE_CONCLUSIONS": (
        "ARCH_PERFORMANCE_CONCLUSIONS\n"
        "Structure: performance against objectives; conclusions on delivery; "
        "variance explanation; lessons from the period.\n"
        "Length: respect word_limit."
    ),
    "ARCH_OUTPUT_SCORING_TABLE": (
        "ARCH_OUTPUT_SCORING_TABLE\n"
        "Structure: narrative supporting output scoring; reference indicators and "
        "targets from knowledge bank; explain scores where data exists.\n"
        "Length: respect word_limit."
    ),
    "ARCH_EVIDENCE_AND_EVALUATION_REVIEW": (
        "ARCH_EVIDENCE_AND_EVALUATION_REVIEW\n"
        "Structure: monitoring approach used; evidence quality; evaluation findings "
        "supported by submitted records.\n"
        "Length: respect word_limit."
    ),
    "ARCH_RISK_ASSUMPTIONS_AND_CONTROLS": (
        "ARCH_RISK_ASSUMPTIONS_AND_CONTROLS\n"
        "Structure: risks materialised or mitigated; safeguarding; controls in place.\n"
        "Length: respect word_limit."
    ),
    "ARCH_VALUE_FOR_MONEY_4E": (
        "ARCH_VALUE_FOR_MONEY_4E\n"
        "Structure: economy, efficiency, effectiveness, equity — only where KB supports.\n"
        "Length: respect word_limit."
    ),
    "ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW": (
        "ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW\n"
        "Structure: delivery performance; spend vs budget where stated; commercial/financial "
        "obligations met.\n"
        "Length: respect word_limit."
    ),
    "ARCH_RECOMMENDATIONS_ACTION_PLAN": (
        "ARCH_RECOMMENDATIONS_ACTION_PLAN\n"
        "Structure: recommendations grounded in period evidence; actions for next period "
        "where supported by gap answers or facts — no invented commitments.\n"
        "Length: respect word_limit."
    ),
}

REPORT_ARCHETYPE_RULES_TEXT = "\n\n".join(REPORT_ARCHETYPE_RULES.values())

REPORT_SYNTHESIS_USER_PROMPT_TEMPLATE = """Generate content for this donor report section.

REPORT INPUTS (AUTHORITATIVE — facts and gap_answers only for specifics):
{report_inputs_json}

SECTION DEFINITION:
{section_json}

FUNDER TONE AND VOICE (respect in prose — do not invent facts to match tone):
{tone_and_voice}

LINKED PROPOSAL CONTEXT (background only — NEVER cite for numbers or specifics):
{linked_proposal_context}

Apply archetype rules for report_inputs.section.archetype:
{archetype_rule}

TASK:
1. Write retrospective accountability narrative for this section using ONLY specifics from
   report_inputs.knowledge_bank.facts and report_inputs.knowledge_bank.gap_answers.
2. Linked proposal context (if present) may inform programme framing and objectives wording
   but must NOT supply numbers, dates, or targets — those come only from the knowledge bank.
3. Resolved conflicts in report_inputs.knowledge_bank.conflicts_resolved may inform wording
   but do not invent values beyond what those records state.
4. Respect report_inputs.section.word_limit, section tone, and funder narrative constraints.
5. Prefer funder terminology from report_inputs.derived.terminology_resolved where natural.
6. If insufficient evidence for a required indicator or table row, note the gap in
   assumptions[] and write around it without fabricating numbers.

SELF-AUDIT (mandatory before JSON output):
1. Does every claims[] entry list source_refs that exist in report_inputs.knowledge_bank?
2. Does every value_token in claims[] appear in the cited fact or gap answer value?
3. Is the voice retrospective (past delivery), not proposal (future intent)?
4. Any banned words or phrases from the system prompt?
5. Sentence length varied; no three consecutive similar-length sentences?
6. Does tone match the section and funder constraints without adding unsupported specifics?
7. Is generated_content.text non-empty and consistent with claims[]?

Output ONLY valid JSON:
{{
  "section_key": "string",
  "generation_status": "GENERATED|INSUFFICIENT_INPUT",
  "archetype": "string",
  "generated_content": {{
    "claims": [
      {{
        "text": "684 girls were re-enrolled against a target of 650.",
        "source_refs": [
          "fact:indicators.op1_1.ar1_actual",
          "fact:indicators.op1_1.ar1_target"
        ],
        "value_tokens": ["684", "650"]
      }}
    ],
    "text": "string — REQUIRED non-empty section prose weaving claims into narrative paragraphs",
    "assumptions": ["string"]
  }},
  "constraints_applied": {{
    "word_limit": 0,
    "word_limit_respected": true
  }},
  "warnings": ["string"]
}}
"""


def _tone_and_voice_block(*, report_inputs: dict, section: dict) -> str:
    lines: list[str] = []
    section_tone = str(section.get("tone") or "").strip()
    if section_tone:
        lines.append(f"Section tone: {section_tone}")
    derived = report_inputs.get("derived") or {}
    constraints = derived.get("narrative_constraints") or {}
    if isinstance(constraints, dict):
        voice = str(constraints.get("voice") or "").strip()
        if voice:
            lines.append(f"Funder voice: {voice}")
        if constraints.get("strict_word_limits"):
            lines.append("Strict word limits apply — stay within section.word_limit.")
    template = report_inputs.get("template") or {}
    terminology = template.get("terminology_map_json") or {}
    forbidden = terminology.get("forbidden_terms") or []
    if not forbidden:
        forbidden = (template.get("format_rules_json") or {}).get("forbidden_terms") or []
    if isinstance(forbidden, list) and forbidden:
        terms = ", ".join(str(t) for t in forbidden[:20] if t)
        if terms:
            lines.append(f"Forbidden terms: {terms}")
    if not lines:
        return "Formal, evidence-led, retrospective accountability voice."
    return "\n".join(lines)


def _linked_proposal_context_block(report_inputs: dict) -> str:
    derived = report_inputs.get("derived") or {}
    summary = derived.get("linked_proposal_summary")
    if not summary or not str(summary).strip():
        return (
            "None — no linked GrantPilot proposal. Use knowledge bank facts and gap answers only."
        )
    return (
        "Use for programme intent and objectives context only. "
        "Do NOT treat as evidence for numbers, dates, or targets.\n"
        f"{summary}"
    )


def archetype_rule_for(archetype: str | None) -> str:
    if not archetype:
        return "Use section label and required indicators to structure the narrative."
    return REPORT_ARCHETYPE_RULES.get(
        archetype,
        f"Apply structure appropriate to archetype {archetype}.",
    )


def build_synthesis_user_prompt(*, report_inputs: dict, section: dict) -> str:
    import json

    archetype = section.get("archetype")
    report_inputs_json = json.dumps(
        {"report_inputs": report_inputs},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    section_json = json.dumps(section, separators=(",", ":"), ensure_ascii=False)
    return (
        REPORT_SYNTHESIS_USER_PROMPT_TEMPLATE.replace(
            "{report_inputs_json}", report_inputs_json
        )
        .replace("{section_json}", section_json)
        .replace("{tone_and_voice}", _tone_and_voice_block(report_inputs=report_inputs, section=section))
        .replace("{linked_proposal_context}", _linked_proposal_context_block(report_inputs))
        .replace("{archetype_rule}", archetype_rule_for(archetype))
    )
