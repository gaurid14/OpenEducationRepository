import os
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from langgraph_agents.graph.workflow import compiled_graph  # same as before

def upload_form(request):
    """Render the upload page"""
    return render(request, "index.html")

@csrf_exempt
def upload_file(request):
    """Handle file upload and pass to your LangGraph agents"""
    metadata_string = None

    if request.method == "POST" and request.FILES.get("files"):
        file = request.FILES["files"]

        # Save uploaded file to /uploads
        upload_dir = os.path.join(settings.BASE_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.name)
        with open(file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)


        try:
            # Run file through LangGraph workflow
            final_state = compiled_graph.invoke({"file_path": file_path})
            metadata_string = final_state.get("result", "No result from graph")
        except Exception as e:
            metadata_string = f"Error: {str(e)}"

    return render(request, "result.html", {"metadata_string": metadata_string})
