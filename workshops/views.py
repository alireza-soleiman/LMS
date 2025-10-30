
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



def problem_tree_view(request, project_id):
    project = Project.objects.get(id=project_id)
    form = ProblemForm(project=project)
    svg_output = "<p>Problem tree will be displayed here.</p>"
    all_problems = Problem.objects.none()

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
            # Fall through to render with errors

    # --- Graphviz Diagram Generation (Runs for GET and invalid POST) ---
    try:
        dot = graphviz.Digraph(comment=f'Problem Tree for {project.title}',
                               graph_attr={'rankdir': 'TB'})

        all_problems = Problem.objects.filter(project=project).order_by('problem_type', 'description')

        if all_problems.exists():
            core_problems = [p for p in all_problems if p.problem_type == 'CORE']
            effect_problems = [p for p in all_problems if p.problem_type == 'EFFECT']
            cause_problems = [p for p in all_problems if p.problem_type == 'CAUSE']

            node_styles = {
                'CORE': {'shape': 'box', 'style': 'filled', 'fillcolor': '#ffc107', 'margin': '0.2,0.1'},
                'EFFECT': {'shape': 'box', 'style': 'filled', 'fillcolor': '#f8d7da', 'margin': '0.2,0.1'},
                'CAUSE': {'shape': 'box', 'style': 'filled', 'fillcolor': '#cfe2ff', 'margin': '0.2,0.1'}
            }

            # Add all nodes first (without rank)
            for problem in all_problems:
                style_attrs = node_styles.get(problem.problem_type, {}).copy()
                if hasattr(problem, 'color') and problem.color:
                    style_attrs['fillcolor'] = problem.color
                dot.node(str(problem.id), problem.description, **style_attrs)

            # Add VISIBLE edges showing relationships, adjusting direction
            for problem in all_problems:
                if problem.parent:
                    # If it's an Effect linked to a Core problem
                    if problem.problem_type == 'EFFECT' and problem.parent.problem_type == 'CORE':
                        # Edge Core -> Effect (arrow points to Effect)
                        # Set constraint=false so this edge doesn't force ranking
                        dot.edge(str(problem.parent.id), str(problem.id), constraint='false')
                    # If it's a Cause linked to anything (Core or another Cause)
                    elif problem.problem_type == 'CAUSE':
                        # Edge Parent -> Cause, but arrow points UP to Parent
                        dot.edge(str(problem.parent.id), str(problem.id), dir='back')
                    # Optional: Default case
                    # else:
                    #    dot.edge(str(problem.parent.id), str(problem.id))

            # Add INVISIBLE edges to enforce vertical ranking (Effect -> Core -> Cause)
            # Connect all Effects to all Core Problems (forces Effects above Core)
            for effect in effect_problems:
                for core in core_problems:
                    dot.edge(str(effect.id), str(core.id), style='invis')

            # Connect all Core Problems to all first-level Causes (forces Core above first Causes)
            first_level_causes = [p for p in cause_problems if p.parent in core_problems]
            for core in core_problems:
                for cause in first_level_causes:
                    # Only add edge if this cause is directly linked to *this* core
                    if cause.parent_id == core.id:
                        dot.edge(str(core.id), str(cause.id), style='invis')

            # Connect first-level Causes to their second-level Causes (forces level 1 above level 2)
            for cause1 in first_level_causes:
                second_level_causes = [p for p in cause_problems if p.parent_id == cause1.id]
                for cause2 in second_level_causes:
                    dot.edge(str(cause1.id), str(cause2.id), style='invis')
            # (Extend this pattern if you need more levels)

            svg_output = dot.pipe(format='svg').decode('utf-8')
            svg_output = svg_output.replace(f'<title>{dot.comment}</title>', '', 1)

        else: # Handle case where no problems exist yet
            # This 'else' is correctly indented inside the 'try'
            svg_output = "<p>No problems added yet to generate a tree.</p>"

    # These 'except' blocks are correctly aligned with 'try'
    except FileNotFoundError:
        svg_output = "<p class='text-danger'>Error: Graphviz executable not found...</p>"
        print("ERROR: Graphviz executable not found...")
    except Exception as e:
        svg_output = f"<p class='text-danger'>Error rendering graph: {e}</p>"
        print(f"ERROR rendering graph: {e}")

    # *** CRITICAL INDENTATION ***
    # These lines MUST be at the same indentation level as the 'try'/'except'
    # and the 'if request.method == POST:' block above.
    # They should NOT be indented further.
    context = {
        'project': project,
        'form': form,
        'problem_tree_svg': svg_output,
        'all_problems': all_problems,
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


def download_problem_tree_png(request, project_id):
    project = Project.objects.get(id=project_id)

    try:
        # Initialize Graphviz object, keeping rankdir='TB'
        dot = graphviz.Digraph(comment=f'Problem Tree for {project.title}',
                               graph_attr={'rankdir': 'TB'})

        # Fetch all problems for the project
        all_problems = Problem.objects.filter(project=project)

        # Check if there are any problems to draw
        if not all_problems.exists():
            return HttpResponse("No problems to generate a tree.", status=404)

        # Separate problems by type (needed for grouping and logic)
        core_problems = [p for p in all_problems if p.problem_type == 'CORE']
        effect_problems = [p for p in all_problems if p.problem_type == 'EFFECT']
        cause_problems = [p for p in all_problems if p.problem_type == 'CAUSE']

        # Define node styles
        node_styles = {
            'CORE': {'shape': 'box', 'style': 'filled', 'fillcolor': '#ffc107', 'margin': '0.2,0.1'},
            'EFFECT': {'shape': 'box', 'style': 'filled', 'fillcolor': '#f8d7da', 'margin': '0.2,0.1'},
            'CAUSE': {'shape': 'box', 'style': 'filled', 'fillcolor': '#cfe2ff', 'margin': '0.2,0.1'}
        }

        # Add all nodes first (without rank)
        for problem in all_problems:
            style_attrs = node_styles.get(problem.problem_type, {}).copy()
            # Check for custom color (assuming 'color' field exists from Phase 2)
            if hasattr(problem, 'color') and problem.color:
                style_attrs['fillcolor'] = problem.color
            dot.node(str(problem.id), problem.description, **style_attrs)

        # Use {rank = ...} constraints for horizontal alignment within levels
        if effect_problems:
            dot.body.append('{ rank = min; ' + '; '.join([str(p.id) for p in effect_problems]) + '; }')
        if core_problems:
            dot.body.append('{ rank = same; ' + '; '.join([str(p.id) for p in core_problems]) + '; }')
        first_level_causes = [p for p in cause_problems if p.parent in core_problems]
        if first_level_causes:
            dot.body.append('{ rank = same; ' + '; '.join([str(p.id) for p in first_level_causes]) + '; }')
        second_level_causes = [p for p in cause_problems if p.parent in first_level_causes]
        if second_level_causes:
            dot.body.append('{ rank = max; ' + '; '.join([str(p.id) for p in second_level_causes]) + '; }')
        # (Extend rank grouping for more levels if needed)

        # Add VISIBLE edges showing relationships, adjusting direction
        for problem in all_problems:
            if problem.parent:
                if problem.problem_type == 'EFFECT' and problem.parent.problem_type == 'CORE':
                    # Edge Core -> Effect (arrow points to Effect), constraint false
                    dot.edge(str(problem.parent.id), str(problem.id), constraint='false')
                elif problem.problem_type == 'CAUSE':
                    # Edge Parent -> Cause, but arrow points UP to Parent
                    dot.edge(str(problem.parent.id), str(problem.id), dir='back')
                # Optional Default case for other potential relationships
                # else:
                #    dot.edge(str(problem.parent.id), str(problem.id))

        # Add INVISIBLE edges to enforce vertical ranking (Effect -> Core -> Cause)
        for effect in effect_problems:
            for core in core_problems:
                dot.edge(str(effect.id), str(core.id), style='invis')
        for core in core_problems:
            for cause in first_level_causes:
                if cause.parent_id == core.id:
                    dot.edge(str(core.id), str(cause.id), style='invis')
        for cause1 in first_level_causes:
            # Re-fetch second level causes based on cause1
            second_level_causes_for_cause1 = [p for p in cause_problems if p.parent_id == cause1.id]
            for cause2 in second_level_causes_for_cause1:
                dot.edge(str(cause1.id), str(cause2.id), style='invis')
        # (Extend invisible edge pattern if you need more levels)

        # --- Return PNG Response ---
        png_content = dot.pipe(format='png')  # Get raw PNG bytes
        response = HttpResponse(png_content, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="project_{project_id}_problem_tree.png"'
        return response

    except FileNotFoundError:
        print("ERROR: Graphviz executable not found in download_problem_tree_png. Check installation and PATH.")
        return HttpResponse("Error: Graphviz executable not found.", status=500)
    except Exception as e:
        print(f"ERROR rendering PNG graph in download_problem_tree_png: {e}")
        return HttpResponse(f"Error rendering PNG graph: {e}. Check server logs/Graphviz setup.", status=500)
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




def objective_tree_view(request, project_id):
    project = Project.objects.get(id=project_id)
    form = ObjectiveForm(project=project)
    svg_output = "<p>Objective tree will be displayed here.</p>"
    all_objectives = Objective.objects.none()

    if request.method == 'POST':
        form = ObjectiveForm(request.POST, project=project)
        if form.is_valid():
            new_objective = form.save(commit=False)
            new_objective.project = project
            new_objective.save()
            return redirect('objective_tree', project_id=project.id)
        else:
            print(f"Objective form invalid: {form.errors}")
            # Fall through to render

    # --- Graphviz Diagram Generation ---
    try:
        dot = graphviz.Digraph(comment=f'Objective Tree for {project.title}',
                               graph_attr={'rankdir': 'TB'})

        all_objectives = Objective.objects.filter(project=project).order_by('objective_type', 'description')

        if all_objectives.exists():
            core_situations = [p for p in all_objectives if p.objective_type == 'SITUATION']
            impacts = [p for p in all_objectives if p.objective_type == 'IMPACT']
            objectives = [p for p in all_objectives if p.objective_type == 'OBJECTIVE']

            # Define node styles
            node_styles = {
                'SITUATION': {'shape': 'box', 'style': 'filled', 'fillcolor': '#ffc107', 'margin': '0.2,0.1'},  # Yellow
                'IMPACT': {'shape': 'box', 'style': 'filled', 'fillcolor': '#f8d7da', 'margin': '0.2,0.1'},  # Pink
                'OBJECTIVE': {'shape': 'box', 'style': 'filled', 'fillcolor': '#cfe2ff', 'margin': '0.2,0.1'}  # Blue
            }

            # Add all nodes first
            for problem in all_objectives:
                style_attrs = node_styles.get(problem.objective_type, {}).copy()
                if hasattr(problem, 'color') and problem.color:
                    style_attrs['fillcolor'] = problem.color
                dot.node(str(problem.id), problem.description, **style_attrs)

            # Use {rank = ...} constraints for alignment
            if impacts:
                dot.body.append('{ rank = min; ' + '; '.join([str(p.id) for p in impacts]) + '; }')
            if core_situations:
                dot.body.append('{ rank = same; ' + '; '.join([str(p.id) for p in core_situations]) + '; }')

            first_level_objectives = [p for p in objectives if p.parent in core_situations]
            if first_level_objectives:
                dot.body.append('{ rank = same; ' + '; '.join([str(p.id) for p in first_level_objectives]) + '; }')

            second_level_objectives = [p for p in objectives if p.parent in first_level_objectives]
            if second_level_objectives:
                dot.body.append('{ rank = max; ' + '; '.join([str(p.id) for p in second_level_objectives]) + '; }')

            # Add VISIBLE edges
            for problem in all_objectives:
                if problem.parent:
                    # Arrows point FROM objectives UP TO desired situation
                    if problem.objective_type == 'OBJECTIVE':
                        dot.edge(str(problem.id), str(problem.parent.id))
                    # Arrows point FROM desired situation UP TO impacts
                    elif problem.objective_type == 'IMPACT' and problem.parent.objective_type == 'SITUATION':
                        dot.edge(str(problem.parent.id), str(problem.id))
                    else:
                        dot.edge(str(problem.id), str(problem.parent.id))  # Default upward flow

            # Add INVISIBLE edges for layout
            for impact in impacts:
                for core in core_situations:
                    dot.edge(str(impact.id), str(core.id), style='invis')
            for core in core_situations:
                for objective in first_level_objectives:
                    if objective.parent_id == core.id:
                        dot.edge(str(core.id), str(objective.id), style='invis')
            for obj1 in first_level_objectives:
                child_objectives = [p for p in objectives if p.parent_id == obj1.id]
                for obj2 in child_objectives:
                    dot.edge(str(obj1.id), str(obj2.id), style='invis')

            svg_output = dot.pipe(format='svg').decode('utf-8')
            svg_output = svg_output.replace(f'<title>{dot.comment}</title>', '', 1)

        else:
            svg_output = "<p>No objectives added yet to generate a tree.</p>"

    except FileNotFoundError:
        svg_output = "<p class='text-danger'>Error: Graphviz executable not found...</p>"
    except Exception as e:
        svg_output = f"<p class='text-danger'>Error rendering graph: {e}</p>"

    context = {
        'project': project,
        'form': form,
        'objective_tree_svg': svg_output,  # Renamed context variable
        'all_objectives': all_objectives,  # Renamed context variable
    }
    return render(request, 'workshops/objective_tree_graphviz.html', context)  # New template


@require_POST
def delete_objective(request, objective_id):
    objective = get_object_or_404(Objective, id=objective_id)
    project_id = objective.project.id
    objective.delete()
    return redirect('objective_tree', project_id=project_id)


def download_objective_tree_png(request, project_id):
    project = Project.objects.get(id=project_id)

    try:
        dot = graphviz.Digraph(comment=f'Objective Tree for {project.title}',
                               graph_attr={'rankdir': 'TB'})

        all_objectives = Objective.objects.filter(project=project)

        if not all_objectives.exists():
            return HttpResponse("No objectives to generate a tree.", status=404)

        core_situations = [p for p in all_objectives if p.objective_type == 'SITUATION']
        impacts = [p for p in all_objectives if p.objective_type == 'IMPACT']
        objectives = [p for p in all_objectives if p.objective_type == 'OBJECTIVE']

        node_styles = {
            'SITUATION': {'shape': 'box', 'style': 'filled', 'fillcolor': '#ffc107'},
            'IMPACT': {'shape': 'box', 'style': 'filled', 'fillcolor': '#f8d7da'},
            'OBJECTIVE': {'shape': 'box', 'style': 'filled', 'fillcolor': '#cfe2ff'}
        }

        # Add all nodes
        for problem in all_objectives:
            style_attrs = node_styles.get(problem.objective_type, {}).copy()
            if hasattr(problem, 'color') and problem.color:
                style_attrs['fillcolor'] = problem.color
            dot.node(str(problem.id), problem.description, **style_attrs)

        # {rank = ...} constraints
        if impacts:
            dot.body.append('{ rank = min; ' + '; '.join([str(p.id) for p in impacts]) + '; }')
        if core_situations:
            dot.body.append('{ rank = same; ' + '; '.join([str(p.id) for p in core_situations]) + '; }')
        first_level_objectives = [p for p in objectives if p.parent in core_situations]
        if first_level_objectives:
            dot.body.append('{ rank = same; ' + '; '.join([str(p.id) for p in first_level_objectives]) + '; }')
        second_level_objectives = [p for p in objectives if p.parent in first_level_objectives]
        if second_level_objectives:
            dot.body.append('{ rank = max; ' + '; '.join([str(p.id) for p in second_level_objectives]) + '; }')

        # Add VISIBLE edges
        for problem in all_objectives:
            if problem.parent:
                if problem.objective_type == 'OBJECTIVE':
                    dot.edge(str(problem.id), str(problem.parent.id))
                elif problem.objective_type == 'IMPACT' and problem.parent.objective_type == 'SITUATION':
                    dot.edge(str(problem.parent.id), str(problem.id))
                else:
                    dot.edge(str(problem.id), str(problem.parent.id))

        # Add INVISIBLE edges
        for impact in impacts:
            for core in core_situations:
                dot.edge(str(impact.id), str(core.id), style='invis')
        for core in core_situations:
            for objective in first_level_objectives:
                if objective.parent_id == core.id:
                    dot.edge(str(core.id), str(objective.id), style='invis')
        for obj1 in first_level_objectives:
            child_objectives = [p for p in objectives if p.parent_id == obj1.id]
            for obj2 in child_objectives:
                dot.edge(str(obj1.id), str(obj2.id), style='invis')

        png_content = dot.pipe(format='png')
        response = HttpResponse(png_content, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="project_{project_id}_objective_tree.png"'
        return response

    except FileNotFoundError:
        return HttpResponse("Error: Graphviz executable not found.", status=500)
    except Exception as e:
        return HttpResponse(f"Error rendering PNG graph: {e}.", status=500)


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