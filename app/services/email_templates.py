from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

LOGO_URL = "https://ngoinfo.org/wp-content/uploads/2026/04/ngoinfo_logo_new.png"
FONT_STACK = "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
BG_COLOR = "#F8F9FC"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#374151"
CTA_BG = "#1A1F71"
CTA_TEXT = "#FFFFFF"
LINK_COLOR = "#1A1F71"
CARD_RADIUS = "12px"
CARD_PADDING = "24px"


@dataclass(frozen=True)
class EmailTemplate:
    subject: str
    html: str
    text: str


def _name_or_empty(full_name: str | None) -> str:
    if not full_name:
        return ""
    cleaned = full_name.strip()
    return cleaned


def _join_url(base_url: str, path_or_url: str) -> str:
    candidate = (path_or_url or "").strip()
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate
    base = base_url.rstrip("/") + "/"
    return urljoin(base, candidate.lstrip("/"))


def _render_email(
    *,
    greeting: str,
    paragraphs: list[str],
    cta_label: str,
    cta_url: str,
    footer_text: str | None = None,
    secondary_link_label: str | None = None,
    secondary_link_url: str | None = None,
) -> str:
    paragraph_html = "".join(
        f'<p style="margin:0 0 14px 0; line-height:1.6; color:{TEXT_COLOR};">{line}</p>'
        for line in paragraphs
    )
    secondary_link_html = ""
    if secondary_link_label and secondary_link_url:
        secondary_link_html = (
            f'<p style="margin:16px 0 0 0; line-height:1.6;">'
            f'<a href="{secondary_link_url}" style="color:{LINK_COLOR};text-decoration:underline;">'
            f"{secondary_link_label}</a></p>"
        )
    footer_html = ""
    if footer_text:
        footer_html = (
            f'<p style="margin:18px 0 0 0; line-height:1.6; color:{TEXT_COLOR};">'
            f"{footer_text}</p>"
        )
    return (
        "<!doctype html>"
        "<html>"
        "<body style=\"margin:0;padding:24px;background:#F8F9FC;"
        f"font-family:{FONT_STACK};color:{TEXT_COLOR};\">"
        "<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:600px;margin:0 auto;\">"
        "<tr><td>"
        f"<div style=\"background:{CARD_COLOR};padding:{CARD_PADDING};border-radius:{CARD_RADIUS};\">"
        f"<img src=\"{LOGO_URL}\" alt=\"NGOInfo\" width=\"150\" style=\"display:block;margin:0 auto 24px;\">"
        f"<h2 style=\"margin:0 0 16px 0; font-size:28px; line-height:1.25; color:{TEXT_COLOR};\">{greeting}</h2>"
        f"{paragraph_html}"
        "<p style=\"margin:18px 0 0 0;\">"
        f"<a href=\"{cta_url}\" style=\"display:inline-block;background:{CTA_BG};color:{CTA_TEXT};"
        "padding:14px 24px;border-radius:8px;font-weight:600;font-size:16px;text-decoration:none;\">"
        f"{cta_label}</a></p>"
        f"{secondary_link_html}"
        f"{footer_html}"
        "</div>"
        "</td></tr></table>"
        "</body></html>"
    )


def _greeting(full_name: str | None, with_suffix: str) -> str:
    name = _name_or_empty(full_name)
    if name:
        return f"{name}, {with_suffix}"
    return with_suffix


def build_magic_link_template(
    *,
    full_name: str | None,
    login_link: str,
    expires_minutes: int,
    base_url: str,
) -> EmailTemplate:
    cta_url = _join_url(base_url, login_link)
    greeting = _greeting(full_name, "you're in.")
    paragraphs = [
        "Use this secure link to sign in to GrantPilot.",
        f"This link expires in {expires_minutes} minutes.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Sign In",
        cta_url=cta_url,
        footer_text="If the button doesn't work, copy and paste the link from your browser's address bar.",
    )
    text = (
        f"{greeting}\n\n"
        "Use this secure link to sign in to GrantPilot.\n\n"
        f"Sign In: {cta_url}\n\n"
        f"This link expires in {expires_minutes} minutes."
    )
    return EmailTemplate(subject="Your GrantPilot magic link", html=html, text=text)


