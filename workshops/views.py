
from .models import Project, Problem, Stakeholder, Objective, Indicator, MasterIndicator
from .forms import StakeholderForm , ProblemForm , IndicatorForm
import csv
import json
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q
import re
from collections import OrderedDict




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

def indicator_selection_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Clone master indicators if project is empty
    if not project.indicators.exists():
        master_list = MasterIndicator.objects.all()
        to_create = [
            Indicator(
                project=project,
                master_indicator=m,
                name=m.name,
                description=m.description,
                category=m.category,
                criterion=m.criterion,
                unit=m.unit,
            ) for m in master_list
        ]
        if to_create:
            Indicator.objects.bulk_create(to_create)

    # Handle add-custom form
    if request.method == "POST" and "add_indicator" in request.POST:
        form = IndicatorForm(request.POST)
        if form.is_valid():
            new_ind = form.save(commit=False)
            new_ind.project = project
            new_ind.added_by_student = True
            new_ind.save()
            return redirect("indicator_selection", project_id=project.id)
    else:
        form = IndicatorForm()

    # Get all indicators for this project
    indicators_qs = project.indicators.all().order_by("category", "name")

    # Collect unique category strings in order
    categories = []
    for c in indicators_qs.values_list("category", flat=True).distinct():
        if c and c not in categories:
            categories.append(c)

    # Helper to get the prefix token (first token, e.g., 'A.', 'A1.', etc.)
    def token_of(cat):
        if not cat:
            return ""
        token = str(cat).strip().split()[0]
        return token

    # Patterns
    main_re = re.compile(r'^[A-Z]\.$')          # e.g. "A."
    sub_re = re.compile(r'^[A-Z]\d+\.$')        # e.g. "A1."
    # indicator names start like "A1.1 - ..." so we'll check name prefix

    # Build ordered main -> sub -> indicators structure
    hierarchy = OrderedDict()

    # Build lists of main and sub category tokens and keep mapping to full category string
    main_map = OrderedDict()   # token -> full string
    sub_map = OrderedDict()    # token -> full string (last occurrence)

    for cat in categories:
        t = token_of(cat)
        if main_re.match(t):
            main_map[t] = cat
        elif sub_re.match(t):
            sub_map[t] = cat
        else:
            # If a category doesn't match, try to detect by first char (fall back)
            # e.g. 'A. Use of ...' or 'A1. Use...'
            if re.match(r'^[A-Z]', t):
                # if single letter token with trailing dot missing, add dot
                if len(t) == 1:
                    main_map[f"{t}."] = cat
                else:
                    sub_map[t if t.endswith('.') else t + '.'] = cat

    # Initialize hierarchy with main categories in order of appearance
    for main_token, main_full in main_map.items():
        hierarchy[main_token] = {
            "full": main_full,
            "subs": OrderedDict()
        }

    # Place subcategories under their parent main category
    for sub_token, sub_full in sub_map.items():
        # parent letter is the first letter of sub_token
        parent_letter = sub_token[0]
        parent_token = f"{parent_letter}."
        if parent_token not in hierarchy:
            # Create parent if missing (defensive)
            hierarchy[parent_token] = {"full": parent_token, "subs": OrderedDict()}
        hierarchy[parent_token]["subs"][sub_token] = {
            "full": sub_full,
            "indicators": []
        }

    # Now assign indicator rows to the matching subcategory by checking the prefix of indicator.name
    for ind in indicators_qs:
        name = (ind.name or "").strip()
        # Attempt to find a subtoken that matches the start of the name (e.g., 'A1.' matches 'A1.1 - ...')
        matched = False
        for main_token, main_dict in hierarchy.items():
            for sub_token, sub_dict in main_dict["subs"].items():
                # ensure sub_token ends with '.' for matching
                st = sub_token if sub_token.endswith('.') else sub_token + '.'
                if name.startswith(st):
                    sub_dict["indicators"].append(ind)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            # If no subcategory matched, try to attach to a "Uncategorized" bucket under top-level
            parent = next(iter(hierarchy.values())) if hierarchy else None
            if parent:
                # create a fallback subcategory label
                fallback_key = "uncategorized"
                if fallback_key not in parent["subs"]:
                    parent["subs"][fallback_key] = {"full": "Uncategorized", "indicators": []}
                parent["subs"][fallback_key]["indicators"].append(ind)

    context = {
        "project": project,
        "form": form,
        "hierarchy": hierarchy,   # OrderedDict of mains -> subs -> indicators
        "indicator_count": indicators_qs.count(),
    }

    return render(request, "workshops/indicator_selection.html", context)


