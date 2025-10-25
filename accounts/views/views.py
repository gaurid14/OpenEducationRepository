# OER/accounts/views/views.py
from django.contrib import messages
from django.shortcuts import render, redirect
# Import Django's authentication tools
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required

from .contributor.generate_expertise import generate_expertise
from ..models import User
from ..forms import ProfilePictureForm # Add this new import at the top
from .syllabus_upload import extract_and_upload
from django.shortcuts import render, redirect
from django.http import JsonResponse
from ..models import Program, Expertise, User  # Adjust import as per your project

# --- REAL LOGIN VIEW ---
# OER/accounts/views.py

def home_view(request):
    print("Home view called")
    # generate_expertise()
    return render(request, 'home/index.html')

def login_view(request):
    if request.method == 'POST':
        # FIX: Use .strip() to remove any accidental leading/trailing spaces
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')

        # The rest of the function stays the same
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            request.session['user_id'] = user.id
            request.session['role'] = user.role

            if user.role == 'CONTRIBUTOR':
                return redirect('contributor_dashboard')
            elif user.role == 'STUDENT':
                return redirect('student_dashboard')
            else:
                return redirect('login')  # fallback
        else:
            print("Login failed: Invalid credentials")
            return redirect('login')

    return render(request, 'home/register.html')


# --- DASHBOARD VIEW ---
# @login_required
# def dashboard_view(request):
#     print("Session data:", request.session.items())
#     # This code runs if the user submits the upload form
#     if request.method == 'POST':
#         print("Session data:", request.session.items())
#         # We pass request.FILES to handle the uploaded image
#         form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
#         if form.is_valid():
#             form.save() # This saves the new picture to the user
#             return redirect('dashboard') # Redirect to refresh the page
#     else:
#         # This creates a blank form for the first visit
#         form = ProfilePictureForm(instance=request.user)
#
#     # We'll pass the form to the template
#     context = {
#         'form': form
#     }
#
#     # Render the correct template based on the user's role
#     if request.user.role == 'STUDENT':
#         return redirect('contributor_dashboard')
#     elif request.user.role == 'CONTRIBUTOR':
#         return redirect('student_dashboard')
#     else:
#         return redirect('login')

# Contributor Dashboard
@login_required
def contributor_dashboard_view(request):
    form = ProfilePictureForm(instance=request.user)
    return render(request, 'contributor/contributor_dashboard.html', {'form': form})

# Student Dashboard
@login_required
def dashboard_view(request):
    form = ProfilePictureForm(instance=request.user)
    return render(request, 'student/student_dashboard.html', {'form': form})


# --- LOGOUT VIEW ---
def logout_view(request):
    logout(request)
    return redirect('login') # Redirect to login page after logout


def register_view(request):
    # ---- Handle AJAX request for expertise dropdown ----
    if request.method == 'GET' and request.GET.get('program'):
        program_name = request.GET.get('program')
        try:
            program = Program.objects.get(program_name=program_name)
            expertises = program.expertises.all().values('id', 'name')
            return JsonResponse(list(expertises), safe=False)
        except Program.DoesNotExist:
            return JsonResponse([], safe=False)

    # ---- Handle form submission ----
    if request.method == 'POST':
        role = request.POST.get('role', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # Validation
        if not email or not password:
            print("ERROR: Email or password was empty.")
            return redirect('register')

        if User.objects.filter(email__iexact=email).exists():
            print(f"ERROR: User with this email already exists.")
            return redirect('register')

        # Create user
        user = User.objects.create_user(username=email, email=email)
        user.set_password(password)

        # Role-specific data
        if role == 'student':
            user.role = User.Role.STUDENT
            user.first_name = request.POST.get('student-name', '').strip()
            user.college_name = request.POST.get('college-name', '').strip()
            user.date_of_birth = request.POST.get('dob') or None
            user.gender = request.POST.get('gender', '').strip()
            user.course = request.POST.get('course', '').strip()
            user.year = request.POST.get('year', '').strip()

        elif role == 'contributor':
            user.role = User.Role.CONTRIBUTOR
            user.first_name = request.POST.get('contrib-fname', '').strip()
            user.last_name = request.POST.get('contrib-lname', '').strip()
            user.phone_number = request.POST.get('contrib-phone', '').strip()
            user.designation = request.POST.get('designation', '').strip()
            user.current_institution = request.POST.get('institution', '').strip()
            user.years_of_experience = request.POST.get('exp') or None
            user.program = Program.objects.get(program_name=request.POST.get('program'))
            user.highest_qualification = request.POST.get('qualification')
            user.date_of_birth = request.POST.get('contrib-dob')
            user.current_institution = request.POST.get('institution', '').strip()
            user.bio = request.POST.get('bio', '').strip()
            domain_ids = request.POST.getlist('expertise')  # can select multiple
            user.save()  # must save user before assigning M2M
            if domain_ids:
                user.domain_of_expertise.set(domain_ids)  # assign multiple Expertise objects

        # Save user
        user.save()
        print(f"SUCCESS: User '{email}' was created and saved.")
        return redirect('register')

    # Default GET render (form page)
    return render(request, 'home/register.html')



def upload_syllabus(request):
    print("Upload view called")
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']

        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, "Only PDF files are allowed.")
            return redirect('upload_syllabus')

        try:
            extract_and_upload(pdf_file)
            messages.success(request, "Syllabus extracted and uploaded successfully!")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'home/upload_syllabus.html')



# Langgraph submission agent
# @login_required
# def upload_content(request):
#     if request.session.get('role') != 'CONTRIBUTOR':
#         return redirect('no_permission')  # Prevent students from accessing
#
#     contributor_id = request.session.get('user_id')
#     contributor = User.objects.get(id=contributor_id)
#
#     if request.method == 'POST':
#         chapter_id = request.POST.get('chapter_id')
#         chapter = Chapter.objects.get(id=chapter_id)
#
#         # ✅ Create the UploadCheck object and link it with contributor
#         upload = UploadCheck.objects.create(
#             contributor=contributor,
#             chapter=chapter
#         )
#
#         # You can also log this or redirect somewhere
#         print(f"✅ Upload recorded by {contributor.username} for {chapter.chapter_name}")
#         return redirect('dashboard')
#
#     # if GET
#     return render(request, 'accounts/upload_content.html')