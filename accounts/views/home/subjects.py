# accounts/views/home/subjects.py
from django.shortcuts import render, get_object_or_404
from ...models import Course, Department, Chapter


def subject_view(request, stream, year, semester):
    print(f"Subject view called for Stream: {stream}, Year: {year}, Semester: {semester}")

    # Convert to int safely
    try:
        year_int = int(year)
    except ValueError:
        year_int = 1  # default fallback

    # Find department (case-insensitive)
    department = Department.objects.filter(dept_name__iexact=stream).first()

    year_map = {1: "First Year", 2: "Second Year", 3: "Third Year", 4: "Fourth Year"}
    year_label = year_map.get(year_int, f"{year_int}th Year")

    courses = Course.objects.filter(
        department=department,
        year_of_study__iexact=year_label,
        semester=int(semester)
)

# Generate readable year label
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(year_int, "th")

    context = {
        'stream': stream,
        'year_text': f"{year_int}{suffix} Year",
        'semester_text': f"Semester {semester[-1]}",
        'subjects': courses,
    }

    return render(request, 'home/subject_list.html', context)



def chapter_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    chapters = Chapter.objects.filter(course=course).order_by('chapter_number')

    context = {
        'course': course,
        'chapters': chapters,
    }
    return render(request, 'home/chapter_list.html', context)
