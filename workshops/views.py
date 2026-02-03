# workshops/views.py
from collections import OrderedDict
import math
from datetime import datetime
import csv
import json
import re
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST , require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .forms import StakeholderForm, ProblemForm, IndicatorForm , ProjectCreateForm
from .models import (
    Project,
    Problem,
    Stakeholder,
    Objective,
    Indicator,
    MasterIndicator,
    SWOTItem,
)


# -------------------------
# Stakeholder Views
# -------------------------
@login_required
def stakeholder_list(request, project_id):
    """Render stakeholder page and handle adding new stakeholders."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if request.method == "POST":
        form = StakeholderForm(request.POST)
        if form.is_valid():
            new_stakeholder = form.save(commit=False)
            new_stakeholder.project = project
            new_stakeholder.save()
            return redirect("stakeholder_list", project_id=project.id)
    else:
        form = StakeholderForm()

    stakeholders = project.stakeholders.all()

    return render(
        request,
        "workshops/stakeholder_list.html",
        {"project": project, "form": form, "stakeholders": stakeholders},
    )


@login_required
def download_stakeholders_csv(request, project_id):
    """Download CSV of stakeholders for the given project (owner-only)."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}_stakeholders.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(["Name", "Interest", "Power", "Level", "Typology", "Resources"])
    for stakeholder in project.stakeholders.all():
        writer.writerow(
            [
                stakeholder.name,
                stakeholder.interest,
                stakeholder.power,
                stakeholder.get_level_display(),
                stakeholder.get_typology_display(),
                stakeholder.get_resources_display(),
            ]
        )
    return response


@login_required
def stakeholder_data(request, project_id):
    """Return stakeholders as JSON for D3 chart (owner-only)."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    stakeholders = list(project.stakeholders.values("name", "interest", "power", "typology"))
    return JsonResponse(stakeholders, safe=False)


@login_required
@require_POST
def update_stakeholder_details(request, stakeholder_id):
    """
    AJAX endpoint to update one field for a stakeholder.
    Expects JSON: { "field": "...", "value": ... }
    """
    try:
        stakeholder = get_object_or_404(Stakeholder, id=stakeholder_id)
        # Ensure user owns the project
        if stakeholder.project.owner != request.user:
            return JsonResponse({"status": "error", "message": "Permission denied."}, status=403)

        data = json.loads(request.body.decode("utf-8"))
        field = data.get("field")
        value = data.get("value")

        if field in ["level", "typology", "resources"]:
            setattr(stakeholder, field, value)
        elif field in ["interest", "power"]:
            setattr(stakeholder, field, int(value))
        else:
            return JsonResponse({"status": "error", "message": "Invalid field."}, status=400)

        stakeholder.save()
        return JsonResponse({"status": "success", "message": "Stakeholder updated."})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
@require_POST
def delete_stakeholder(request, stakeholder_id):
    """Delete a stakeholder (owner-only)."""
    stakeholder = get_object_or_404(Stakeholder, id=stakeholder_id)
    if stakeholder.project.owner != request.user:
        return HttpResponseBadRequest("Permission denied.")
    project_id = stakeholder.project.id
    stakeholder.delete()
    return redirect("stakeholder_list", project_id=project_id)


# -------------------------
# Problem Tree Views
# -------------------------
@login_required
def problem_tree_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if request.method == "POST":
        form = ProblemForm(request.POST, project=project)
        if form.is_valid():
            new_problem = form.save(commit=False)
            new_problem.project = project
            new_problem.save()
            return redirect("problem_tree", project_id=project.id)
    else:
        form = ProblemForm(project=project)

    all_problems = Problem.objects.filter(project=project).order_by("problem_type", "description")

    return render(
        request,
        "workshops/problem_tree_graphviz.html",
        {"project": project, "form": form, "all_problems": all_problems},
    )


@login_required
@require_POST
def delete_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    if problem.project.owner != request.user:
        return HttpResponseBadRequest("Permission denied.")
    project_id = problem.project.id
    problem.delete()
    return redirect("problem_tree", project_id=project_id)


@login_required
def problem_tree_data(request, project_id):
    """
    API: return hierarchical problem tree JSON for D3.
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    all_problems = Problem.objects.filter(project=project)

    core_problem = all_problems.filter(problem_type="CORE").first()
    if not core_problem:
        return JsonResponse({"name": "No Core Problem Defined", "no_core_problem": True})

    def get_children(parent_node):
        children_data = {"causes": [], "effects": []}
        child_problems = all_problems.filter(parent=parent_node)
        for child in child_problems:
            grand_children = get_children(child)
            node_data = {
                "name": child.description,
                "id": child.id,
                "type": child.problem_type,
                "color": child.color,
                "causes": grand_children["causes"],
                "effects": grand_children["effects"],
            }
            if child.problem_type == "EFFECT":
                children_data["effects"].append(node_data)
            else:
                children_data["causes"].append(node_data)
        return children_data

    core_children = get_children(core_problem)

    tree_data = {
        "name": core_problem.description,
        "id": core_problem.id,
        "type": core_problem.problem_type,
        "color": core_problem.color,
        "causes": core_children["causes"],
        "effects": core_children["effects"],
    }

    return JsonResponse(tree_data)