def build_welcome_template(
    *,
    full_name: str | None,
    profile_link: str,
    base_url: str,
) -> EmailTemplate:
    cta_url = _join_url(base_url, profile_link)
    greeting = _greeting(full_name, "you're in.")
    paragraphs = [
        "GrantPilot generates proposal drafts and runs donor fit checks — but it needs your organisation's details first. The better your profile, the more useful the output.",
        "About 5 minutes to fill in.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Complete Your Profile",
        cta_url=cta_url,
        footer_text="Questions? Reply here. Someone reads this inbox.",
    )
    text = (
        f"{greeting}\n\n"
        "GrantPilot generates proposal drafts and runs donor fit checks — but it needs your organisation's details first. "
        "The better your profile, the more useful the output.\n\n"
        "About 5 minutes to fill in.\n\n"
        f"Complete Your Profile: {cta_url}\n\n"
        "Questions? Reply here. Someone reads this inbox."
    )
    return EmailTemplate(
        subject="Welcome to GrantPilot — set up your profile",
        html=html,
        text=text,
    )


def build_profile_complete_template(
    *,
    full_name: str | None,
    dashboard_link: str,
    base_url: str,
) -> EmailTemplate:
    dashboard_url = _join_url(base_url, dashboard_link)
    browse_url = "https://ngoinfo.org"
    greeting = _greeting(full_name, "your profile's all set.")
    paragraphs = [
        "Next step: pick a funding opportunity on NGOInfo.org that looks relevant, and run a fit scan. It'll tell you where your organisation lines up with what the funder wants — and where the gaps are.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Browse Opportunities",
        cta_url=browse_url,
        secondary_link_label="Go to Dashboard",
        secondary_link_url=dashboard_url,
    )
    text = (
        f"{greeting}\n\n"
        "Next step: pick a funding opportunity on NGOInfo.org that looks relevant, and run a fit scan. "
        "It'll tell you where your organisation lines up with what the funder wants — and where the gaps are.\n\n"
        f"Browse Opportunities: {browse_url}\n"
        f"Go to Dashboard: {dashboard_url}"
    )
    return EmailTemplate(
        subject="Profile done — ready for your first fit scan",
        html=html,
        text=text,
    )


def _fit_rating_label(overall_fit_rating: str) -> str:
    mapping = {
        "RECOMMENDED": "Recommended",
        "APPLY_WITH_CAVEATS": "Apply with Caveats",
        "NOT_RECOMMENDED": "Not Recommended",
    }
    return mapping.get((overall_fit_rating or "").strip().upper(), overall_fit_rating or "Unknown")


def build_fit_scan_ready_template(
    *,
    full_name: str | None,
    opportunity_title: str,
    overall_fit_rating: str,
    fit_scan_link: str,
    base_url: str,
) -> EmailTemplate:
    cta_url = _join_url(base_url, fit_scan_link)
    rating_label = _fit_rating_label(overall_fit_rating)
    greeting = _greeting(full_name, f"your fit scan for {opportunity_title} is done.")
    paragraphs = [
        f"Rating: {rating_label}",
        "The results break down how your organisation matches the funder's requirements — eligibility, thematic focus, geography, and budget. Worth reading through before deciding whether to draft a proposal.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="View Results",
        cta_url=cta_url,
    )
    text = (
        f"{greeting}\n\n"
        f"Rating: {rating_label}\n\n"
        "The results break down how your organisation matches the funder's requirements — eligibility, thematic focus, geography, and budget. "
        "Worth reading through before deciding whether to draft a proposal.\n\n"
        f"View Results: {cta_url}"
    )
    return EmailTemplate(
        subject=f"Fit scan for {opportunity_title} — {rating_label}",
        html=html,
        text=text,
    )


def build_proposal_ready_template(
    *,
    full_name: str | None,
    opportunity_title: str,
    proposal_link: str,
    upgrade_link: str,
    is_free_plan: bool,
    base_url: str,
) -> EmailTemplate:
    proposal_url = _join_url(base_url, proposal_link)
    upgrade_url = _join_url(base_url, upgrade_link)
    greeting = _greeting(full_name, f"your draft for {opportunity_title} is ready.")
    paragraphs = [
        "Go through each section carefully. This is a working draft — adjust the language, add specifics the draft couldn't know, and check anything flagged as an assumption before you submit.",
    ]
    if is_free_plan:
        paragraphs.extend(
            [
                "------------------------------",
                "That was your free proposal. If you want to run more fit scans and generate additional proposals, take a look at the paid plans.",
            ]
        )
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Review Your Draft",
        cta_url=proposal_url,
        secondary_link_label="View plans" if is_free_plan else None,
        secondary_link_url=upgrade_url if is_free_plan else None,
    )
    text = (
        f"{greeting}\n\n"
        "Go through each section carefully. This is a working draft — adjust the language, add specifics the draft couldn't know, "
        "and check anything flagged as an assumption before you submit.\n\n"
        f"Review Your Draft: {proposal_url}"
    )
    if is_free_plan:
        text += (
            "\n\nThat was your free proposal. If you want to run more fit scans and generate additional proposals, "
            f"take a look at the paid plans.\nView plans: {upgrade_url}"
        )
    return EmailTemplate(
        subject=f"Your draft proposal for {opportunity_title}",
        html=html,
        text=text,
    )


