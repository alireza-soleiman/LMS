# workshops/views.py
from collections import OrderedDict
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
# Workshop List / Projects
# -------------------------
from django.contrib.auth.decorators import login_required

@login_required
def workshop_list(request):
    if request.user.is_staff:
        projects = Project.objects.all().order_by('title')  # admin sees all
    else:
        projects = Project.objects.filter(owner=request.user).order_by('title')

    return render(request, 'workshops/workshop_list.html', {'projects': projects})


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
            return redirect('project_overview', project_id=project.id)
    else:
        form = ProjectCreateForm()

    return render(request, 'workshops/create_project.html', {'form': form})