# -------------------------
# Objective Tree Views (Workshop 2.3)
# -------------------------
from .models import Objective
from .forms import ObjectiveForm

@login_required
def objective_tree_view(request, project_id):
    """
    Workshop 2.3 – Objective Tree (manual, like Problem Tree):
    - Students manually add objectives (overall, impacts, means)
    - D3 visualizes them in a split tree (impacts up, means down)
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if request.method == "POST":
        form = ObjectiveForm(request.POST, project=project)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.project = project
            obj.save()
            return redirect("objective_tree", project_id=project.id)
    else:
        form = ObjectiveForm(project=project)

    all_objectives = Objective.objects.filter(project=project).order_by(
        "objective_type", "description"
    )

    return render(
        request,
        "workshops/objective_tree.html",
        {
            "project": project,
            "form": form,
            "all_objectives": all_objectives,
        },
    )


@login_required
def objective_tree_data(request, project_id):
    """
    API: return hierarchical objective tree JSON for D3,
    mirroring the structure of problem_tree_data.

    Root: SITUATION (desired situation) OR first top-level objective.
    Children:
      - objective_type == 'IMPACT'  -> go into 'effects' (upper branch)
      - others (OBJECTIVE/SITUATION etc.) -> go into 'causes' (lower branch / means)
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    all_objs = Objective.objects.filter(project=project)

    # Root: try SITUATION with no parent, or any parent-less objective
    root = (
        all_objs.filter(objective_type="SITUATION", parent__isnull=True).first()
        or all_objs.filter(parent__isnull=True).first()
    )

    if not root:
        return JsonResponse({"name": "No Overall Objective Defined", "no_root": True})

    def get_children(parent_node):
        children_data = {"causes": [], "effects": []}
        child_objs = all_objs.filter(parent=parent_node)
        for child in child_objs:
            grand_children = get_children(child)
            node_data = {
                "name": child.description,
                "id": child.id,
                "type": child.objective_type,
                "color": child.color,
                "causes": grand_children["causes"],
                "effects": grand_children["effects"],
            }
            # IMPACT → upper branch (effects)
            if child.objective_type == "IMPACT":
                children_data["effects"].append(node_data)
            else:
                # OBJECTIVE / SITUATION → lower branch (means)
                children_data["causes"].append(node_data)
        return children_data

    root_children = get_children(root)

    tree_data = {
        "name": root.description,
        "id": root.id,
        "type": root.objective_type,
        "color": root.color,
        "causes": root_children["causes"],
        "effects": root_children["effects"],
    }

    return JsonResponse(tree_data)


@login_required
@require_POST
def delete_objective(request, objective_id):
    """
    Delete a single objective node (and its children via cascade).
    """
    obj = get_object_or_404(Objective, id=objective_id)
    if obj.project.owner != request.user:
        return HttpResponseBadRequest("Permission denied.")
    project_id = obj.project.id
    obj.delete()
    return redirect("objective_tree", project_id=project_id)

# -------------------------
# Workshop List / Projects
# -------------------------

