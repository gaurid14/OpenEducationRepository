import re
import pdfplumber
from django.db import transaction
from ..models import Program, Department, Scheme, Course, Chapter, CourseOutcome
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# --- Initialize Gemini ---
llm = None
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=api_key)

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10
}

def _roman_to_int(r):
    return ROMAN_TO_INT.get(r.upper(), None)


def extract_and_upload(pdf_file):
    """Robust syllabus parser for Mumbai University-style PDFs."""

    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    lines = [re.sub(r'\s+', ' ', l).strip() for l in text.splitlines() if l.strip()]

    # --- Program / Dept / Scheme header ---
    header = "\n".join(lines[:150])
    program = re.search(r'(Bachelor of [A-Za-z &]+)', header, re.IGNORECASE)
    dept = re.search(r'in ([A-Za-z &]+)', header, re.IGNORECASE)
    scheme = re.search(r'\(REV[-– ]?\s*\d{4}\s*[A-Za-z‘’"]*\s*Scheme\)', header, re.IGNORECASE)
    year = re.search(r'(\d{4})', header)

    program_name = program.group(1) if program else "Bachelor of Engineering"
    dept_name = dept.group(1) if dept else "Information Technology"
    scheme_name = scheme.group(0) if scheme else "REV-2019 C Scheme"
    start_year = int(year.group(1)) if year else 2020

    print(f"\n📘 Program: {program_name}")
    print(f"🏫 Department: {dept_name}")
    print(f"📚 Scheme: {scheme_name} ({start_year})\n")

    # --- Detect course headers ---
    course_re = re.compile(r'^([A-Z]{2,5}\d{3,4}[A-Z]?)\s+([A-Za-z].+)$')
    course_indices = [i for i, ln in enumerate(lines) if course_re.match(ln)]

    if not course_indices:
        print("⚠️ No course headers detected — check PDF text structure!")
        return False

    print(f"Found {len(course_indices)} courses:\n")

    with transaction.atomic():
        program_obj, _ = Program.objects.get_or_create(program_name=program_name)
        dept_obj, _ = Department.objects.get_or_create(program=program_obj, dept_name=dept_name)
        scheme_obj, _ = Scheme.objects.get_or_create(name=scheme_name, defaults={'start_year': start_year})

        for idx, ci in enumerate(course_indices):
            header_line = lines[ci]
            m = course_re.match(header_line)
            if not m:
                continue
            code, name = m.groups()
            end = course_indices[idx + 1] if idx + 1 < len(course_indices) else len(lines)
            block = "\n".join(lines[ci:end])

            print(f"📖 {code} — {name}")

            # --- Extract COs (only within the CO section) ---
            co_section = re.search(r'Course Outcomes:(.+?)(Prerequisite:|Sr\. No\. Course Objectives|DETAILED SYLLABUS)',
                                   block, re.DOTALL | re.IGNORECASE)
            outcomes = []
            if co_section:
                co_text = co_section.group(1)
                outcomes = [m.group(1).strip() for m in re.finditer(r'\d+\s+(.+)', co_text)]
            print(f"   ➕ {len(outcomes)} COs detected")

            # --- Extract Modules (within “DETAILED SYLLABUS” section) ---
            mod_section = re.search(r'DETAILED SYLLABUS[:\-]?(.*)', block, re.DOTALL | re.IGNORECASE)
            modules = []
            if mod_section:
                mod_text = mod_section.group(1)
                for m1 in re.finditer(r'^\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\s+([A-Za-z].+)', mod_text, re.MULTILINE):
                    modules.append({'num': _roman_to_int(m1.group(1)), 'title': m1.group(2).strip()})
                for m2 in re.finditer(r'Module\s*(\d+)[:\-]?\s*(.+)', mod_text, re.IGNORECASE):
                    modules.append({'num': int(m2.group(1)), 'title': m2.group(2).strip()})
            print(f"   📚 {len(modules)} Modules detected\n")

            # --- DB Save ---
            course_obj, _ = Course.objects.get_or_create(
                department=dept_obj,
                scheme=scheme_obj,
                course_code=code,
                defaults={'course_name': name}
            )

            for i, o in enumerate(outcomes, 1):
                CourseOutcome.objects.get_or_create(
                    course=course_obj, outcome_code=f"CO{i}", defaults={'description': o}
                )

            for m in modules:
                Chapter.objects.get_or_create(
                    course=course_obj,
                    chapter_number=m['num'] or 0,
                    defaults={'chapter_name': m['title']}
                )

    print("\n✅ Parsing and upload complete!\n")
    return True
