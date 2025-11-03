
from .models import Project, Problem, Stakeholder , Objective
from .forms import StakeholderForm , ProblemForm , ObjectiveForm
import csv
import json
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
import graphviz

def stakeholder_list(request, project_id):
    project = Project.objects.get(id=project_id)

    # This block handles the form submission (POST request)
    if request.method == 'POST':
        form = StakeholderForm(request.POST)
        if form.is_valid():
            new_stakeholder = form.save(commit=False)
            new_stakeholder.project = project  # Assign the project before saving
            new_stakeholder.save()
            return redirect('stakeholder_list', project_id=project.id)
    # For a normal page load (GET request), we just create a blank form
    else:
        form = StakeholderForm()  # This was the line causing the error

    stakeholders = project.stakeholders.all()

    context = {
        'project': project,
        'form': form,
        'stakeholders': stakeholders,
    }
    return render(request, 'workshops/stakeholder_list.html', context)


def download_stakeholders_csv(request, project_id):
    project = Project.objects.get(id=project_id)
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="project_{project_id}_stakeholders.csv"'},
    )
    writer = csv.writer(response)
    # Update the header row
    writer.writerow(['Name', 'Interest', 'Power', 'Level', 'Typology', 'Resources'])
    # Update the data rows
    for stakeholder in project.stakeholders.all():
        writer.writerow([
            stakeholder.name,
            stakeholder.interest,
            stakeholder.power,
            stakeholder.get_level_display(),    # Use get_..._display() for human-readable value
            stakeholder.get_typology_display(),
            stakeholder.get_resources_display(),
        ])
    return response

def stakeholder_data(request, project_id):
    """
    This view serves stakeholder data as JSON for our D3.js chart.
    """
    project = Project.objects.get(id=project_id)
    # We convert the stakeholder data into a list of dictionaries.
    stakeholders = list(project.stakeholders.values('name', 'interest', 'power', 'typology'))
    return JsonResponse(stakeholders, safe=False)


# --- THIS IS THE NEW, SIMPLIFIED FUNCTION ---
def problem_tree_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # --- Handle POST Request ---
    if request.method == 'POST':
        form = ProblemForm(request.POST, project=project)
        if form.is_valid():
            new_problem = form.save(commit=False)
            new_problem.project = project
            new_problem.save()
            print(f"SAVED: {new_problem}")
            return redirect('problem_tree', project_id=project.id)
        else:
            print("Form is NOT valid. Errors:")
            print(form.errors)
            # If form is invalid, we'll fall through and re-render with the errors

    # --- Handle GET Request (or invalid POST) ---
    form = ProblemForm(project=project)  # Create a fresh form for GET

    # We still need all_problems for the "Manage Problems" list
    all_problems = Problem.objects.filter(project=project).order_by('problem_type', 'description')

    context = {
        'project': project,
        'form': form,
        'all_problems': all_problems,
        # 'problem_tree_svg' is no longer needed! D3.js handles it.
    }
    return render(request, 'workshops/problem_tree_graphviz.html', context)
# --- Other views ---
def update_stakeholder_details(request, stakeholder_id):
    # This view only accepts asynchronous POST requests
    if request.method == 'POST':
        try:
            stakeholder = Stakeholder.objects.get(id=stakeholder_id)
            data = json.loads(request.body)
            field = data.get('field')
            value = data.get('value')

            # --- UPDATE THIS LOGIC BLOCK ---
            if field in ['level', 'typology', 'resources']:
                setattr(stakeholder, field, value)
            elif field in ['interest', 'power']:
                # Convert slider values to integers
                setattr(stakeholder, field, int(value))
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid field.'}, status=400)

            stakeholder.save()
            return JsonResponse({'status': 'success', 'message': 'Stakeholder updated.'})
            # --- END OF UPDATE ---

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return HttpResponseBadRequest("Invalid request method.")

@require_POST  # Ensures this view only accepts POST requests for security
def delete_problem(request, problem_id):
    # Find the problem or return a 404 error if not found
    problem = get_object_or_404(Problem, id=problem_id)
    project_id = problem.project.id  # Get project ID before deleting

    # Check if the problem is a Core Problem with children (optional safety check)
    # You might want to prevent deletion or add a confirmation step later
    # if problem.problem_type == 'CORE' and problem.children.exists():
    #     messages.error(request, "Cannot delete a Core Problem that has causes or effects linked to it.")
    #     return redirect('problem_tree', project_id=project_id)

    problem.delete()
    # messages.success(request, f"Problem '{problem.description}' deleted.") # Optional: Add user feedback

    # Redirect back to the problem tree page for the same project
    return redirect('problem_tree', project_id=project_id)




def workshop_list(request):
    # Fetch all projects from the database
    projects = Project.objects.all().order_by('title')

    context = {
        'projects': projects,
    }
    # We will create this new template in Step 3
    return render(request, 'workshops/workshop_list.html', context)

@require_POST
def delete_stakeholder(request, stakeholder_id):
    stakeholder = get_object_or_404(Stakeholder, id=stakeholder_id)
    project_id = stakeholder.project.id
    stakeholder.delete()
    return redirect('stakeholder_list', project_id=project_id)


from django.http import JsonResponse
from .models import Project, Problem  # Make sure Problem is imported at the top





def problem_tree_data(request, project_id):
    """
    This new API view serves the problem tree data as a hierarchical JSON
    for D3.js to consume.
    It finds the first CORE problem and builds two-sided tree data.
    """
    project = get_object_or_404(Project, id=project_id)
    all_problems = Problem.objects.filter(project=project)

    # 1. Find the first CORE problem to act as the root
    core_problem = all_problems.filter(problem_type='CORE').first()

    if not core_problem:
        # If no core problem exists, send a specific flag
        return JsonResponse({'name': 'No Core Problem Defined', 'no_core_problem': True})

    # 2. Recursive helper function to find all descendants
    def get_children(parent_node):
        # This will hold the children, split by type
        children_data = {'causes': [], 'effects': []}

        # Find all direct children of the current parent
        child_problems = all_problems.filter(parent=parent_node)

        for child in child_problems:
            # Get the children of this child, recursively
            grand_children = get_children(child)

            # Build the node data for this child
            node_data = {
                'name': child.description,
                'id': child.id,
                'type': child.problem_type,
                'color': child.color,
                # Pass the recursively-found children along
                'causes': grand_children['causes'],
                'effects': grand_children['effects']
            }

            # 3. Sort the child into the correct list
            if child.problem_type == 'EFFECT':
                children_data['effects'].append(node_data)
            else:
                # Any other type (CAUSE, or even another CORE) goes down
                children_data['causes'].append(node_data)

        return children_data

    # 4. Build the final tree data, starting from the core problem
    core_children = get_children(core_problem)

    tree_data = {
        'name': core_problem.description,
        'id': core_problem.id,
        'type': core_problem.problem_type,
        'color': core_problem.color,
        'causes': core_children['causes'],  # The 'down' tree
        'effects': core_children['effects']  # The 'up' tree
    }

    return JsonResponse(tree_data)