@login_required
def workshop_list_view(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    ws_flags = {
        'ws1': project.stakeholders.exists(),
        'ws2': project.problems.exists(),
        'ws3': project.indicators.filter(accepted=True).exists(),
        'ws4': project.swot_items.exists(),
    }
    return render(request, 'workshops/workshop_list.html', {
        'project': project,
        'ws_flags': ws_flags,
    })



# -------------------------
# Indicator Selection & SRF
# -------------------------
@login_required
def indicator_selection_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    # If project has no indicators, clone from MasterIndicator
    if not project.indicators.exists():
        master_list = MasterIndicator.objects.all()
        to_create = []
        for m in master_list:
            to_create.append(
                Indicator(
                    project=project,
                    master_indicator=m,
                    name=m.name,
                    description=m.description,
                    category=m.category,
                    criterion=m.criterion,
                    unit=m.unit,
                )
            )
        if to_create:
            Indicator.objects.bulk_create(to_create)

    # Add custom indicator
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

    indicators_qs = project.indicators.all().order_by("category", "name")

    # Build categories and hierarchy (main -> sub -> indicators)
    categories = []
    for c in indicators_qs.values_list("category", flat=True).distinct():
        if c and c not in categories:
            categories.append(c)

    def token_of(cat):
        if not cat:
            return ""
        return str(cat).strip().split()[0]

    main_re = re.compile(r"^[A-Z]\.$")
    sub_re = re.compile(r"^[A-Z]\d+\.$")

    hierarchy = OrderedDict()
    main_map = OrderedDict()
    sub_map = OrderedDict()

    for cat in categories:
        t = token_of(cat)
        if main_re.match(t):
            main_map[t] = cat
        elif sub_re.match(t):
            sub_map[t] = cat
        else:
            if re.match(r"^[A-Z]", t):
                if len(t) == 1:
                    main_map[f"{t}."] = cat
                else:
                    sub_map[t if t.endswith(".") else t + "."] = cat

    for main_token, main_full in main_map.items():
        hierarchy[main_token] = {"full": main_full, "subs": OrderedDict()}

    for sub_token, sub_full in sub_map.items():
        parent_letter = sub_token[0]
        parent_token = f"{parent_letter}."
        if parent_token not in hierarchy:
            hierarchy[parent_token] = {"full": parent_token, "subs": OrderedDict()}
        hierarchy[parent_token]["subs"][sub_token] = {"full": sub_full, "indicators": []}

    for ind in indicators_qs:
        name = (ind.name or "").strip()
        matched = False
        for main_token, main_dict in hierarchy.items():
            for sub_token, sub_dict in main_dict["subs"].items():
                st = sub_token if sub_token.endswith(".") else sub_token + "."
                if name.startswith(st):
                    sub_dict["indicators"].append(ind)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            # Place into first main's 'Uncategorized' fallback
            if hierarchy:
                parent = next(iter(hierarchy.values()))
                fallback_key = "uncategorized"
                if fallback_key not in parent["subs"]:
                    parent["subs"][fallback_key] = {"full": "Uncategorized", "indicators": []}
                parent["subs"][fallback_key]["indicators"].append(ind)

    return render(
        request,
        "workshops/indicator_selection.html",
        {
            "project": project,
            "form": form,
            "hierarchy": hierarchy,
            "indicator_count": indicators_qs.count(),
        },
    )


@login_required
@require_POST
def toggle_indicator_accept(request, indicator_id):
    """Toggle an indicator's 'accepted' flag (owner only)."""
    ind = get_object_or_404(Indicator, id=indicator_id)
    if ind.project.owner != request.user:
        return JsonResponse({"status": "error", "message": "Permission denied."}, status=403)
    try:
        ind.accepted = not ind.accepted
        ind.save()
        return JsonResponse({"status": "success", "accepted": ind.accepted})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def ranking_page_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    indicators = project.indicators.filter(accepted=True).order_by("order", "id")[:15]
    return render(request, "workshops/indicator_ranking.html", {"project": project, "indicators": indicators})


@login_required
@require_POST
def indicator_ranking_view(request, project_id):
    """
    Accepts JSON body with: { "order": [id_or_gap,...], "groups": [...] }
    Computes weights and saves them to indicators (owner-only).
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        order = payload.get("order", [])
        if not isinstance(order, list) or not order:
            return JsonResponse({"status": "error", "message": "Invalid or empty order"}, status=400)

        # Build simos-like incremental scores where "gap" increases separation
        score = 1.0
        scores = {}
        for item in order:
            if item == "gap":
                score += 1.0
                continue
            scores[int(item)] = score
            score += 1.0

        total = sum(scores.values()) if scores else 0.0
        if total == 0.0:
            return JsonResponse({"status": "error", "message": "No scores computed"}, status=400)

        weights = {str(k): round(v / total, 6) for k, v in scores.items()}

        # Save weights atomically
        with transaction.atomic():
            for ind_id_str, weight in weights.items():
                Indicator.objects.filter(project=project, id=int(ind_id_str)).update(weight=weight)

        return JsonResponse({"status": "success", "weights": weights})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def download_indicators_csv(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    indicators = project.indicators.filter(accepted=True).order_by("order")
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}_indicators.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(["Order", "Indicator", "Description", "WhiteCardsAfter", "Weight"])
    for ind in indicators:
        writer.writerow(
            [
                ind.order if ind.order else "",
                ind.name,
                ind.description or "",
                ind.white_cards_after,
                "{:.6f}".format(ind.weight) if ind.weight is not None else "",
            ]
        )
    return response


@login_required
@require_POST
def save_indicator_selections(request, project_id):
    """AJAX: save accepted selections for a project (owner-only)."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    data = json.loads(request.body.decode("utf-8"))
    selected_ids = data.get("selected_ids", [])
    Indicator.objects.filter(project=project).update(accepted=False)
    if selected_ids:
        Indicator.objects.filter(project=project, id__in=selected_ids).update(accepted=True)
    return JsonResponse({"status": "success", "count": len(selected_ids)})


# -------------------------
# SWOT Views
# -------------------------
@login_required
def swot_analysis_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    swot_items = project.swot_items.all() if hasattr(project, "swot_items") else []
    categories = {"S": [], "W": [], "O": [], "T": []}
    for item in swot_items:
        # Ensure category key exists and append
        categories.setdefault(item.category, []).append(item)
    return render(request, "workshops/swot_analysis.html", {"project": project, "swot": categories})


@login_required
@require_POST
def save_swot_entry(request, project_id):
    """
    AJAX CRUD for SWOT items.
    Expects JSON: { action: "add"|"edit"|"delete"|"reorder", ... }
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    try:
        data = json.loads(request.body.decode("utf-8"))
        action = data.get("action")

        if action == "add":
            item = SWOTItem.objects.create(
                project=project,
                category=data.get("category"),
                title=data.get("title", ""),
                description=data.get("description", ""),
            )
            return JsonResponse({"status": "ok", "id": item.id})

        elif action == "edit":
            item = get_object_or_404(SWOTItem, id=data.get("id"), project=project)
            item.title = data.get("title", "")
            item.description = data.get("description", "")
            item.save()
            return JsonResponse({"status": "ok"})

        elif action == "delete":
            item = get_object_or_404(SWOTItem, id=data.get("id"), project=project)
            item.delete()
            return JsonResponse({"status": "ok"})

        elif action == "reorder":
            order = data.get("order", [])
            for position, item_id in enumerate(order, start=1):
                SWOTItem.objects.filter(id=item_id, project=project).update(order=position)
            return JsonResponse({"status": "ok"})

        else:
            return JsonResponse({"status": "error", "message": "Unknown action"}, status=400)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def dashboard_view(request):
    """
    Student landing page after login.
    Shows one-card per project owned by user (staff sees all).
    Also shows progress heuristic for each project.
    """
    if request.user.is_staff:
        projects = Project.objects.all().order_by('title')
    else:
        projects = Project.objects.filter(owner=request.user).order_by('title')

    # compute a simple progress score per project (0-100)
    project_cards = []
    for p in projects:
        # simple heuristics: flags for each workshop presence:
        ws1 = p.stakeholders.exists() if hasattr(p, 'stakeholders') else False
        ws2 = p.problems.exists() if hasattr(p, 'problems') else False
        ws3 = p.indicators.filter(accepted=True).exists() if hasattr(p, 'indicators') else False
        ws4 = p.swot_items.exists() if hasattr(p, 'swot_items') else False

        completed = sum([1 if ws1 else 0, 1 if ws2 else 0, 1 if ws3 else 0, 1 if ws4 else 0])
        total = 4
        percent = int((completed / total) * 100)

        project_cards.append({
            'project': p,
            'completed': completed,
            'total': total,
            'percent': percent,
            'ws_flags': {'ws1': ws1, 'ws2': ws2, 'ws3': ws3, 'ws4': ws4},
        })

    return render(request, 'workshops/dashboard.html', {'project_cards': project_cards})


@login_required
@require_http_methods(["GET", "POST"])
def create_project_view(request):
    """
    Allow students to create exactly one project.
    If they already have one, redirect to dashboard or project overview.
    """
    # If user already has a project (non-staff), prevent creating another
    if not request.user.is_staff:
        if Project.objects.filter(owner=request.user).exists():
            # redirect to dashboard
            return redirect('dashboard')

    if request.method == "POST":
        form = ProjectCreateForm(request.POST)
        members_json = request.POST.get('members_json', '[]')
        try:
            members = json.loads(members_json)
        except Exception:
            members = []

        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.members = members
            project.save()
            return redirect('workshop_list', project_id=project.id)
    else:
        form = ProjectCreateForm()

    return render(request, 'workshops/create_project.html', {'form': form})



@login_required
@csrf_exempt  # TEMPORARY to test saving; we’ll secure later
def project_overview_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    # Initialize overview dict if empty
    if not project.overview:
        project.overview = {
            "A1": {"title": "Problem", "text": ""},
            "A2": {"title": "Context", "text": ""},
            "B1": {"title": "Solution", "text": ""},
            "B2": {"title": "Activities", "text": ""},
            "C1": {"title": "Stakeholders", "text": ""},
            "C2": {"title": "Resources", "text": ""},
            "C3": {"title": "Dissemination", "text": ""},
            "D2": {"title": "Impact on SDGs", "text": ""}
        }

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            box = data.get("box")
            text = data.get("text")

            if box in project.overview:
                project.overview[box]["text"] = text
                project.save()
                return JsonResponse({"status": "ok"})
            else:
                return JsonResponse({"status": "error", "message": "Invalid box key"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return render(request, "workshops/project_overview.html", {"project": project, "overview": project.overview})



def get_scenario_data(project: Project) -> dict:
    data = project.scenario_data or {}
    data.setdefault("actions", [])
    data.setdefault("qsorts", [])
    data.setdefault("scenarios", [])
    return data


def save_scenario_data(project: Project, data: dict) -> None:
    project.scenario_data = data
    project.save(update_fields=["scenario_data"])

@login_required
def scenario_building_view(request, project_id):
    """Stage 1 – Development of Research Instrument (actions CRUD)."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    data = get_scenario_data(project)
    actions = data["actions"]

    # Simple auto-id for actions
    next_id = max([a["id"] for a in actions], default=0) + 1

    if request.method == "POST":
        # Non-AJAX form fallback (optional)
        texts = request.POST.getlist("action_text[]")
        new_actions = []
        _id = 1
        for t in texts:
            t = t.strip()
            if not t:
                continue
            new_actions.append({
                "id": _id,
                "text": t,
                "created_at": datetime.utcnow().isoformat()
            })
            _id += 1
        data["actions"] = new_actions
        save_scenario_data(project, data)
        return redirect("scenario_building", project_id=project.id)

    return render(
        request,
        "workshops/scenario_actions.html",
        {
            "project": project,
            "actions": actions,
        },
    )

@login_required
def scenario_qsort_view(request, project_id):
    """Stage 2 – Q-Sorting Simulation."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    data = get_scenario_data(project)
    actions = data["actions"]

    if not actions:
        # If no actions yet, redirect back to stage 1
        return redirect("scenario_building", project_id=project.id)

    # 👇 this list will be used in the template instead of ".split()"
    score_levels = ["-3", "-2", "-1", "0", "1", "2", "3"]

    return render(
        request,
        "workshops/scenario_qsort.html",
        {
            "project": project,
            "actions": actions,
            "score_levels": score_levels,
            "qsorts": data.get("qsorts", []),
        },
    )

def _vector_from_qsort(distribution, action_ids):
    """Convert a distribution dict into a vector aligned with action_ids."""
    score_by_action = {aid: 0 for aid in action_ids}
    for score_str, ids in distribution.items():
        try:
            score = int(score_str)
        except ValueError:
            continue
        for aid in ids:
            score_by_action[int(aid)] = score
    return [score_by_action[aid] for aid in action_ids]


def _euclidean_distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _kmeans(qsort_vectors, k=3, max_iter=25):
    """Very simple k-means implementation."""
    n = len(qsort_vectors)
    if n == 0:
        return []

    k = min(k, n)
    centroids = qsort_vectors[:k]  # initial centroids
    assignments = [0] * n

    for _ in range(max_iter):
        # Assignment step
        changed = False
        for i, vec in enumerate(qsort_vectors):
            dists = [_euclidean_distance(vec, c) for c in centroids]
            new_cluster = dists.index(min(dists))
            if new_cluster != assignments[i]:
                assignments[i] = new_cluster
                changed = True

        if not changed:
            break

        # Update step
        new_centroids = []
        for cluster_idx in range(k):
            members = [qsort_vectors[i] for i in range(n) if assignments[i] == cluster_idx]
            if not members:
                new_centroids.append(centroids[cluster_idx])
            else:
                dim = len(members[0])
                avg = [
                    sum(vec[d] for vec in members) / len(members)
                    for d in range(dim)
                ]
                new_centroids.append(avg)
        centroids = new_centroids

    return assignments


def run_scenario_extraction(data):
    actions = data.get("actions", [])
    qsorts = data.get("qsorts", [])
    if not actions or not qsorts:
        data["scenarios"] = []
        return data

    action_ids = [a["id"] for a in actions]

    # Build vectors
    vectors = []
    for qs in qsorts:
        dist = qs.get("distribution", {})
        vec = _vector_from_qsort(dist, action_ids)
        vectors.append(vec)

    # Cluster into 3 scenarios
    assignments = _kmeans(vectors, k=3)

    # Group qsort indices by cluster
    clusters = {}
    for idx, cluster_id in enumerate(assignments):
        clusters.setdefault(cluster_id, []).append(idx)

    scenarios = []
    scenario_counter = 1

    for cluster_id, q_indices in clusters.items():
        if not q_indices:
            continue

        # Compute composite score per action (average across qsorts in this cluster)
        composite = {aid: 0.0 for aid in action_ids}
        for aid_idx, aid in enumerate(action_ids):
            scores = [vectors[i][aid_idx] for i in q_indices]
            composite[aid] = sum(scores) / len(scores)

        # Sort actions by composite score descending
        sorted_actions = sorted(action_ids, key=lambda aid: composite[aid], reverse=True)
        top_actions_ids = sorted_actions[:3]
        top_actions_texts = [
            next(a["text"] for a in actions if a["id"] == tid)
            for tid in top_actions_ids
        ]

        # Title + description suggestion
        main_action = top_actions_texts[0] if top_actions_texts else "Key action"
        title = f"Scenario {scenario_counter}: {main_action[:60]}"

        description_parts = [
            "This scenario groups participants who strongly support:",
        ]
        for t in top_actions_texts:
            description_parts.append(f"• {t}")
        description = "\n".join(description_parts)

        scenarios.append({
            "id": scenario_counter,
            "title": title,
            "description": description,
            "top_actions": top_actions_ids,
            "composite_scores": composite,
        })

        scenario_counter += 1

    data["scenarios"] = scenarios
    data["last_clustered_at"] = datetime.utcnow().isoformat()
    return data


@login_required
def scenario_results_view(request, project_id):
    """Stage 3–4 – Show scenarios + allow recalculation + PDF export."""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    data = get_scenario_data(project)

    if request.method == "POST":
        # Trigger clustering
        data = run_scenario_extraction(data)
        save_scenario_data(project, data)
        return redirect("scenario_results", project_id=project.id)

    actions = data.get("actions", [])
    scenarios = data.get("scenarios", [])

    # Make a quick lookup for actions by id for template use
    action_by_id = {a["id"]: a for a in actions}

    return render(
        request,
        "workshops/scenario_results.html",
        {
            "project": project,
            "scenarios": scenarios,
            "actions": actions,
            "action_by_id": action_by_id,
        },
    )


@require_POST
@login_required
def save_scenario(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    data = get_scenario_data(project)

    mode = request.POST.get("mode")
    if mode == "actions":
        # expects 'actions_json' = JSON list of {id?, text}
        try:
            actions_json = request.POST.get("actions_json", "[]")
            incoming = json.loads(actions_json)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

        new_actions = []
        next_id = 1
        for item in incoming:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            new_actions.append({
                "id": next_id,
                "text": text,
                "created_at": datetime.utcnow().isoformat()
            })
            next_id += 1

        data["actions"] = new_actions
        save_scenario_data(project, data)
        return JsonResponse({"status": "ok", "actions": new_actions})

    elif mode == "qsort":
        # expects: participant_label, role, distribution_json
        participant_label = (request.POST.get("participant_label") or "").strip()
        role = (request.POST.get("role") or "").strip()
        try:
            dist_json = request.POST.get("distribution_json", "{}")
            distribution = json.loads(dist_json)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

        qsorts = data.get("qsorts", [])
        next_id = max([q["id"] for q in qsorts], default=0) + 1

        qsorts.append({
            "id": next_id,
            "participant_label": participant_label or f"Participant {next_id}",
            "role": role or "Unspecified",
            "created_at": datetime.utcnow().isoformat(),
            "distribution": distribution,
        })
        data["qsorts"] = qsorts
        save_scenario_data(project, data)
        return JsonResponse({"status": "ok", "qsort_id": next_id})

    else:
        return HttpResponseBadRequest("Unknown mode")
