# import re
# import pdfplumber
# from .models import Program, Department, Scheme, Course, Chapter, CourseOutcome, OutcomeChapterMapping
#
# def extract_and_upload(pdf_file):
#     # 1️⃣ Extract text
#     pdf_text = ""
#     with pdfplumber.open(pdf_file) as pdf:
#         for page in pdf.pages:
#             pdf_text += page.extract_text() + "\n"
#
#     text = re.sub(r'\s+', ' ', pdf_text)  # clean up spaces
#
#     # 2️⃣ Static / inferred values (modify as needed)
#     program_name = "Engineering"
#     dept_name = "Information Technology"
#     scheme_name = "Revised C19"
#     start_year = 2019
#
#     program, _ = Program.objects.get_or_create(program_name=program_name)
#     department, _ = Department.objects.get_or_create(program=program, dept_name=dept_name)
#     scheme, _ = Scheme.objects.get_or_create(name=scheme_name, start_year=start_year)
#
#     # 3️⃣ Extract course info
#     course_pattern = re.compile(r"Course\s*Code\s*[:\-]\s*([A-Za-z0-9]+)\s*Course\s*Name\s*[:\-]\s*([A-Za-z0-9\s\-\(\)&,]+)", re.IGNORECASE)
#     course_matches = course_pattern.findall(text)
#
#     for code, name in course_matches:
#         course, _ = Course.objects.get_or_create(
#             department=department,
#             scheme=scheme,
#             course_code=code.strip(),
#             course_name=name.strip()
#         )
#
#         # 4️⃣ Extract modules/chapters
#         module_pattern = re.compile(r"Module\s*(\d+)\s*[:\-]\s*([A-Za-z0-9\s,.\-\(\)]+)", re.IGNORECASE)
#         for num, mod_name in module_pattern.findall(text):
#             Chapter.objects.get_or_create(
#                 course=course,
#                 chapter_number=int(num),
#                 chapter_name=mod_name.strip()
#             )
#
#         # 5️⃣ Extract Course Outcomes (CO1, CO2, etc.)
#         co_pattern = re.compile(r"(CO\d+)\s*[:\-]\s*([A-Za-z0-9\s,.\-\(\)]+)", re.IGNORECASE)
#         for code, desc in co_pattern.findall(text):
#             CourseOutcome.objects.get_or_create(
#                 course=course,
#                 outcome_code=code.strip().upper(),
#                 description=desc.strip()
#             )
#
#     return True


# accounts/utils.py
import re
import pdfplumber
from django.db import transaction
from ..models import Program, Department, Scheme, Course, Chapter, CourseOutcome, OutcomeChapterMapping

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15
}

def _roman_to_int(r):
    return ROMAN_TO_INT.get(r.upper(), None)

def _normalize_line(ln):
    return re.sub(r'\s+', ' ', (ln or '')).strip()