def _plan_label(plan_name: str) -> str:
    mapping = {"GROWTH": "Growth", "IMPACT": "Impact"}
    return mapping.get((plan_name or "").strip().upper(), plan_name or "Plan")


def build_subscription_activated_template(
    *,
    full_name: str | None,
    plan_name: str,
    dashboard_link: str,
    billing_portal_link: str,
    base_url: str,
) -> EmailTemplate:
    plan_label = _plan_label(plan_name)
    dashboard_url = _join_url(base_url, dashboard_link)
    billing_url = _join_url(base_url, billing_portal_link)
    greeting = _greeting(full_name, f"your {plan_label} plan is active.")
    paragraphs = [
        "Updated quotas apply from now.",
        "You can manage your subscription or update payment details from the billing page any time.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Go to Dashboard",
        cta_url=dashboard_url,
        secondary_link_label="Manage billing",
        secondary_link_url=billing_url,
    )
    text = (
        f"{greeting}\n\nUpdated quotas apply from now.\n\n"
        "You can manage your subscription or update payment details from the billing page any time.\n\n"
        f"Go to Dashboard: {dashboard_url}\nManage billing: {billing_url}"
    )
    return EmailTemplate(
        subject=f"You're on the {plan_label} plan",
        html=html,
        text=text,
    )


def build_payment_failed_template(
    *,
    full_name: str | None,
    plan_name: str,
    billing_portal_link: str,
    base_url: str,
) -> EmailTemplate:
    plan_label = _plan_label(plan_name)
    billing_url = _join_url(base_url, billing_portal_link)
    greeting = _greeting(full_name, f"the latest charge for your {plan_label} plan didn't go through.")
    paragraphs = [
        "Usually that's an expired card or a temporary bank issue.",
        "If it's not sorted out, your account will drop back to the Free plan once the current billing period ends. You'd keep your data and past work — just the quota limits would change.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Update Payment Method",
        cta_url=billing_url,
        footer_text="Something look wrong? Reply to this email and we'll figure it out.",
    )
    text = (
        f"{greeting}\n\nUsually that's an expired card or a temporary bank issue.\n\n"
        "If it's not sorted out, your account will drop back to the Free plan once the current billing period ends. "
        "You'd keep your data and past work — just the quota limits would change.\n\n"
        f"Update Payment Method: {billing_url}\n\n"
        "Something look wrong? Reply to this email and we'll figure it out."
    )
    return EmailTemplate(
        subject=f"Payment issue on your {plan_label} plan",
        html=html,
        text=text,
    )


def _format_access_end_date(access_end_date: datetime | None) -> str:
    if access_end_date is None:
        return "the end of your current billing period"
    return f"{access_end_date.day} {access_end_date.strftime('%B %Y')}"


def build_subscription_cancelled_template(
    *,
    full_name: str | None,
    plan_name: str,
    access_end_date: datetime | None,
    billing_portal_link: str,
    base_url: str,
) -> EmailTemplate:
    plan_label = _plan_label(plan_name)
    billing_url = _join_url(base_url, billing_portal_link)
    end_date_text = _format_access_end_date(access_end_date)
    greeting = _greeting(full_name, f"your {plan_label} cancellation is confirmed.")
    paragraphs = [
        f"You've got access to {plan_label} features until {end_date_text}. After that, your account switches to the Free plan. Everything you've already created — fit scans, proposals, your profile — stays where it is.",
        f"Changed your mind? You can reactivate before {end_date_text}.",
    ]
    html = _render_email(
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Reactivate",
        cta_url=billing_url,
    )
    text = (
        f"{greeting}\n\n"
        f"You've got access to {plan_label} features until {end_date_text}. After that, your account switches to the Free plan. "
        "Everything you've already created — fit scans, proposals, your profile — stays where it is.\n\n"
        f"Changed your mind? You can reactivate before {end_date_text}.\n\n"
        f"Reactivate: {billing_url}"
    )
    return EmailTemplate(
        subject=f"{plan_label} plan cancelled",
        html=html,
        text=text,
    )