# Toggle accept/refuse for an indicator (AJAX-friendly POST)
@require_POST
def toggle_indicator_accept(request, indicator_id):
    ind = get_object_or_404(Indicator, id=indicator_id)
    try:
        ind.accepted = not ind.accepted
        ind.save()
        return JsonResponse({'status': 'success', 'accepted': ind.accepted})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)



# Phase 2: Ranking + SRF weighting
# Accepts POST JSON: { "order": [indicator_id,...], "white_cards": {id: n, ...} }
@require_POST
@csrf_exempt
def indicator_ranking_view(request, project_id):
    """
    Expects JSON body with:
    {
      "order": [id1, id2, id3, ...],
      "white_cards": {"id1": 0, "id2": 2, ...}
    }
    We'll compute a simple SRF-style score:
      - assign sequential base scores considering white cards as added gaps
      - normalize to weights that sum to 1.0
    """
    project = get_object_or_404(Project, id=project_id)

    try:
        payload = json.loads(request.body)
        order = payload.get('order', [])
        white_cards = payload.get('white_cards', {})
        # Validate order
        if not isinstance(order, list):
            return JsonResponse({'status': 'error', 'message': 'Invalid order list'}, status=400)

        # Build base scores using Simos-like incremental scheme:
        # Start with score = 1 for the topmost group, then for each next indicator:
        # score_next = score_prev + 1 + white_cards_between
        scores = {}
        current_score = 1.0
        for idx, ind_id in enumerate(order):
            # ensure white_cards is an int 0..4
            wb = int(white_cards.get(str(ind_id), white_cards.get(ind_id, 0) or 0))
            if wb < 0:
                wb = 0
            if wb > 10:  # safety cap
                wb = 10
            scores[int(ind_id)] = current_score
            # increment for next
            current_score = current_score + 1.0 + float(wb)

        # Normalize scores into weights (weights sum to 1.0)
        total = sum(scores.values()) if scores else 0.0

        # If no items, return error
        if total == 0.0:
            return JsonResponse({'status': 'error', 'message': 'No indicators found in order'}, status=400)

        weights = {str(k): (v / total) for k, v in scores.items()}

        # Save order, white_cards_after and weight in a transaction
        with transaction.atomic():
            for position, ind_id in enumerate(order, start=1):
                ind = Indicator.objects.filter(project=project, id=ind_id).first()
                if not ind:
                    continue
                ind.order = position
                wc = int(white_cards.get(str(ind_id), white_cards.get(ind_id, 0) or 0))
                ind.white_cards_after = wc
                ind.weight = float(weights.get(str(ind_id), 0.0))
                ind.save()

        # Return computed weights for client display + CSV option
        return JsonResponse({'status': 'success', 'weights': weights})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# CSV download of finalized indicators
def download_indicators_csv(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    indicators = project.indicators.filter(accepted=True).order_by('order')
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="project_{project_id}_indicators.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(['Order', 'Indicator', 'Description', 'WhiteCardsAfter', 'Weight'])
    for ind in indicators:
        writer.writerow([
            ind.order if ind.order else '',
            ind.name,
            ind.description or '',
            ind.white_cards_after,
            "{:.6f}".format(ind.weight) if ind.weight is not None else '',
        ])
    return response


from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse

@csrf_exempt
def save_indicator_selections(request, project_id):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        selected_ids = data.get("selected_ids", [])
        # Reset all first
        Indicator.objects.filter(project_id=project_id).update(accepted=False)
        # Mark selected ones
        Indicator.objects.filter(project_id=project_id, id__in=selected_ids).update(accepted=True)
        return JsonResponse({"status": "success", "count": len(selected_ids)})
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)
