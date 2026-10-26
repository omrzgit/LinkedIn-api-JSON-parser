#!/usr/bin/env python3
"""
LinkedIn JSON to HTML Profile Generator
Converts LinkedIn scraper/API JSON payloads into an authentic, standalone LinkedIn-styled HTML profile.

Usage:
    python linkedin_to_html.py input.json [-o output.html] [--open]
    cat input.json | python linkedin_to_html.py > output.html
"""

import argparse
import html
import json
import os
import sys
import webbrowser
from typing import Any, Dict, List, Optional

MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def format_date(d: Optional[Dict[str, Any]]) -> str:
    if not d or not isinstance(d, dict):
        return ""
    year = d.get("year")
    month = d.get("month")
    if not year:
        return ""
    if month and 1 <= month <= 12:
        return f"{MONTH_NAMES[month]} {year}"
    return str(year)

def format_date_range(start: Optional[Dict[str, Any]], end: Optional[Dict[str, Any]], is_current: bool = False) -> str:
    start_str = format_date(start)
    if is_current:
        end_str = "Present"
    elif end:
        end_str = format_date(end)
    else:
        end_str = "Present" if not start_str else ""
    
    if start_str and end_str:
        return f"{start_str} - {end_str}"
    return start_str or end_str or ""

def calc_duration(start: Optional[Dict[str, Any]], end: Optional[Dict[str, Any]], is_current: bool = False) -> str:
    if not start or not isinstance(start, dict) or not start.get("year"):
        return ""
    
    s_year = start.get("year")
    s_month = start.get("month") or 1
    
    if is_current or not end or not isinstance(end, dict) or not end.get("year"):
        import datetime
        now = datetime.datetime.now()
        e_year = now.year
        e_month = now.month
    else:
        e_year = end.get("year")
        e_month = end.get("month") or 12
    
    total_months = (e_year - s_year) * 12 + (e_month - s_month) + 1
    if total_months <= 0:
        return ""
    
    years = total_months // 12
    months = total_months % 12
    
    parts = []
    if years > 0:
        parts.append(f"{years} yr{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} mo{'s' if months > 1 else ''}")
    return " · " + " ".join(parts) if parts else ""

def extract_profile_data(raw_data: Any) -> Dict[str, Any]:
    """Finds the profile dictionary inside nested JSON structures."""
    if not isinstance(raw_data, dict):
        return {}
    
    if "data" in raw_data and isinstance(raw_data["data"], dict):
        if "profile" in raw_data["data"] and isinstance(raw_data["data"]["profile"], dict):
            return raw_data["data"]["profile"]
        return raw_data["data"]
    
    if "profile" in raw_data and isinstance(raw_data["profile"], dict):
        return raw_data["profile"]
    
    return raw_data

def escape(val: Any) -> str:
    if val is None:
        return ""
    return html.escape(str(val))

