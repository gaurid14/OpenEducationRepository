# OER/accounts/views.py

from django.shortcuts import render, redirect
# Import Django's authentication tools
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import User
from .forms import ProfilePictureForm # Add this new import at the top


# --- REAL LOGIN VIEW ---
# OER/accounts/views.py

def login_view(request):
    if request.method == 'POST':
        # FIX: Use .strip() to remove any accidental leading/trailing spaces
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')

        # The rest of the function stays the same
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            print("Login failed: Invalid credentials")
            return redirect('login')

    return render(request, 'accounts/register.html')


# --- DASHBOARD VIEW ---
@login_required
def dashboard_view(request):
    # This code runs if the user submits the upload form
    if request.method == 'POST':
        # We pass request.FILES to handle the uploaded image
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save() # This saves the new picture to the user
            return redirect('dashboard') # Redirect to refresh the page
    else:
        # This creates a blank form for the first visit
        form = ProfilePictureForm(instance=request.user)

    # We'll pass the form to the template
    context = {
        'form': form
    }

    # Render the correct template based on the user's role
    if request.user.role == 'STUDENT':
        return render(request, 'accounts/student_dashboard.html', context)
    elif request.user.role == 'CONTRIBUTOR':
        return render(request, 'accounts/contributor_dashboard.html', context)
    else:
        return redirect('login')


# --- LOGOUT VIEW ---
def logout_view(request):
    logout(request)
    return redirect('login') # Redirect to login page after logout


# --- Your existing register_view ---
# OER/accounts/views.py

# OER/accounts/views.py

def register_view(request):
    if request.method == 'POST':
        # Step 1: Get and clean all common data from the form
        role = request.POST.get('role', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # Step 2: Validation
        if not email or not password:
            print("ERROR: Email or password was empty.")
            return redirect('register')
        
        if User.objects.filter(email__iexact=email).exists():
            print(f"ERROR: User with this email already exists.")
            return redirect('register')

        # Step 3: Create the user object
        user = User.objects.create_user(username=email, email=email)
        user.set_password(password)
        
        # Step 4: Assign role and save all role-specific data
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
            user.first_name = request.POST.get('contrib-name', '').strip()
            user.phone_number = request.POST.get('contrib-phone', '').strip()
            user.designation = request.POST.get('designation', '').strip()
            user.years_of_experience = request.POST.get('exp') or None
            user.domain_of_expertise = request.POST.get('domain', '').strip()
            user.date_of_birth = request.POST.get('contrib-dob') or None
            user.current_institution = request.POST.get('institution', '').strip()
            user.bio = request.POST.get('bio', '').strip()

        # Step 5: Save the fully updated user to the database
        user.save()
        print(f"SUCCESS: User '{email}' was created and saved.")
        return redirect('register')

    # This runs for a GET request (when a user just visits the page)
    return render(request, 'accounts/register.html')