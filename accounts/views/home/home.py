from django.shortcuts import render


def about(request):
    return render(request, 'home/about.html', )

def contact(request):
    return render(request, 'home/contact.html', )