def generate_linkedin_html(raw_json: Any) -> str:
    p = extract_profile_data(raw_json)
    
    # Basic info
    full_name = p.get("fullName") or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or "LinkedIn Member"
    headline = p.get("headline") or ""
    summary = p.get("summary") or ""
    location = p.get("location") or (p.get("geo") or {}).get("full") or "Global"
    profile_url = p.get("profileUrl") or f"https://www.linkedin.com/in/{p.get('handle', '')}" if p.get("handle") else "https://www.linkedin.com"
    handle = p.get("handle") or full_name.lower().replace(" ", "")
    
    # Counts
    follower_count = p.get("followerCount")
    connections_count = p.get("connectionsCount")
    conn_text_parts = []
    if connections_count:
        conn_text_parts.append(f"<strong>{connections_count:,}</strong> connections")
    if follower_count:
        conn_text_parts.append(f"<span>{follower_count:,} followers</span>")
    connections_html = " · ".join(conn_text_parts) if conn_text_parts else "<span>500+ connections</span>"
    
    is_open_to_work = bool(p.get("isOpenToWork"))
    
    # Images
    profile_pic = p.get("profilePictureUrl")
    if not profile_pic and p.get("profilePictures"):
        pics = p.get("profilePictures")
        if isinstance(pics, list) and len(pics) > 0:
            profile_pic = pics[-1].get("url")
    if not profile_pic:
        profile_pic = f"https://ui-avatars.com/api/?name={escape(full_name)}&background=0a66c2&color=fff&size=200"

    banner_img = None
    if p.get("backgroundImages") and isinstance(p["backgroundImages"], list) and len(p["backgroundImages"]) > 0:
        banner_img = p["backgroundImages"][-1].get("url")
    
    banner_style = f"background-image: url('{escape(banner_img)}');" if banner_img else "background: linear-gradient(135deg, #183353 0%, #0d1e34 100%);"
    
    # Current Positions & Education for hero side-rail
    positions = p.get("positions") or p.get("fullPositions") or []
    current_pos_list = [pos for pos in positions if pos.get("isCurrent")] or (positions[:1] if positions else [])
    
    education_list = p.get("education") or []
    
    hero_affiliations_html = ""
    if current_pos_list:
        first_pos = current_pos_list[0]
        org = first_pos.get("organization") or {}
        org_name = org.get("name") or first_pos.get("organizationName") or ""
        org_logo = org.get("logoUrl") or first_pos.get("organizationLogo") or f"https://ui-avatars.com/api/?name={escape(org_name)}&background=0a66c2&color=fff"
        org_url = org.get("url") or first_pos.get("organizationUrl") or "#"
        if org_name:
            hero_affiliations_html += f"""
              <a href="{escape(org_url)}" target="_blank" class="affiliation-item">
                <img src="{escape(org_logo)}" alt="{escape(org_name)}" class="affiliation-logo" onerror="this.src='https://ui-avatars.com/api/?name={escape(org_name)}&background=0a66c2&color=fff';">
                <span>{escape(org_name)}</span>
              </a>"""
              
    if education_list:
        first_edu = education_list[0]
        school_name = first_edu.get("schoolName") or ""
        school_logo = first_edu.get("schoolLogo") or f"https://ui-avatars.com/api/?name={escape(school_name)}&background=2e7d32&color=fff"
        school_url = first_edu.get("schoolUrl") or "#"
        if school_name:
            hero_affiliations_html += f"""
              <a href="{escape(school_url)}" target="_blank" class="affiliation-item">
                <img src="{escape(school_logo)}" alt="{escape(school_name)}" class="affiliation-logo" onerror="this.src='https://ui-avatars.com/api/?name={escape(school_name)}&background=2e7d32&color=fff';">
                <span>{escape(school_name)}</span>
              </a>"""

    # Open to work badge & card
    otw_frame_html = ""
    otw_card_html = ""
    if is_open_to_work:
        otw_frame_html = """
            <svg class="opentowork-frame" viewBox="0 0 156 156" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M 12 110 A 74 74 0 0 0 144 110" stroke="#057642" stroke-width="12" stroke-linecap="round" fill="none" />
              <path id="otw-text-path" d="M 22 108 A 66 66 0 0 0 134 108" fill="none"/>
              <text font-family="-apple-system, Segoe UI, Roboto, sans-serif" font-size="8.5" font-weight="800" fill="#ffffff" letter-spacing="1.2">
                <textPath href="#otw-text-path" startOffset="50%" text-anchor="middle">
                  #OPEN TO WORK
                </textPath>
              </text>
            </svg>"""
        
        otw_card_html = f"""
          <div class="open-to-work-card">
            <div>
              <div class="otw-title">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="#057642">
                  <path d="M13.5 2h-11A1.5 1.5 0 001 3.5v9A1.5 1.5 0 002.5 14h11a1.5 1.5 0 001.5-1.5v-9A1.5 1.5 0 0013.5 2zM6 4h4v1H6V4zm7 8.5a.5.5 0 01-.5.5h-9a.5.5 0 01-.5-.5V8h10v4.5zm0-5.5H3V5h10v1.5z"/>
                </svg>
                <span>Open to work</span>
              </div>
              <p class="otw-desc">
                <span class="otw-roles">Open to new opportunities and roles relevant to skill set</span>
              </p>
              <a href="#about" class="otw-link">Show details</a>
            </div>
            <svg class="edit-pencil-icon" viewBox="0 0 16 16">
              <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
            </svg>
          </div>"""

    # About Section
    about_html = ""
    if summary:
        formatted_summary = escape(summary).replace("\n", "<br>")
        about_html = f"""
      <section id="about" class="card section-card">
        <div class="section-header">
          <h2 class="section-title">About</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="about-text">{formatted_summary}</div>
      </section>"""

    # Experience Section
    experience_html = ""
    if positions:
        pos_items_html = []
        for pos in positions:
            title = escape(pos.get("title") or "Position")
            emp_type = escape(pos.get("employmentType") or "")
            org = pos.get("organization") or {}
            org_name = escape(org.get("name") or pos.get("organizationName") or "")
            org_logo = org.get("logoUrl") or pos.get("organizationLogo") or f"https://ui-avatars.com/api/?name={org_name}&background=0a66c2&color=fff"
            org_url = org.get("url") or pos.get("organizationUrl") or "#"
            
            sub_parts = [p for p in [org_name, emp_type] if p]
            subtitle = " · ".join(sub_parts)
            
            is_cur = bool(pos.get("isCurrent"))
            date_range = format_date_range(pos.get("start"), pos.get("end"), is_cur)
            dur = calc_duration(pos.get("start"), pos.get("end"), is_cur)
            date_line = f"{escape(date_range)}{escape(dur)}" if date_range else ""
            
            loc = escape(pos.get("location") or "")
            desc = escape(pos.get("description") or "").replace("\n", "<br>")
            
            desc_block = f'<div class="entry-description">{desc}</div>' if desc else ""
            loc_block = f'<div class="entry-location">{loc}</div>' if loc else ""
            
            pos_items_html.append(f"""
          <div class="entry-item">
            <a href="{escape(org_url)}" target="_blank">
              <img src="{escape(org_logo)}" alt="{org_name}" class="entry-logo" onerror="this.src='https://ui-avatars.com/api/?name={org_name}&background=0a66c2&color=fff';">
            </a>
            <div class="entry-content">
              <div class="entry-title">{title}</div>
              <div class="entry-subtitle">{subtitle}</div>
              <div class="entry-date">{date_line}</div>
              {loc_block}
              {desc_block}
            </div>
          </div>""")
            
        experience_html = f"""
      <section class="card section-card">
        <div class="section-header">
          <h2 class="section-title">Experience</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="entry-list">
          {''.join(pos_items_html)}
        </div>
      </section>"""

    # Education Section
    education_html = ""
    if education_list:
        edu_items_html = []
        for edu in education_list:
            s_name = escape(edu.get("schoolName") or "Institution")
            s_url = edu.get("schoolUrl") or "#"
            s_logo = edu.get("schoolLogo") or f"https://ui-avatars.com/api/?name={s_name}&background=2e7d32&color=fff"
            deg = escape(edu.get("degreeName") or "")
            fos = escape(edu.get("fieldOfStudy") or "")
            deg_parts = [p for p in [deg, fos] if p]
            degree_str = ", ".join(deg_parts)
            
            dates = format_date_range(edu.get("start"), edu.get("end"))
            grade = escape(edu.get("grade") or "")
            grade_html = f'<div class="entry-location">Grade: <strong>{grade}</strong></div>' if grade else ""
            
            desc = escape(edu.get("description") or "").replace("\n", "<br>")
            desc_html = f'<div class="entry-description">{desc}</div>' if desc else ""
            
            edu_items_html.append(f"""
          <div class="entry-item">
            <a href="{escape(s_url)}" target="_blank">
              <img src="{escape(s_logo)}" alt="{s_name}" class="entry-logo" onerror="this.src='https://ui-avatars.com/api/?name={s_name}&background=2e7d32&color=fff';">
            </a>
            <div class="entry-content">
              <div class="entry-title">{s_name}</div>
              <div class="entry-subtitle">{degree_str}</div>
              <div class="entry-date">{dates}</div>
              {grade_html}
              {desc_html}
            </div>
          </div>""")
            
        education_html = f"""
      <section class="card section-card">
        <div class="section-header">
          <h2 class="section-title">Education</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="entry-list">
          {''.join(edu_items_html)}
        </div>
      </section>"""

    # Certifications Section
    certifications = p.get("certifications") or []
    certifications_html = ""
    if certifications:
        cert_items_html = []
        for cert in certifications:
            c_name = escape(cert.get("name") or cert.get("title") or "Certification")
            auth = escape(cert.get("authority") or (cert.get("organization") or {}).get("name") or "")
            c_logo = (cert.get("organization") or {}).get("logoUrl") or f"https://ui-avatars.com/api/?name={auth}&background=c62828&color=fff"
            
            issue_date = format_date(cert.get("start"))
            exp_date = format_date(cert.get("end"))
            date_str = ""
            if issue_date and exp_date:
                date_str = f"Issued {issue_date} · Expires {exp_date}"
            elif issue_date:
                date_str = f"Issued {issue_date}"
            elif exp_date:
                date_str = f"Expires {exp_date}"
                
            cred_url = cert.get("url") or "#"
            
            cert_items_html.append(f"""
          <div class="entry-item">
            <img src="{escape(c_logo)}" alt="{auth}" class="entry-logo" onerror="this.src='https://ui-avatars.com/api/?name={auth}&background=0a66c2&color=fff';">
            <div class="entry-content">
              <div class="entry-title">{c_name}</div>
              <div class="entry-subtitle">{auth}</div>
              <div class="entry-date">{escape(date_str)}</div>
              <a href="{escape(cred_url)}" class="credential-button" target="_blank">
                <span>Show credential</span>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M14 9v5a1 1 0 01-1 1H2a1 1 0 01-1-1V3a1 1 0 011-1h5v2H3v9h9V9h2zm-2-7h4v4h-2V4.41L7.71 10.7 6.3 9.29 12.59 3H12V2z"/>
                </svg>
              </a>
            </div>
          </div>""")
            
        certifications_html = f"""
      <section class="card section-card">
        <div class="section-header">
          <h2 class="section-title">Licenses &amp; Certifications</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="entry-list">
          {''.join(cert_items_html)}
        </div>
      </section>"""

    # Projects Section
    projects = p.get("projects") or []
    projects_html = ""
    if projects:
        proj_items_html = []
        for proj in projects:
            p_title = escape(proj.get("title") or "Project")
            p_desc = escape(proj.get("description") or "").replace("\n", "<br>")
            p_dates = format_date_range(proj.get("start"), proj.get("end"))
            p_url = proj.get("url") or ""
            
            title_el = f'<a href="{escape(p_url)}" target="_blank" class="entry-title">{p_title}</a>' if p_url else f'<div class="entry-title">{p_title}</div>'
            desc_el = f'<div class="entry-description">{p_desc}</div>' if p_desc else ""
            date_el = f'<div class="entry-date">{escape(p_dates)}</div>' if p_dates else ""
            
            proj_items_html.append(f"""
          <div class="entry-item">
            <div class="entry-logo" style="display:flex;align-items:center;justify-content:center;background:#f0f7ff;color:#0a66c2;border-radius:4px;font-size:20px;">
              🛡️
            </div>
            <div class="entry-content">
              {title_el}
              {date_el}
              {desc_el}
            </div>
          </div>""")
            
        projects_html = f"""
      <section class="card section-card">
        <div class="section-header">
          <h2 class="section-title">Projects</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="entry-list">
          {''.join(proj_items_html)}
        </div>
      </section>"""

    # Skills Section
    skills_raw = p.get("skills") or []
    skills_html = ""
    if skills_raw:
        pill_list = []
        for s in skills_raw:
            s_name = s.get("name") if isinstance(s, dict) else str(s)
            if s_name:
                pill_list.append(f'<div class="skill-pill"><span class="skill-bullet"></span> {escape(s_name)}</div>')
        if pill_list:
            skills_html = f"""
      <section class="card section-card">
        <div class="section-header">
          <h2 class="section-title">Skills</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="skills-grid">
          {''.join(pill_list)}
        </div>
      </section>"""

    # Languages Section
    languages = p.get("languages") or []
    languages_html = ""
    if languages:
        lang_cards = []
        for lang in languages:
            l_name = escape(lang.get("name") or "")
            l_prof = escape((lang.get("proficiency") or "").replace("_", " ").title())
            if l_name:
                lang_cards.append(f"""
          <div class="language-card">
            <div class="language-name">{l_name}</div>
            <div class="language-level">{l_prof}</div>
          </div>""")
        if lang_cards:
            languages_html = f"""
      <section class="card section-card">
        <div class="section-header">
          <h2 class="section-title">Languages</h2>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <div class="language-grid">
          {''.join(lang_cards)}
        </div>
      </section>"""

    # Assemble HTML document
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="referrer" content="no-referrer">
  <title>{escape(full_name)} | LinkedIn</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-color: #f4f2ee;
      --card-bg: #ffffff;
      --border-color: #e0dfdc;
      --border-light: #ebebeb;
      --text-primary: #191919;
      --text-secondary: #666666;
      --text-muted: #8c8c8c;
      --li-blue: #0a66c2;
      --li-blue-hover: #004182;
      --li-blue-light: #e8f3fc;
      --open-to-work-green: #057642;
      --shadow-card: 0 0 0 1px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
      --font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background-color: var(--bg-color);
      color: var(--text-primary);
      font-family: var(--font-family);
      line-height: 1.45;
      -webkit-font-smoothing: antialiased;
    }}

    a {{ color: var(--li-blue); text-decoration: none; font-weight: 600; }}
    a:hover {{ text-decoration: underline; }}

    /* GLOBAL NAV BAR */
    .global-nav {{
      position: sticky; top: 0; background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      z-index: 1000; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .nav-container {{
      max-width: 1128px; margin: 0 auto; height: 53px;
      display: flex; align-items: center; justify-content: space-between; padding: 0 16px;
    }}
    .nav-left {{ display: flex; align-items: center; gap: 10px; }}
    .li-logo-svg {{ width: 35px; height: 35px; fill: var(--li-blue); flex-shrink: 0; }}
    .search-box {{
      display: flex; align-items: center; background: #edf3f8;
      border-radius: 4px; padding: 0 12px; height: 34px; width: 280px; gap: 8px;
    }}
    .search-box input {{ border: none; background: transparent; outline: none; font-size: 14px; width: 100%; }}
    .nav-right {{ display: flex; align-items: center; height: 100%; gap: 4px; }}
    .nav-item {{
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-width: 60px; height: 100%; color: var(--text-secondary); font-size: 12px; text-decoration: none; position: relative;
    }}
    .nav-item:hover, .nav-item.active {{ color: var(--text-primary); text-decoration: none; }}
    .nav-item.active::after {{
      content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: var(--text-primary);
    }}
    .nav-item svg {{ width: 22px; height: 22px; fill: currentColor; margin-bottom: 2px; }}
    .nav-avatar-mini {{ width: 22px; height: 22px; border-radius: 50%; object-fit: cover; margin-bottom: 2px; }}
    .nav-divider {{ width: 1px; height: 34px; background: var(--border-color); margin: 0 8px; }}
    .premium-link {{ color: #915907 !important; font-size: 11px; text-align: center; }}

    /* APP BODY */
    .app-body {{
      max-width: 1128px; margin: 20px auto 40px auto; padding: 0 16px;
      display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 24px;
    }}
    @media (max-width: 860px) {{
      .app-body {{ grid-template-columns: 1fr; }}
      .right-sidebar {{ display: none; }}
    }}

    .card {{
      background: var(--card-bg); border-radius: 10px; border: 1px solid var(--border-color);
      box-shadow: var(--shadow-card); margin-bottom: 12px; overflow: hidden;
    }}

    /* PROFILE HERO */
    .banner-container {{
      height: 200px; position: relative; overflow: hidden; {banner_style}
      background-size: cover; background-position: center;
    }}
    .profile-header-content {{ padding: 0 24px 24px 24px; position: relative; }}
    .avatar-wrapper {{
      position: relative; width: 152px; height: 152px; margin-top: -106px; margin-bottom: 12px;
    }}
    .avatar-img {{
      width: 144px; height: 144px; border-radius: 50%; border: 4px solid #ffffff;
      background: #ffffff; object-fit: cover; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
      position: relative; z-index: 1;
    }}
    .opentowork-frame {{
      position: absolute; top: -2px; left: -2px; width: 156px; height: 156px; z-index: 2; pointer-events: none;
    }}

    .hero-grid {{ display: flex; justify-content: space-between; gap: 24px; }}
    .hero-main-info {{ flex: 1; }}
    .name-badge-row {{ display: flex; align-items: center; gap: 8px; }}
    .profile-name {{ font-size: 24px; font-weight: 700; color: var(--text-primary); line-height: 1.25; }}
    .verified-icon {{ width: 18px; height: 18px; fill: var(--li-blue); }}
    .pronouns-degree {{ color: var(--text-secondary); font-size: 14px; }}
    .profile-headline {{ font-size: 15px; color: var(--text-primary); margin-top: 6px; line-height: 1.35; }}
    .location-contact-row {{
      margin-top: 10px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 14px; color: var(--text-secondary);
    }}
    .contact-info-link {{ font-weight: 600; color: var(--li-blue); }}
    .connections-count {{ margin-top: 10px; font-size: 14px; color: var(--li-blue); font-weight: 600; }}
    .connections-count span {{ color: var(--text-secondary); font-weight: 400; }}

    .hero-company-edu {{ width: 240px; display: flex; flex-direction: column; gap: 12px; }}
    @media (max-width: 720px) {{
      .hero-grid {{ flex-direction: column; }}
      .hero-company-edu {{ width: 100%; }}
    }}
    .affiliation-item {{
      display: flex; align-items: center; gap: 10px; color: var(--text-primary); font-size: 14px; font-weight: 600;
    }}
    .affiliation-item:hover {{ text-decoration: underline; color: var(--li-blue); }}
    .affiliation-logo {{
      width: 36px; height: 36px; border-radius: 4px; border: 1px solid var(--border-light);
      object-fit: cover; flex-shrink: 0; background: #ffffff;
    }}

    .hero-actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
    .btn {{
      display: inline-flex; align-items: center; justify-content: center; gap: 6px;
      padding: 6px 16px; font-size: 15px; font-weight: 600; border-radius: 20px;
      cursor: pointer; text-decoration: none; transition: all 0.2s ease; line-height: 20px;
    }}
    .btn-primary {{ background-color: var(--li-blue); color: #ffffff; border: 1px solid transparent; }}
    .btn-primary:hover {{ background-color: var(--li-blue-hover); color: #ffffff; text-decoration: none; }}
    .btn-outline-primary {{ background-color: transparent; color: var(--li-blue); border: 1px solid var(--li-blue); }}
    .btn-outline-primary:hover {{ background-color: var(--li-blue-light); text-decoration: none; }}
    .btn-outline-secondary {{ background-color: transparent; color: var(--text-secondary); border: 1px solid var(--text-secondary); }}
    .btn-outline-secondary:hover {{ background-color: rgba(0,0,0,0.05); color: var(--text-primary); text-decoration: none; }}

    /* OPEN TO WORK CARD */
    .open-to-work-card {{
      background: #edf7ee; border: 1px solid #d0e7d2; border-radius: 8px;
      padding: 14px 16px; margin-top: 18px; display: flex; justify-content: space-between; align-items: flex-start;
    }}
    .otw-title {{ font-size: 14px; font-weight: 600; color: #0b5c2a; display: flex; align-items: center; gap: 6px; }}
    .otw-desc {{ font-size: 13px; color: var(--text-primary); margin-top: 2px; }}
    .otw-roles {{ font-weight: 500; }}
    .otw-link {{ font-size: 13px; color: var(--li-blue); font-weight: 600; margin-top: 4px; display: inline-block; }}

    /* SECTION CARD & LISTS */
    .section-card {{ padding: 24px; }}
    .section-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }}
    .section-title {{ font-size: 20px; font-weight: 700; color: var(--text-primary); }}
    .edit-pencil-icon {{ width: 20px; height: 20px; fill: var(--text-secondary); cursor: pointer; }}
    .about-text {{ font-size: 14px; line-height: 1.6; color: var(--text-primary); }}

    .entry-list {{ display: flex; flex-direction: column; }}
    .entry-item {{ display: flex; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border-light); }}
    .entry-item:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .entry-item:first-child {{ padding-top: 0; }}
    .entry-logo {{
      width: 48px; height: 48px; border-radius: 4px; border: 1px solid var(--border-light);
      object-fit: contain; background: #ffffff; flex-shrink: 0; margin-top: 2px;
    }}
    .entry-content {{ flex: 1; }}
    .entry-title {{ font-size: 16px; font-weight: 600; color: var(--text-primary); line-height: 1.3; }}
    .entry-subtitle {{ font-size: 14px; color: var(--text-primary); margin-top: 2px; font-weight: 500; }}
    .entry-date {{ font-size: 12px; color: var(--text-secondary); margin-top: 2px; }}
    .entry-location {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}
    .entry-description {{ font-size: 14px; line-height: 1.5; color: var(--text-primary); margin-top: 8px; }}

    .credential-button {{
      display: inline-flex; align-items: center; gap: 6px; margin-top: 10px;
      padding: 4px 12px; font-size: 13px; font-weight: 600; color: var(--text-secondary);
      border: 1px solid var(--text-secondary); border-radius: 16px; text-decoration: none;
    }}
    .credential-button:hover {{ background: rgba(0,0,0,0.04); color: var(--text-primary); text-decoration: none; }}

    /* SKILLS */
    .skills-grid {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
    .skill-pill {{
      background: #ffffff; border: 1px solid var(--border-color); padding: 8px 16px;
      border-radius: 20px; font-size: 14px; font-weight: 600; color: var(--text-primary);
      display: flex; align-items: center; gap: 6px; transition: all 0.2s;
    }}
    .skill-pill:hover {{ border-color: var(--li-blue); color: var(--li-blue); background: var(--li-blue-light); }}
    .skill-bullet {{ width: 6px; height: 6px; border-radius: 50%; background: var(--li-blue); }}

    /* LANGUAGES */
    .language-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-top: 8px; }}
    .language-card {{ padding: 12px 14px; background: #f9fafb; border-radius: 8px; border: 1px solid var(--border-light); }}
    .language-name {{ font-size: 15px; font-weight: 600; color: var(--text-primary); }}
    .language-level {{ font-size: 13px; color: var(--text-secondary); margin-top: 2px; }}

    /* SIDEBAR */
    .sidebar-card {{ padding: 20px; }}
    .sidebar-title {{ font-size: 16px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
    .sidebar-desc {{ font-size: 13px; color: var(--text-secondary); word-break: break-all; }}
    .sidebar-link {{ font-size: 13px; color: var(--text-secondary); font-weight: 600; display: block; margin-top: 4px; }}
    .sidebar-divider {{ height: 1px; background: var(--border-light); margin: 16px 0; }}

    /* FOOTER */
    .page-footer {{ max-width: 1128px; margin: 20px auto 40px auto; text-align: center; font-size: 12px; color: var(--text-secondary); padding: 0 16px; }}
    .footer-links {{ display: flex; justify-content: center; flex-wrap: wrap; gap: 16px; margin-bottom: 12px; }}
    .footer-links a {{ color: var(--text-secondary); font-weight: 500; text-decoration: none; }}
    .footer-links a:hover {{ color: var(--li-blue); text-decoration: underline; }}
  </style>
</head>
<body>

  <!-- GLOBAL NAV BAR -->
  <header class="global-nav">
    <div class="nav-container">
      <div class="nav-left">
        <a href="https://www.linkedin.com" target="_blank" title="LinkedIn">
          <svg class="li-logo-svg" viewBox="0 0 24 24">
            <path d="M20.5 2h-17A1.5 1.5 0 002 3.5v17A1.5 1.5 0 003.5 22h17a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0020.5 2zM8 19H5v-9h3zM6.5 8.25A1.75 1.75 0 118.3 6.5a1.78 1.78 0 01-1.8 1.75zM19 19h-3v-4.74c0-1.42-.6-1.93-1.38-1.93A1.74 1.74 0 0013 14.19a.66.66 0 000 .14V19h-3v-9h2.9v1.3a3.11 3.11 0 012.7-1.4c1.55 0 3.36.86 3.36 3.66z"></path>
          </svg>
        </a>
        <div class="search-box">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="#666666">
            <path d="M14.56 12.44L11.3 9.18a5.5 5.5 0 10-2.12 2.12l3.26 3.26a1.5 1.5 0 002.12-2.12zM2.5 6.5a4 4 0 114 4 4 4 0 01-4-4z"/>
          </svg>
          <input type="text" placeholder="Search" value="{escape(full_name)}" readonly>
        </div>
      </div>

      <nav class="nav-right">
        <a href="#" class="nav-item">
          <svg viewBox="0 0 24 24"><path d="M23 9v2h-2v7a3 3 0 01-3 3h-4v-6h-4v6H6a3 3 0 01-3-3v-7H1V9l11-7z"></path></svg>
          <span>Home</span>
        </a>
        <a href="#" class="nav-item">
          <svg viewBox="0 0 24 24"><path d="M12 16v6H3v-6a3 3 0 013-3h3a3 3 0 013 3zm5.5-3A3.5 3.5 0 1014 9.5a3.5 3.5 0 003.5 3.5zm1 2h-2a2.5 2.5 0 00-2.5 2.5V22h7v-4.5a2.5 2.5 0 00-2.5-2.5zM7.5 2A4.5 4.5 0 1012 6.5 4.49 4.49 0 007.5 2z"></path></svg>
          <span>My Network</span>
        </a>
        <a href="#" class="nav-item">
          <svg viewBox="0 0 24 24"><path d="M17 6V5a3 3 0 00-3-3h-4a3 3 0 00-3 3v1H2v4a3 3 0 003 3h14a3 3 0 003-3V6zM9 5a1 1 0 011-1h4a1 1 0 011 1v1H9zm10 9a4 4 0 00-3 1.38V15H8v.38A4 4 0 005 14H2v5a3 3 0 003 3h14a3 3 0 003-3v-5z"></path></svg>
          <span>Jobs</span>
        </a>
        <a href="#" class="nav-item">
          <svg viewBox="0 0 24 24"><path d="M16 4H8a7 7 0 000 14h4v4l5.62-4.11A6.74 6.74 0 0023 11a7 7 0 00-7-7zm-4 9H8V11h4zm4-4H8V7h8z"></path></svg>
          <span>Messaging</span>
        </a>
        <a href="#" class="nav-item">
          <svg viewBox="0 0 24 24"><path d="M22 19h-1.63a6.11 6.11 0 01-.37-.87l-1-3.32A5 5 0 0014 11V7a2 2 0 00-4 0v4a5 5 0 00-5 3.81l-1 3.32a6.11 6.11 0 01-.37.87H2v2h20zm-8 2a2 2 0 01-4 0z"></path></svg>
          <span>Notifications</span>
        </a>
        <a href="#" class="nav-item active">
          <img src="{escape(profile_pic)}" class="nav-avatar-mini" alt="Me" onerror="this.src='https://ui-avatars.com/api/?name={escape(full_name)}&background=0a66c2&color=fff';">
          <span>Me ▾</span>
        </a>
        <div class="nav-divider"></div>
        <a href="#" class="nav-item premium-link">
          <span>Try Premium for $0</span>
        </a>
      </nav>
    </div>
  </header>

  <!-- MAIN CONTAINER -->
  <main class="app-body">
    <div class="main-content">
      
      <!-- HERO CARD -->
      <section class="card profile-hero">
        <div class="banner-container"></div>
        <div class="profile-header-content">
          <div class="avatar-wrapper">
            <img src="{escape(profile_pic)}" alt="{escape(full_name)}" class="avatar-img" onerror="this.src='https://ui-avatars.com/api/?name={escape(full_name)}&background=0a66c2&color=fff';">
            {otw_frame_html}
          </div>

          <div class="hero-grid">
            <div class="hero-main-info">
              <div class="name-badge-row">
                <h1 class="profile-name">{escape(full_name)}</h1>
                <span class="pronouns-degree">· 1st</span>
                <svg class="verified-icon" viewBox="0 0 16 16" title="Verified Member">
                  <path d="M8 0a8 8 0 108 8A8 8 0 008 0zm3.7 6.3l-4.24 4.24a.75.75 0 01-1.06 0L4.3 8.44a.75.75 0 011.06-1.06L7 9.04l3.64-3.8a.75.75 0 011.06 1.06z"/>
                </svg>
              </div>

              <p class="profile-headline">{escape(headline)}</p>

              <div class="location-contact-row">
                <span>{escape(location)}</span>
                <span>·</span>
                <a href="{escape(profile_url)}" target="_blank" class="contact-info-link">Contact info</a>
              </div>

              <div class="connections-count">
                {connections_html}
              </div>

              <div class="hero-actions">
                <a href="{escape(profile_url)}" target="_blank" class="btn btn-primary">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M14 2H2a1 1 0 00-1 1v10a1 1 0 001 1h12a1 1 0 001-1V3a1 1 0 00-1-1zm-1 3.25L8 8.42 3 5.25V4l5 3.17L13 4v1.25z"/>
                  </svg>
                  Message
                </a>
                <a href="{escape(profile_url)}" target="_blank" class="btn btn-outline-primary">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M8 2a3 3 0 103 3 3 3 0 00-3-3zm0 7c-3 0-5 1.5-5 3v1h10v-1c0-1.5-2-3-5-3zm5-2h-1V6h-1v1h-1v1h1v1h1V8h1V7z"/>
                  </svg>
                  Connect
                </a>
                <a href="#about" class="btn btn-outline-secondary">More</a>
              </div>
            </div>

            <div class="hero-company-edu">
              {hero_affiliations_html}
            </div>
          </div>

          {otw_card_html}
        </div>
      </section>

      {about_html}
      {experience_html}
      {education_html}
      {certifications_html}
      {projects_html}
      {skills_html}
      {languages_html}

    </div>

    <!-- RIGHT SIDEBAR -->
    <aside class="right-sidebar">
      <div class="card sidebar-card">
        <div class="sidebar-title">
          <span>Public profile &amp; URL</span>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <p class="sidebar-desc">
          <a href="{escape(profile_url)}" target="_blank" class="sidebar-link">
            www.linkedin.com/in/{escape(handle)}
          </a>
        </p>

        <div class="sidebar-divider"></div>

        <div class="sidebar-title">
          <span>Profile language</span>
          <svg class="edit-pencil-icon" viewBox="0 0 16 16">
            <path d="M12.85 2.15a1.5 1.5 0 010 2.12L4.54 12.58l-3.08.77a.5.5 0 01-.61-.61l.77-3.08L9.93 1.34a1.5 1.5 0 012.92.81z"/>
          </svg>
        </div>
        <p class="sidebar-desc" style="font-weight: 500;">English</p>
      </div>

      <div class="card sidebar-card" style="text-align: center;">
        <span style="font-size: 11px; color: var(--text-muted); float: right;">Promoted ···</span>
        <div style="clear:both; margin-top: 10px;">
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Connect and discover relevant opportunities</p>
          <div style="display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 14px;">
            <img src="{escape(profile_pic)}" style="width: 52px; height: 52px; border-radius: 50%; object-fit: cover; border: 2px solid #0a66c2;" alt="{escape(full_name)}" onerror="this.src='https://ui-avatars.com/api/?name={escape(full_name)}&background=0a66c2&color=fff';">
            <div style="width: 48px; height: 48px; border-radius: 8px; background: #0a66c2; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 20px;">
              💼
            </div>
          </div>
          <p style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">
            {escape(full_name)}, explore industry opportunities
          </p>
          <a href="{escape(profile_url)}" target="_blank" class="btn btn-outline-primary" style="margin-top: 8px; width: 100%;">
            View Profile
          </a>
        </div>
      </div>
    </aside>
  </main>

  <footer class="page-footer">
    <div class="footer-links">
      <a href="#">About</a>
      <a href="#">Accessibility</a>
      <a href="#">Help Center</a>
      <a href="#">Privacy &amp; Terms ▾</a>
      <a href="#">Ad Choices</a>
      <a href="#">Advertising</a>
      <a href="#">Business Services ▾</a>
    </div>
    <p>LinkedIn Corporation © 2026. Standalone profile viewer generated from JSON.</p>
  </footer>

</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(
        description="Convert LinkedIn profile JSON into a viewable LinkedIn-style HTML document."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to the JSON file (or '-' to read from stdin). If omitted, reads stdin if piped."
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output HTML file path (default: stdout or <input_stem>.html)"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the generated HTML file in your web browser."
    )

    args = parser.parse_args()

    # Read JSON
    if args.input and args.input != "-":
        if not os.path.isfile(args.input):
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        with open(args.input, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        default_out = os.path.splitext(args.input)[0] + ".html"
    else:
        if sys.stdin.isatty():
            print("Error: No input file specified and no piped data detected.", file=sys.stderr)
            parser.print_help(file=sys.stderr)
            sys.exit(1)
        raw_data = json.load(sys.stdin)
        default_out = "linkedin_profile.html"

    # Generate HTML
    html_output = generate_linkedin_html(raw_data)

    out_file = args.output
    if not out_file and (args.open or (args.input and args.input != "-")):
        out_file = default_out

    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"[+] Successfully generated LinkedIn HTML: {os.path.abspath(out_file)}")
        if args.open:
            webbrowser.open(os.path.abspath(out_file))
    else:
        sys.stdout.write(html_output)

if __name__ == "__main__":
    main()