def extract_and_upload(pdf_file):
    """
    Parse a Mumbai University style syllabus PDF and populate DB models.
    Accepts a file-like object (e.g. Django UploadedFile).
    Returns a dict summary of created/updated objects.
    """

    # 1) read pages -> keep line-based structure (we need line boundaries)
    pages_lines = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # keep original newlines per page; normalize \r
            page_lines = [ln.rstrip() for ln in text.splitlines()]
            pages_lines.append(page_lines)

    # flatten pages with a blank line between pages (helps section separation)
    lines = []
    for page in pages_lines:
        # trim leading/trailing empties per page
        for ln in page:
            ln2 = ln.strip()
            # keep lines that have content (but we preserve short lines for headers)
            lines.append(ln2)
        lines.append("")  # page separator

    full_text = "\n".join(lines)

    # 2) Extract program/department/scheme/start_year from top portion (first 40 lines)
    header_text = "\n".join(lines[:120]).strip()

    # Program name (e.g. "Bachelor of Engineering")
    prog_m = re.search(r'(Bachelor of [A-Za-z &]+)', header_text, re.IGNORECASE)
    program_name = prog_m.group(1).strip() if prog_m else "Bachelor of Engineering"

    # Department (e.g. "Information Technology")
    dept_m = re.search(r'Bachelor of [A-Za-z &]+ in ([A-Za-z &]+)', header_text, re.IGNORECASE)
    dept_name = dept_m.group(1).strip() if dept_m else None
    # fallback: search for "Information Technology" explicit
    if not dept_name:
        dm = re.search(r'Information Technology|Computer Science|Mechanical|EXTC', header_text, re.IGNORECASE)
        dept_name = dm.group(0).strip() if dm else "Information Technology"

    # Scheme name: try to capture text containing "Scheme" near "REV" or "Revised"
    scheme_name = None
    scheme_m = re.search(r'\(([^)]*Scheme[^)]*)\)', header_text, re.IGNORECASE)
    if scheme_m:
        scheme_name = scheme_m.group(1).strip()
    else:
        s2 = re.search(r'(Revised\s*[A-Za-z0-9\'"\- ]*Scheme)', header_text, re.IGNORECASE)
        if s2:
            scheme_name = s2.group(1).strip()
    if not scheme_name:
        # generic fallback: look for "REV" followed by year
        s3 = re.search(r'(REV[-\s]*\d{4}.*?)Scheme', header_text, re.IGNORECASE)
        scheme_name = s3.group(0).strip() if s3 else "Revised C Scheme"

    # start_year: find first 4-digit year in header (likely academic start)
    sy = re.search(r'Academic Year.*?(\d{4})', header_text, re.IGNORECASE)
    if sy:
        start_year = int(sy.group(1))
    else:
        # fallback: first 4-digit year in top-of-document
        any_year = re.search(r'(\d{4})', header_text)
        start_year = int(any_year.group(1)) if any_year else None

    # 3) Find "DETAILED SYLLABUS" occurrences and associate each with nearest course header above it
    detailed_indices = [i for i, ln in enumerate(lines) if 'DETAILED SYLLABUS' in (ln or '').upper()]

    # helper regex for course header line containing code + name
    course_header_re = re.compile(r'^\s*([A-Z]{2,5}\d{3}[A-Z]?)\s+(.+)$')

    course_sections = []  # list of dicts: {code, name, start_idx, end_idx}
    for det_idx in detailed_indices:
        # look up to 12 lines above for a course header
        found = False
        for back in range(1, 13):
            idx = det_idx - back
            if idx < 0:
                break
            ln = lines[idx]
            if not ln:
                continue
            m = course_header_re.match(ln)
            if m:
                code = m.group(1).strip()
                name = m.group(2).strip()
                # find end_idx: either the next detailed section or next course code occurrence later
                # choose end at next detailed index (if exists) or det_idx+200 (cap)
                # we'll compute end_idx later; temporarily store start as idx
                course_sections.append({'code': code, 'name': name, 'start': idx, 'det_idx': det_idx})
                found = True
                break
        if not found:
            # fallback: maybe course header is two lines above (code on one line, name on next)
            # search for a code only line
            for back in range(1, 15):
                idx = det_idx - back
                if idx < 0: break
                ln = lines[idx]
                cm = re.match(r'^\s*([A-Z]{2,5}\d{3}[A-Z]?)\s*$', ln)
                if cm:
                    code = cm.group(1).strip()
                    name = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
                    course_sections.append({'code': code, 'name': name, 'start': idx, 'det_idx': det_idx})
                    found = True
                    break
        # if still not found, skip this detailed block

    # de-duplicate by code (some PDFs may have repeats)
    seen_codes = set()
    unique_sections = []
    for sec in course_sections:
        if sec['code'] not in seen_codes:
            seen_codes.add(sec['code'])
            unique_sections.append(sec)

    # determine end indices: end = next section start - 1 else end = start + 300 (cap)
    for i, sec in enumerate(unique_sections):
        next_start = unique_sections[i+1]['start'] if i+1 < len(unique_sections) else None
        if next_start:
            sec['end'] = next_start - 1
        else:
            sec['end'] = min(len(lines)-1, sec['start'] + 400)

    # 4) Persist Program / Department / Scheme (use transaction)
    created = {'program': 0, 'department': 0, 'scheme': 0, 'courses': 0, 'chapters': 0, 'outcomes': 0, 'mappings': 0}
    with transaction.atomic():
        program_obj, created_prog = Program.objects.get_or_create(program_name=program_name)
        created['program'] += 1 if created_prog else 0

        dept_obj, created_dept = Department.objects.get_or_create(program=program_obj, dept_name=dept_name)
        created['department'] += 1 if created_dept else 0

        scheme_obj, created_scheme = Scheme.objects.get_or_create(name=scheme_name, defaults={'start_year': start_year or 0})
        if created_scheme and start_year:
            scheme_obj.start_year = start_year
            scheme_obj.save()
        created['scheme'] += 1 if created_scheme else 0

        # 5) For each course section, parse outcomes and modules and insert
        for sec in unique_sections:
            code = sec['code']
            name = sec['name']

            # find the sub-block text
            block_lines = lines[sec['start']:sec['end']+1]

            # create or get course
            course_obj, created_course = Course.objects.get_or_create(
                department=dept_obj,
                scheme=scheme_obj,
                course_code=code,
                defaults={'course_name': name[:200]}
            )
            if not created_course:
                # if course exists but name empty or different, try to update if blank
                if course_obj.course_name.strip() == "" and name:
                    course_obj.course_name = name[:200]
                    course_obj.save()
            created['courses'] += 1 if created_course else 0

            # ----- extract course outcomes: numbered list after "Course Outcomes" heading -----
            outcomes = []  # list of strings
            # find index in block_lines
            block_text = "\n".join(block_lines)
            co_head_idx = None
            for i_b, ln in enumerate(block_lines):
                if 'course outcomes' in ln.lower():
                    co_head_idx = i_b
                    break
            if co_head_idx is not None:
                # collect subsequent numbered lines until we hit a stop token
                j = co_head_idx + 1
                current = None
                while j < len(block_lines):
                    ln = block_lines[j].strip()
                    if ln == "":
                        # skip blanks but stop if subsequent stop words appear
                        j += 1
                        continue
                    low = ln.lower()
                    if any(low.startswith(token) for token in ('detailed syllabus', 'detailed syllabus:', 'text books', 'prerequisite', 'course objectives', 'sr. no.', 'sr no', 'module')):
                        break
                    # numbered outcome e.g. "1 Design models ..."
                    m = re.match(r'^\s*(\d+)\s+(.+)', ln)
                    if m:
                        # start a new outcome
                        if current:
                            outcomes.append(current.strip())
                        current = m.group(2).strip()
                    else:
                        # continuation line
                        if current:
                            current += " " + ln
                        else:
                            # sometimes outcomes are labelled "CO1: ..." directly
                            mco = re.match(r'^\s*(CO\d+)\s*[:\-]\s*(.+)', ln, re.IGNORECASE)
                            if mco:
                                outcomes.append(mco.group(2).strip())
                            else:
                                # unknown line: maybe part of previous; append to last if exists
                                if outcomes:
                                    outcomes[-1] += " " + ln
                    j += 1
                if current:
                    outcomes.append(current.strip())

            # If no outcomes found by numeric method, try to find CO1: labels anywhere
            if not outcomes:
                cos_direct = re.findall(r'(?:CO|Co|co)\s*?(\d+)\s*[:\-]\s*([A-Za-z0-9 ,.\-\(\)/&]+)', block_text)
                if cos_direct:
                    # cos_direct is list of tuples of (num, desc)
                    outcomes = [d.strip() for n, d in cos_direct]

            # Create CourseOutcome objects (CO1..)
            co_objs = []
            for idx, desc in enumerate(outcomes):
                code_label = f"CO{idx+1}"
                co_obj, created_co = CourseOutcome.objects.get_or_create(
                    course=course_obj,
                    outcome_code=code_label,
                    defaults={'description': desc}
                )
                if not created_co and (not co_obj.description) and desc:
                    co_obj.description = desc
                    co_obj.save()
                co_objs.append((code_label, co_obj))
                created['outcomes'] += 1 if created_co else 0

            # ----- extract modules/chapters (after "DETAILED SYLLABUS") -----
            modules = []  # list of dicts {num:int, title:str, cos:[codes]}
            # find index of "DETAILED SYLLABUS" in block_lines
            det_idx_block = None
            for i_b, ln in enumerate(block_lines):
                if 'detailed syllabus' in ln.lower():
                    det_idx_block = i_b
                    break
            if det_idx_block is not None:
                # scan lines after det_idx_block for module starts
                i_m = det_idx_block + 1
                current_module = None
                while i_m < len(block_lines):
                    ln = block_lines[i_m].strip()
                    if ln == "":
                        i_m += 1
                        continue
                    low = ln.lower()
                    if any(low.startswith(token) for token in ('text books', 'references', 'prerequisite', 'sr. no.', 'course objectives')):
                        break  # stop module parsing
                    # Module by roman numerals e.g. "I Uncertainty" or "II Cognitive Computing"
                    roman_match = re.match(r'^\s*(?P<roman>I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b[\s\-\:]*([A-Za-z].*)?', ln, re.IGNORECASE)
                    module_match = re.match(r'^\s*(?:Module)\s*(\d+)\s*[:\-]?\s*(.+)', ln, re.IGNORECASE)
                    # some rows may be like "I\nUncertainty in AI, Inference..." so treat single-letter line as numeral header
                    if roman_match:
                        roman = roman_match.group(1).upper()
                        num = _roman_to_int(roman) or (len(modules)+1)
                        # title may be on same line after numeral
                        maybe_title = ln[roman_match.end():].strip()
                        # start an entry
                        if current_module:
                            # finalize previous module
                            modules.append(current_module)
                        current_module = {'num': num, 'title': maybe_title or None, 'desc_lines': [], 'cos': []}
                        i_m += 1
                        # collect description lines until a line that contains "CO" token or next roman/module
                        while i_m < len(block_lines):
                            subln = block_lines[i_m].strip()
                            if not subln:
                                i_m += 1
                                continue
                            # check if subln is next roman/module header
                            if re.match(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b', subln, re.IGNORECASE) or re.match(r'^(Module)\s*\d+', subln, re.IGNORECASE):
                                break
                            # if line contains something like "04 CO1" (hours + CO mapping) -> extract CO tokens
                            cos_found = re.findall(r'\bCO\s*\d+\b', subln, re.IGNORECASE)
                            if cos_found:
                                # normalize CO tokens
                                cos_norm = [c.upper().replace(' ', '') for c in cos_found]
                                current_module['cos'].extend(cos_norm)
                                i_m += 1
                                # continue looking for further CO tokens on subsequent lines
                                continue
                            # else this is description
                            current_module['desc_lines'].append(subln)
                            i_m += 1
                        # end inner while, do not increment i_m here because outer loop continues correctly
                        continue  # next outer iteration without i_m +=1 because inner loop progressed
                    elif module_match:
                        # "Module 1: Title"
                        num = int(module_match.group(1))
                        maybe_title = module_match.group(2).strip()
                        if current_module:
                            modules.append(current_module)
                        current_module = {'num': num, 'title': maybe_title, 'desc_lines': [], 'cos': []}
                        i_m += 1
                        # collect following description lines similar to above
                        while i_m < len(block_lines):
                            subln = block_lines[i_m].strip()
                            if not subln:
                                i_m += 1
                                continue
                            if re.match(r'^(Module)\s*\d+', subln, re.IGNORECASE) or re.match(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\b', subln, re.IGNORECASE):
                                break
                            cos_found = re.findall(r'\bCO\s*\d+\b', subln, re.IGNORECASE)
                            if cos_found:
                                cos_norm = [c.upper().replace(' ', '') for c in cos_found]
                                current_module['cos'].extend(cos_norm)
                                i_m += 1
                                continue
                            current_module['desc_lines'].append(subln)
                            i_m += 1
                        continue
                    else:
                        # not a module header; maybe a part of table rows like "I Uncertainty" was split into two lines
                        # Try to detect patterns like "Uncertainty in AI..." followed later by "04 CO1" — if we have current_module, append
                        if current_module:
                            # detect CO tokens on this line
                            cos_found = re.findall(r'\bCO\s*\d+\b', ln, re.IGNORECASE)
                            if cos_found:
                                cos_norm = [c.upper().replace(' ', '') for c in cos_found]
                                current_module['cos'].extend(cos_norm)
                            else:
                                current_module['desc_lines'].append(ln)
                        i_m += 1
                        continue
                # finalize last module
                if current_module:
                    modules.append(current_module)

            # If modules were not detected via detailed table, attempt simpler fallback: find lines starting with "Sr. No." or "1." etc (omitted here for brevity)

            # Create Chapter entries and OutcomeChapterMapping
            # If outcomes exist, build a map outcome_code -> CourseOutcome obj
            outcome_map = {}
            for code_label, co_obj in co_objs:
                outcome_map[code_label.upper()] = co_obj

            # create chapters
            for idx_m, mod in enumerate(modules):
                # determine number and title
                chap_num = mod.get('num') or idx_m+1
                chap_title = mod.get('title') or " ".join(mod.get('desc_lines')[:1])[:200] or f"Module {chap_num}"
                ch_obj, created_ch = Chapter.objects.get_or_create(
                    course=course_obj,
                    chapter_number=chap_num,
                    defaults={'chapter_name': chap_title[:200]}
                )
                if not created_ch and (not ch_obj.chapter_name) and chap_title:
                    ch_obj.chapter_name = chap_title[:200]
                    ch_obj.save()
                created['chapters'] += 1 if created_ch else 0

                # map COs for this module
                cos_for_module = mod.get('cos', [])
                for co_token in cos_for_module:
                    # normalize token like CO1, maybe CO1,CO2 or CO 1
                    normalized = re.sub(r'\s+', '', co_token).upper()
                    # if mapping matches created outcomes (CO1..), create mapping
                    co_obj = outcome_map.get(normalized)
                    if co_obj:
                        mapping_obj, created_map = OutcomeChapterMapping.objects.get_or_create(outcome=co_obj, chapter=ch_obj)
                        created['mappings'] += 1 if created_map else 0

            # If module CO mapping information exists but some COs were not created earlier
            # try to create outcomes placeholders if CO tokens used in modules exceed discovered outcomes
            # e.g., module references CO4 but only 3 outcomes were found -> create placeholder CO4
            referenced_co_tokens = set()
            for mod in modules:
                for t in mod.get('cos', []):
                    referenced_co_tokens.add(re.sub(r'\s+', '', t).upper())
            for token in referenced_co_tokens:
                if token not in outcome_map:
                    # create placeholder
                    co_obj, created_co = CourseOutcome.objects.get_or_create(course=course_obj, outcome_code=token, defaults={'description': ''})
                    outcome_map[token] = co_obj
                    created['outcomes'] += 1 if created_co else 0

            # After ensuring outcome_map contains all referenced COs, create mappings (in case placeholders were created)
            for mod in modules:
                # identify chapter (exists or get it)
                chap_num = mod.get('num') or 0
                try:
                    ch_obj = Chapter.objects.get(course=course_obj, chapter_number=chap_num)
                except Chapter.DoesNotExist:
                    continue
                for t in mod.get('cos', []):
                    normalized = re.sub(r'\s+', '', t).upper()
                    co_obj = outcome_map.get(normalized)
                    if co_obj:
                        mapping_obj, created_map = OutcomeChapterMapping.objects.get_or_create(outcome=co_obj, chapter=ch_obj)
                        created['mappings'] += 1 if created_map else 0

    # Done - return summary
    # return {
    #     "program": program_obj.program_name,
    #     "department": dept_obj.dept_name,
    #     "scheme": scheme_obj.name,
    #     "start_year": start_year,
    #     "created": created,
    #     "parsed_courses_count": len(unique_sections),
    # }

    return True

